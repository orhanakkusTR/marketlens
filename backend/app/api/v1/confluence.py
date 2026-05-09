"""Confluence endpoints.

GET /api/v1/confluence/local/{symbol}/{timeframe} → LocalConfluenceResult

Auth: bu adımda public (rate limit aktif).
"""
from __future__ import annotations

from fastapi import APIRouter, Path, Request

from app.core.exceptions import NotFoundError, ValidationError
from app.core.middleware import limiter
from app.data.binance_spot import TF_TO_INTERVAL
from app.schemas.confluence import LocalConfluenceResult
from app.services.indicators.engine import indicator_engine

router = APIRouter(prefix="/confluence", tags=["confluence"])

KNOWN_SYMBOLS: set[str] = {
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "AVAXUSDT", "ADAUSDT",
    "DOGEUSDT", "POLUSDT", "DOTUSDT", "LINKUSDT", "ATOMUSDT", "NEARUSDT", "APTUSDT",
    "ARBUSDT", "OPUSDT", "SHIBUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT", "UNIUSDT",
    "AAVEUSDT", "LDOUSDT", "INJUSDT", "SUIUSDT", "SEIUSDT", "GOLD",
}


@router.get("/local/{symbol}/{timeframe}", response_model=LocalConfluenceResult)
@limiter.limit("30/minute")
async def get_local_confluence(
    request: Request,
    symbol: str = Path(..., min_length=3, max_length=20),
    timeframe: str = Path(..., min_length=2, max_length=4),
) -> LocalConfluenceResult:
    """Lokal confluence skoru — 5 label + direction + component breakdown."""
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

    return await indicator_engine.compute_local_confluence(symbol_upper, timeframe)
