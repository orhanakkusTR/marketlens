"""Korelasyon endpoints (Adım 12).

GET /api/v1/correlations/matrix?period_days=30&tf=1D    → CorrelationMatrix
GET /api/v1/correlations/{symbol}?period_days=30&tf=1D  → SymbolCorrelations

Auth: public (market data, rate limit aktif).
"""
from __future__ import annotations

from fastapi import APIRouter, Path, Query, Request

from app.core.exceptions import NotFoundError, ValidationError
from app.core.middleware import limiter
from app.data.symbols_meta import ALL_SYMBOLS
from app.schemas.correlation import CorrelationMatrix, SymbolCorrelations
from app.services.correlation.engine import correlation_engine

router = APIRouter(prefix="/correlations", tags=["correlations"])

KNOWN_SYMBOLS: frozenset[str] = frozenset(ALL_SYMBOLS)


def _validate_params(period_days: int, tf: str) -> None:
    if not 7 <= period_days <= 180:
        raise ValidationError(
            f"period_days 7-180 aralığında olmalı (verildi: {period_days})",
            details={"min": 7, "max": 180},
        )
    if tf != "1D":
        raise ValidationError(
            f"Şimdilik sadece 1D destekleniyor (verildi: {tf})",
            details={"supported": ["1D"]},
        )


@router.get("/matrix", response_model=CorrelationMatrix)
@limiter.limit("30/minute")
async def get_correlation_matrix(
    request: Request,
    period_days: int = Query(30, ge=7, le=180),
    tf: str = Query("1D"),
) -> CorrelationMatrix:
    """Full 27 sembol + 3 tradfi korelasyon matrisi (kare, simetrik)."""
    _validate_params(period_days, tf)
    return await correlation_engine.compute_matrix(period_days, tf)


@router.get("/{symbol}", response_model=SymbolCorrelations)
@limiter.limit("30/minute")
async def get_symbol_correlations(
    request: Request,
    symbol: str = Path(..., min_length=3, max_length=20),
    period_days: int = Query(30, ge=7, le=180),
    tf: str = Query("1D"),
) -> SymbolCorrelations:
    """Tek sembolün diğer 26 sembol + tradfi referanslarıyla korelasyonu.

    Response içinde:
    - all: abs(r) desc sıralı
    - strong/moderate/weak/decoupled: kategorize listeler
    - by_sector_avg: sektör başına ortalama
    - vs_btc / vs_eth / vs_dxy / vs_sp500: cross-asset
    """
    symbol_upper = symbol.upper()
    if symbol_upper not in KNOWN_SYMBOLS:
        raise NotFoundError(
            f"Bilinmeyen sembol: {symbol}",
            details={"known": sorted(KNOWN_SYMBOLS)},
        )
    _validate_params(period_days, tf)
    return await correlation_engine.get_symbol_correlations(
        symbol_upper, period_days, tf
    )
