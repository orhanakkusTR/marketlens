"""Macro endpoints (Adım 10 + 20 polish).

GET /api/v1/macro/snapshot       → MacroSnapshot (full)
GET /api/v1/macro/regime         → RegimeResult (sadece rejim, cache shared)
GET /api/v1/macro/regime-detail  → RegimeDetailResponse (composite, Adım 20 polish)

Auth: public (market data).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import limiter
from app.core.security import get_current_user_optional
from app.db.session import get_session
from app.models.user import User
from app.schemas.macro import MacroSnapshot, RegimeResult
from app.schemas.regime_detail import RegimeDetailResponse
from app.services.macro.context import macro_service
from app.services.macro.regime_detail import build_regime_detail

router = APIRouter(prefix="/macro", tags=["macro"])


@router.get("/snapshot", response_model=MacroSnapshot)
@limiter.limit("30/minute")
async def get_macro_snapshot(request: Request) -> MacroSnapshot:
    """Tüm macro metriklerini tek call'da: caps, BTC mcap, ETH/BTC, TradFi (6),
    F&G, market regime."""
    return await macro_service.get_snapshot()


@router.get("/regime", response_model=RegimeResult)
@limiter.limit("30/minute")
async def get_market_regime(request: Request) -> RegimeResult:
    """Şu anki market regime (5 sınıf, türkçe label, hangi trigger'lar aktif)."""
    return await macro_service.get_regime()


@router.get("/regime-detail", response_model=RegimeDetailResponse)
@limiter.limit("30/minute")
async def get_regime_detail(
    request: Request,
    timeframe: str = Query(default="4H", min_length=2, max_length=4),
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_current_user_optional),
) -> RegimeDetailResponse:
    """Rejim composite: macro özeti + 27 sembol setup distribution + Türkçe
    warnings + dinamik strateji önerisi. Cache 60s."""
    user_id = user.id if user else None
    return await build_regime_detail(session, user_id=user_id, timeframe=timeframe)
