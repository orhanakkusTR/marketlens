"""Macro endpoints (Adım 10).

GET /api/v1/macro/snapshot   → MacroSnapshot (full)
GET /api/v1/macro/regime     → RegimeResult (sadece rejim, cache shared)

Auth: public (market data).
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.middleware import limiter
from app.schemas.macro import MacroSnapshot, RegimeResult
from app.services.macro.context import macro_service

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
