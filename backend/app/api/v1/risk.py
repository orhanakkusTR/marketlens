"""Risk Management endpoint'leri — Adım 15.

POST /api/v1/risk/calculate-position   — custom entry/stop/targets
GET  /api/v1/analysis/risk/{sym}/{tf}  — sistem auto hesabı
GET  /api/v1/risk/daily-status         — günlük durum (optional auth)
POST /api/v1/risk/pause                — manuel pause (optional auth)
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.middleware import limiter
from app.core.security import get_current_user_optional
from app.data.binance_spot import TF_TO_INTERVAL
from app.data.symbols_meta import ALL_SYMBOLS
from app.db.session import get_session
from app.models.user import User
from app.schemas.risk import (
    DailyRiskStatus,
    PositionRiskInput,
    PositionRiskResult,
    RiskPauseRequest,
    RiskPauseResponse,
)
from app.services.indicators.engine import indicator_engine
from app.services.risk.daily_tracker import (
    PAUSE_DEFAULT_HOURS,
    daily_risk_tracker,
)
from app.services.risk.position_sizer import compute_position

router = APIRouter(tags=["risk"])

KNOWN_SYMBOLS: frozenset[str] = frozenset(ALL_SYMBOLS)

# Auto endpoint için varsayılan parametreler
DEFAULT_BALANCE_USDT = 3000.0
DEFAULT_BASE_RISK_PCT = 2.0
DEFAULT_MAX_LEVERAGE = 10
AUTO_STOP_ATR_MULT = 1.5
AUTO_TP_ATR_MULT_1 = 1.5
AUTO_TP_ATR_MULT_2 = 3.0
AUTO_TP_ATR_MULT_3 = 5.0


# ─── BTC 24h proxy ───


async def _btc_24h_change() -> float | None:
    try:
        klines = await indicator_engine._get_klines("BTCUSDT", "1H", 25)
        if len(klines) < 25:
            return None
        old = float(klines[0]["close"])
        new = float(klines[-1]["close"])
        if old <= 0:
            return None
        return ((new - old) / old) * 100
    except Exception:
        return None


# ─── 1. POST /risk/calculate-position ───


@router.post("/risk/calculate-position", response_model=PositionRiskResult)
@limiter.limit("60/minute")
async def calculate_position(
    request: Request,
    payload: PositionRiskInput,
) -> PositionRiskResult:
    """Kullanıcı parametreli pozisyon hesabı.

    - Volatility adjustment (BTC 24h |%|>5/>8 veya ATR z-score >2)
    - R/R per TP + weighted (40/35/25)
    - Liquidation @5x, @10x, @actual_leverage
    - Funding cost 24h/72h/1w (direction-aware signed)
    - Warnings: stop_too_tight (blocking), leverage_capped, rr_below_1
    """
    if payload.symbol.upper() not in KNOWN_SYMBOLS:
        raise NotFoundError(
            f"Bilinmeyen sembol: {payload.symbol}",
            details={"known": sorted(KNOWN_SYMBOLS)},
        )

    btc_change = payload.btc_24h_change_pct
    if btc_change is None:
        btc_change = await _btc_24h_change()

    funding = payload.funding_rate
    if funding is None:
        try:
            bundle = await indicator_engine.compute_all(
                payload.symbol.upper(), "4H", modules=["futures"],
            )
            if bundle.futures is not None:
                funding = bundle.futures.funding.current_rate
        except Exception:
            funding = None

    return compute_position(
        symbol=payload.symbol.upper(),
        direction=payload.direction,
        balance=payload.balance,
        base_risk_pct=payload.base_risk_pct,
        entry=payload.entry,
        stop=payload.stop,
        targets=payload.targets,
        max_leverage=payload.max_leverage,
        funding_rate=funding,
        btc_24h_change_pct=btc_change,
        atr_zscore=payload.atr_zscore,
    )


# ─── 2. GET /analysis/risk/{sym}/{tf} — auto ───


@router.get("/analysis/risk/{symbol}/{timeframe}", response_model=PositionRiskResult)
@limiter.limit("60/minute")
async def auto_risk_for_symbol(
    request: Request,
    symbol: str = Path(..., min_length=3, max_length=20),
    timeframe: str = Path(..., min_length=2, max_length=4),
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_current_user_optional),
) -> PositionRiskResult:
    """Sistem auto entry/stop/TP hesabı.

    - entry = current_price
    - stop  = current_price ∓ 1.5*ATR (direction-aware)
    - TP1/TP2/TP3 = ATR multiplier 1.5 / 3 / 5
    - direction = final confluence'dan
    - balance = 3000 USDT (default), risk = smart-reduction sonrası
    - Notr direction veya volatility yok → ValidationError
    """
    symbol_upper = symbol.upper()
    if symbol_upper not in KNOWN_SYMBOLS:
        raise NotFoundError(
            f"Bilinmeyen sembol: {symbol}",
            details={"known": sorted(KNOWN_SYMBOLS)},
        )
    if timeframe not in TF_TO_INTERVAL:
        raise ValidationError(
            f"Geçersiz timeframe: {timeframe}",
            details={"valid": sorted(TF_TO_INTERVAL.keys())},
        )

    final = await indicator_engine.compute_final_confluence(symbol_upper, timeframe)
    if final.direction == "neutral":
        raise ValidationError(
            f"{symbol_upper} {timeframe} için yön nötr — auto pozisyon hesaplanmıyor.",
            details={"direction": "neutral"},
        )

    bundle = await indicator_engine.compute_all(
        symbol_upper, timeframe, modules=["volatility", "levels", "futures"],
    )
    if bundle.volatility is None or bundle.levels is None:
        raise ValidationError(
            "Volatility veya levels hesaplanamadı — auto pozisyon mümkün değil.",
            details={"symbol": symbol_upper, "timeframe": timeframe},
        )

    atr = bundle.volatility.atr.value_usdt
    current_price = bundle.levels.current_price

    if final.direction == "long":
        stop = current_price - AUTO_STOP_ATR_MULT * atr
        targets = [
            current_price + AUTO_TP_ATR_MULT_1 * atr,
            current_price + AUTO_TP_ATR_MULT_2 * atr,
            current_price + AUTO_TP_ATR_MULT_3 * atr,
        ]
    else:  # short
        stop = current_price + AUTO_STOP_ATR_MULT * atr
        targets = [
            current_price - AUTO_TP_ATR_MULT_1 * atr,
            current_price - AUTO_TP_ATR_MULT_2 * atr,
            current_price - AUTO_TP_ATR_MULT_3 * atr,
        ]

    # Smart reduction sonrası risk
    risk_pct, _, _ = await daily_risk_tracker.get_current_risk_per_trade_pct(
        session, user.id if user else None
    )

    funding_rate = (
        bundle.futures.funding.current_rate if bundle.futures is not None else None
    )
    btc_change = await _btc_24h_change()

    return compute_position(
        symbol=symbol_upper,
        direction=final.direction,
        balance=DEFAULT_BALANCE_USDT,
        base_risk_pct=risk_pct,
        entry=current_price,
        stop=stop,
        targets=targets,
        max_leverage=DEFAULT_MAX_LEVERAGE,
        funding_rate=funding_rate,
        btc_24h_change_pct=btc_change,
        atr_zscore=None,
    )


# ─── 3. GET /risk/daily-status ───


@router.get("/risk/daily-status", response_model=DailyRiskStatus)
@limiter.limit("60/minute")
async def daily_status(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_current_user_optional),
) -> DailyRiskStatus:
    """Günlük risk durumu — auth varsa user'a, yoksa global state."""
    return await daily_risk_tracker.get_status(
        session, user.id if user else None, now_utc=datetime.now(UTC)
    )


# ─── 4. POST /risk/pause ───


@router.post("/risk/pause", response_model=RiskPauseResponse)
@limiter.limit("20/minute")
async def pause_risk(
    request: Request,
    payload: RiskPauseRequest | None = None,
    user: User | None = Depends(get_current_user_optional),
) -> RiskPauseResponse:
    """Manuel pause — auth varsa kullanıcıya, yoksa global key."""
    hours = payload.hours if payload is not None else PAUSE_DEFAULT_HOURS
    paused_until = await daily_risk_tracker.pause(
        user.id if user else None, hours=hours
    )
    return RiskPauseResponse(
        paused_until=paused_until,
        hours=hours,
        message=f"Risk {hours} saat duraklatıldı.",
    )
