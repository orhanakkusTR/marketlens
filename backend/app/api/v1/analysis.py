"""Analysis Orchestrator endpoint — Adım 17.

GET /api/v1/analysis/full/{symbol}/{timeframe} → AnalysisFullResult

Frontend Adım 18+ için tek istek = tüm dashboard verisi.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    MarketLensError,
    NotFoundError,
    ValidationError,
)
from app.core.middleware import limiter
from app.core.security import get_current_user_optional
from app.data.binance_spot import TF_TO_INTERVAL
from app.data.symbols_meta import ALL_SYMBOLS
from app.db.session import get_session
from app.models.user import User
from app.schemas.analysis import AnalysisFullResult
from app.services.analysis.orchestrator import (
    CoreAnalysisError,
    analysis_orchestrator,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])

KNOWN_SYMBOLS: frozenset[str] = frozenset(ALL_SYMBOLS)


class CoreUnavailableError(MarketLensError):
    """Phase 1 core fail → 503."""

    status_code = 503
    error_code = "core_unavailable"


@router.get("/full/{symbol}/{timeframe}", response_model=AnalysisFullResult)
@limiter.limit("30/minute")
async def get_full_analysis(
    request: Request,
    symbol: str = Path(..., min_length=3, max_length=20),
    timeframe: str = Path(..., min_length=2, max_length=4),
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_current_user_optional),
) -> AnalysisFullResult:
    """Tüm modüllerin composite analizi (frontend için tek endpoint).

    İçerik:
    - indicators (trend + momentum + volatility + volume + fibonacci + levels + futures)
    - final_confluence + multi_tf_alignment
    - setup_quality (içinde scenario + no_trade + confidence + counter_trend + trade_quality)
    - macro (opsiyonel — fail → None + warning)
    - correlations (GOLD veya tek-sembol fail → None)
    - risk_position (scenario None → None, normal davranış)

    Cache: 30s TTL, user_id key'e gömülü (smart reduction user-specific).
    Phase 1 core fail → 503.
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

    try:
        return await analysis_orchestrator.compute_full_analysis(
            symbol_upper,
            timeframe,
            session=session,
            user_id=user.id if user else None,
        )
    except CoreAnalysisError as e:
        raise CoreUnavailableError(
            "Sembol analizi şu an mümkün değil — birkaç saniye sonra tekrar deneyin.",
            details={"reason": str(e), "symbol": symbol_upper, "timeframe": timeframe},
        ) from e
