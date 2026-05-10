"""Multi-TF Alignment endpoint.

GET /api/v1/alignment/{symbol} → AlignmentResult (6 TF için ağırlıklı toplam)
"""
from __future__ import annotations

from fastapi import APIRouter, Path, Request

from app.core.exceptions import NotFoundError
from app.core.middleware import limiter
from app.schemas.confluence import AlignmentResult
from app.services.indicators.engine import indicator_engine

router = APIRouter(prefix="/alignment", tags=["alignment"])

KNOWN_SYMBOLS: set[str] = {
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "AVAXUSDT", "ADAUSDT",
    "DOGEUSDT", "POLUSDT", "DOTUSDT", "LINKUSDT", "ATOMUSDT", "NEARUSDT", "APTUSDT",
    "ARBUSDT", "OPUSDT", "SHIBUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT", "UNIUSDT",
    "AAVEUSDT", "LDOUSDT", "INJUSDT", "SUIUSDT", "SEIUSDT",
}


@router.get("/{symbol}", response_model=AlignmentResult)
@limiter.limit("30/minute")
async def get_alignment(
    request: Request,
    symbol: str = Path(..., min_length=3, max_length=20),
) -> AlignmentResult:
    """6 TF için final score'ların ağırlıklı toplamı + label + consistent_direction.

    Ağırlıklar: 15m 0.05, 1H 0.10, 4H 0.25, 1D 0.30, 1W 0.20, 1M 0.10.
    Label: strong (|score|>70), aligned (>40), weak (>20), conflicted (≤20 veya yön çelişkisi).
    """
    symbol_upper = symbol.upper()
    if symbol_upper not in KNOWN_SYMBOLS:
        raise NotFoundError(
            f"Bilinmeyen sembol: {symbol}",
            details={"known": sorted(KNOWN_SYMBOLS)},
        )
    return await indicator_engine.compute_multi_tf_alignment(symbol_upper)
