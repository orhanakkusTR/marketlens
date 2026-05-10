"""Setup Quality + No-Trade Zone + Scenario endpoints (Adım 13/14/16).

GET /api/v1/analysis/quality/{symbol}/{tf}          → SetupQualityResult
GET /api/v1/analysis/no-trade-zones/{symbol}/{tf}   → NoTradeZoneResult
GET /api/v1/analysis/scenario/{symbol}/{tf}         → ScenarioWithPosition
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.middleware import limiter
from app.core.security import get_current_user_optional
from app.data.binance_spot import TF_TO_INTERVAL
from app.data.symbols_meta import ALL_SYMBOLS
from app.db.session import get_session
from app.models.user import User
from app.schemas.no_trade_zone import NoTradeZoneResult
from app.schemas.scenario import ScenarioWithPosition
from app.schemas.setup_quality import SetupQualityResult
from app.services.analysis.scenario_generator import generate_scenario
from app.services.indicators.base import klines_to_dataframe
from app.services.indicators.engine import indicator_engine
from app.services.quality.no_trade_zone import no_trade_zone_detector
from app.services.quality.setup_quality import setup_quality_engine
from app.services.risk.daily_tracker import daily_risk_tracker
from app.services.risk.position_sizer import compute_position

router = APIRouter(prefix="/analysis", tags=["analysis"])

DEFAULT_BALANCE_USDT = 3000.0
DEFAULT_MAX_LEVERAGE = 10

KNOWN_SYMBOLS: frozenset[str] = frozenset(ALL_SYMBOLS)


@router.get("/quality/{symbol}/{timeframe}", response_model=SetupQualityResult)
@limiter.limit("30/minute")
async def get_setup_quality(
    request: Request,
    symbol: str = Path(..., min_length=3, max_length=20),
    timeframe: str = Path(..., min_length=2, max_length=4),
    session: AsyncSession = Depends(get_session),
) -> SetupQualityResult:
    """Setup quality değerlendirmesi: 4 modül composite.

    - Base score (0-100) + grade (A/B/C/D)
    - Confidence (trade journal — şu an boş, VERY_LOW)
    - Counter-trend warnings (max 5, severity desc)
    - Trade quality filter (5 faktör, EXCELLENT/GOOD/WEAK/AVOID)
    - Final grade (modifier'lar uygulanmış, NO_TRADE override mümkün)
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

    return await setup_quality_engine.evaluate(
        symbol_upper, timeframe, session=session
    )


@router.get(
    "/no-trade-zones/{symbol}/{timeframe}",
    response_model=NoTradeZoneResult,
)
@limiter.limit("60/minute")
async def get_no_trade_zones(
    request: Request,
    symbol: str = Path(..., min_length=3, max_length=20),
    timeframe: str = Path(..., min_length=2, max_length=4),
    session: AsyncSession = Depends(get_session),
) -> NoTradeZoneResult:
    """No-trade zone tespiti — 9 tip (5 active + 4 future-ready info).

    Active triggers:
    - weekend (blocking): Cuma 22:00 UTC → Pzt 02:00 UTC
    - low_liquidity_session (warning): Asya seansı 00:00-08:00 UTC
    - high_volatility (warning): BTC 24h |%| ≥ 8 veya ATR z-score ≥ 2
    - range_market (warning): BB squeeze + flat OBV
    - tilt (blocking): son 24h ≥3 ardışık SL

    Severity desc sıralı (blocking → warning → info).
    Detector cache'siz — anlık zone değişimleri yansır.
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

    bundle = await indicator_engine.compute_all(
        symbol_upper,
        timeframe,
        modules=["volatility", "volume"],
    )
    klines = await indicator_engine._get_klines(symbol_upper, timeframe)
    df = klines_to_dataframe(klines)

    # BTC 24h proxy: 1H 25 mum
    btc_24h_change: float | None = None
    try:
        btc_klines = await indicator_engine._get_klines("BTCUSDT", "1H", 25)
        if len(btc_klines) >= 25:
            btc_old = float(btc_klines[0]["close"])
            btc_new = float(btc_klines[-1]["close"])
            if btc_old > 0:
                btc_24h_change = ((btc_new - btc_old) / btc_old) * 100
    except Exception:
        pass

    return await no_trade_zone_detector.detect(
        symbol=symbol_upper,
        timeframe=timeframe,
        df=df,
        volatility=bundle.volatility,
        volume=bundle.volume,
        btc_24h_change_pct=btc_24h_change,
        session=session,
    )


# ─── Scenario (Adım 16) ───


@router.get("/scenario/{symbol}/{timeframe}", response_model=ScenarioWithPosition)
@limiter.limit("60/minute")
async def get_scenario(
    request: Request,
    symbol: str = Path(..., min_length=3, max_length=20),
    timeframe: str = Path(..., min_length=2, max_length=4),
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_current_user_optional),
) -> ScenarioWithPosition:
    """Sistem auto entry/stop/TP senaryosu + pozisyon hesabı.

    - direction = final confluence'tan
    - entry = current_price ± 0.3 ATR band
    - stop  = en yakın support/resistance ∓ 0.5 ATR buffer
              (level 0.5-3 ATR aralığı dışındaysa ATR×1.5 fallback)
    - TP1/TP2/TP3 = levels'tan (R/R ≥ 1, cluster ≥ 0.5 ATR aralık)
                    fallback: ATR×2/4/6
    - Pozisyon: 3000 USDT default + smart reduction sonrası risk %

    422: direction nötr veya veriler yetersiz.
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
            f"{symbol_upper} {timeframe} için yön nötr — senaryo üretilemez.",
            details={"direction": "neutral", "final_score": final.final_score},
        )

    bundle = await indicator_engine.compute_all(
        symbol_upper, timeframe, modules=["volatility", "levels", "futures"],
    )
    if bundle.volatility is None or bundle.levels is None:
        raise ValidationError(
            "Volatility veya levels hesaplanamadı — senaryo mümkün değil.",
            details={"symbol": symbol_upper, "timeframe": timeframe},
        )

    atr = bundle.volatility.atr.value_usdt
    current_price = bundle.levels.current_price

    scenario = generate_scenario(
        symbol=symbol_upper,
        timeframe=timeframe,
        direction=final.direction,
        current_price=current_price,
        atr=atr,
        levels=bundle.levels,
        final_confluence=final.final_score,
    )
    if scenario is None:
        raise ValidationError(
            "Senaryo üretilemedi (ATR ≤ 0 veya current_price ≤ 0).",
            details={"atr": atr, "current_price": current_price},
        )

    # Position hesabı — entry.mid + stop + TP'ler
    risk_pct, _, _ = await daily_risk_tracker.get_current_risk_per_trade_pct(
        session, user.id if user else None
    )
    funding_rate = (
        bundle.futures.funding.current_rate if bundle.futures is not None else None
    )

    # BTC 24h proxy
    btc_change: float | None = None
    try:
        btc_klines = await indicator_engine._get_klines("BTCUSDT", "1H", 25)
        if len(btc_klines) >= 25:
            btc_old = float(btc_klines[0]["close"])
            btc_new = float(btc_klines[-1]["close"])
            if btc_old > 0:
                btc_change = ((btc_new - btc_old) / btc_old) * 100
    except Exception:
        pass

    position = compute_position(
        symbol=symbol_upper,
        direction=scenario.direction,
        balance=DEFAULT_BALANCE_USDT,
        base_risk_pct=risk_pct,
        entry=scenario.entry.mid,
        stop=scenario.stop.price,
        targets=[t.price for t in scenario.targets],
        max_leverage=DEFAULT_MAX_LEVERAGE,
        funding_rate=funding_rate,
        btc_24h_change_pct=btc_change,
        atr_zscore=None,
    )

    return ScenarioWithPosition(scenario=scenario, position=position)
