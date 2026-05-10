"""Setup Quality + No-Trade Zone endpoints (Adım 13 + 14).

GET /api/v1/analysis/quality/{symbol}/{tf}          → SetupQualityResult
GET /api/v1/analysis/no-trade-zones/{symbol}/{tf}   → NoTradeZoneResult
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.middleware import limiter
from app.data.binance_spot import TF_TO_INTERVAL
from app.data.symbols_meta import ALL_SYMBOLS
from app.db.session import get_session
from app.schemas.no_trade_zone import NoTradeZoneResult
from app.schemas.setup_quality import SetupQualityResult
from app.services.indicators.base import klines_to_dataframe
from app.services.indicators.engine import indicator_engine
from app.services.quality.no_trade_zone import no_trade_zone_detector
from app.services.quality.setup_quality import setup_quality_engine

router = APIRouter(prefix="/analysis", tags=["analysis"])

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
