"""Setup Quality endpoint (Adım 13).

GET /api/v1/analysis/quality/{symbol}/{tf} → SetupQualityResult
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.middleware import limiter
from app.data.binance_spot import TF_TO_INTERVAL
from app.data.symbols_meta import ALL_SYMBOLS
from app.db.session import get_session
from app.schemas.setup_quality import SetupQualityResult
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
