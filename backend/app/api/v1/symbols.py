"""Sembol toplu durum endpoint'leri — Adım 19.

GET /api/v1/symbols/grades → 27 sembol için lightweight grade+direction snapshot.

Cache:
- Endpoint-level: 60s (tek Redis fetch hot path)
- Per-symbol: zaten setup_quality 60s TTL (cold start için fallback)

XAUUSDT senaryosu: setup_quality CoreAnalysisError raise eder (Ichimoku
mum sayısı yetersiz, yeni listelendi). error field doldurulur, grade null.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cached_call
from app.core.logging import get_logger
from app.core.middleware import limiter
from app.core.security import get_current_user_optional
from app.data.binance_spot import TF_TO_INTERVAL
from app.data.symbols_meta import ALL_SYMBOLS
from app.db.session import get_session
from app.models.user import User
from app.schemas.symbols import GradesResponse, GradeSummary
from app.services.quality.setup_quality import setup_quality_engine

logger = get_logger(__name__)

router = APIRouter(prefix="/symbols", tags=["symbols"])

CACHE_TTL = 60  # saniye — frontend refetch interval'iyla aynı


def _summarize(symbol: str, payload: dict[str, Any] | None, error: str | None) -> GradeSummary:
    if error or payload is None:
        return GradeSummary(symbol=symbol, error=error or "Bilinmeyen hata")
    no_trade = payload.get("no_trade_zones") or {}
    return GradeSummary(
        symbol=symbol,
        grade=payload.get("grade"),
        direction=payload.get("direction"),
        final_score=payload.get("final_score"),
        is_blocking=bool(no_trade.get("is_blocking", False)),
        error=None,
    )


async def _evaluate_one(
    symbol: str, timeframe: str, session: AsyncSession, user_id: Any
) -> tuple[str, dict[str, Any] | None, str | None]:
    """Tek sembol için setup_quality.evaluate — exception → error string."""
    try:
        result = await setup_quality_engine.evaluate(
            symbol, timeframe, session=session, user_id=user_id
        )
        return symbol, result.model_dump(mode="json"), None
    except Exception as e:
        msg = str(e)
        # Türkçe kısaltma
        if "Ichimoku" in msg or "yeterli" in msg.lower() or "mum" in msg.lower():
            short = "Yetersiz veri (yeni listelendi)"
        elif "400 Bad Request" in msg or "404" in msg:
            short = "Sembol verisi bulunamadı"
        else:
            short = "Hesaplanamadı"
        logger.warning(
            "grades_symbol_failed", symbol=symbol, timeframe=timeframe, error=msg
        )
        return symbol, None, short


@router.get("/grades", response_model=GradesResponse)
@limiter.limit("30/minute")
async def get_all_grades(
    request: Request,
    timeframe: str = Query(default="4H", min_length=2, max_length=4),
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_current_user_optional),
) -> GradesResponse:
    """27 sembol için grade/direction snapshot.

    Endpoint cache 60s + per-symbol cache 60s (alt katmandaki setup_quality).
    Cache miss durumunda 27 sembol asyncio.gather ile paralel hesaplanır.
    """
    if timeframe not in TF_TO_INTERVAL:
        # default 4H her zaman geçerli; kullanıcı yanlış parametre verirse
        timeframe = "4H"

    user_id = user.id if user else None
    user_key = str(user_id) if user_id is not None else "anonymous"
    cache_key = f"symbols:grades:{timeframe}:{user_key}"

    async def _build() -> dict[str, Any]:
        # 27 sembol paralel
        tasks = [
            _evaluate_one(sym, timeframe, session, user_id) for sym in ALL_SYMBOLS
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        items = [_summarize(sym, payload, err) for sym, payload, err in results]
        response = GradesResponse(
            computed_at=datetime.now(UTC),
            timeframe=timeframe,
            items=items,
        )
        return response.model_dump(mode="json")

    raw = await cached_call(key=cache_key, ttl=CACHE_TTL, fetch_fn=_build)
    return GradesResponse.model_validate(raw)
