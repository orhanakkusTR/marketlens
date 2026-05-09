"""Indicator endpoints.

GET /api/v1/indicators/{symbol}/{timeframe} → IndicatorBundle (full)
GET /api/v1/levels/{symbol}/{timeframe}     → LevelsResult + Fibonacci

Auth: bu adımda public (slowapi rate limit aktif).
"""
from __future__ import annotations

from fastapi import APIRouter, Path, Request
from pydantic import BaseModel, ConfigDict

from app.core.exceptions import NotFoundError, ValidationError
from app.core.middleware import limiter
from app.data.binance_spot import TF_TO_INTERVAL
from app.schemas.indicators import (
    FibonacciResult,
    IndicatorBundle,
    LevelsResult,
)
from app.services.indicators.engine import indicator_engine

router = APIRouter(tags=["indicators"])

# Bilinen sembol listesi (CLAUDE.md — 26 kripto + GOLD spot Binance'ta yok)
KNOWN_CRYPTO_SYMBOLS: set[str] = {
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "AVAXUSDT", "ADAUSDT",
    "DOGEUSDT", "POLUSDT", "DOTUSDT", "LINKUSDT", "ATOMUSDT", "NEARUSDT", "APTUSDT",
    "ARBUSDT", "OPUSDT", "SHIBUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT", "UNIUSDT",
    "AAVEUSDT", "LDOUSDT", "INJUSDT", "SUIUSDT", "SEIUSDT",
}


def _validate(symbol: str, timeframe: str) -> str:
    symbol_upper = symbol.upper()
    if symbol_upper not in KNOWN_CRYPTO_SYMBOLS:
        raise NotFoundError(
            f"Bilinmeyen sembol: {symbol}",
            details={"known_symbols": sorted(KNOWN_CRYPTO_SYMBOLS)},
        )
    if timeframe not in TF_TO_INTERVAL:
        raise ValidationError(
            f"Geçersiz timeframe: {timeframe}",
            details={"valid": sorted(TF_TO_INTERVAL.keys())},
        )
    return symbol_upper


class LevelsBundle(BaseModel):
    """LevelsResult + Fibonacci ortak response."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    timeframe: str
    levels: LevelsResult
    fibonacci: FibonacciResult | None


@router.get("/indicators/{symbol}/{timeframe}", response_model=IndicatorBundle)
@limiter.limit("30/minute")
async def get_indicators(
    request: Request,
    symbol: str = Path(..., min_length=3, max_length=20),
    timeframe: str = Path(..., min_length=2, max_length=4),
) -> IndicatorBundle:
    """Bir sembol+TF için tüm indikatörleri hesapla (trend + momentum + volatility +
    volume + fibonacci + levels).

    Cache: TF'ye göre kline TTL'i (15m=60s, 1H=180s, 4H=600s, 1D=1800s, ...).
    Rate limit: 30 istek/dakika/IP.
    """
    symbol_upper = _validate(symbol, timeframe)
    return await indicator_engine.compute_all(symbol_upper, timeframe)


@router.get("/levels/{symbol}/{timeframe}", response_model=LevelsBundle)
@limiter.limit("30/minute")
async def get_levels(
    request: Request,
    symbol: str = Path(..., min_length=3, max_length=20),
    timeframe: str = Path(..., min_length=2, max_length=4),
) -> LevelsBundle:
    """Auto S/R level'ları + Fibonacci seviyeleri (sadece levels & fib)."""
    symbol_upper = _validate(symbol, timeframe)
    levels = await indicator_engine.compute_levels(symbol_upper, timeframe)
    fibonacci = await indicator_engine.compute_fibonacci(symbol_upper, timeframe)
    return LevelsBundle(
        symbol=symbol_upper,
        timeframe=timeframe,
        levels=levels,
        fibonacci=fibonacci,
    )
