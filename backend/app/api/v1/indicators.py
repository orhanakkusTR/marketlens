"""Indicator endpoints.

GET /api/v1/indicators/{symbol}/{timeframe}?modules=trend,momentum → IndicatorBundle
GET /api/v1/levels/{symbol}/{timeframe}     → LevelsResult + Fibonacci

Auth: bu adımda public (slowapi rate limit aktif).
"""
from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Path, Query, Request
from pydantic import BaseModel, ConfigDict

from app.core.exceptions import NotFoundError, ValidationError
from app.core.middleware import limiter
from app.data.binance_spot import TF_TO_INTERVAL
from app.schemas.indicators import (
    FibonacciResult,
    IndicatorBundle,
    LevelsResult,
    ModuleName,
)
from app.services.indicators.engine import ALL_MODULES, indicator_engine

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
    modules: str | None = Query(
        None,
        description=(
            "Virgülle ayrılmış modül listesi (örn. 'trend,momentum,futures'). "
            f"Boş bırakılırsa hepsi. İzin verilen: {', '.join(ALL_MODULES)}"
        ),
    ),
) -> IndicatorBundle:
    """Bir sembol+TF için indikatör bundle'ı.

    - Tüm modüller: `?modules` boş veya hiç gönderme
    - Seçili modüller: `?modules=trend,momentum,futures`
    - Module bazlı cache + bundle compose: seçim performansı azaltmaz
    """
    symbol_upper = _validate(symbol, timeframe)

    selected: list[ModuleName] | None = None
    if modules is not None:
        raw = [m.strip() for m in modules.split(",") if m.strip()]
        invalid = [m for m in raw if m not in ALL_MODULES]
        if invalid:
            raise ValidationError(
                f"Geçersiz modül(ler): {', '.join(invalid)}",
                details={"valid": list(ALL_MODULES)},
            )
        selected = cast("list[ModuleName]", raw)

    return await indicator_engine.compute_all(symbol_upper, timeframe, modules=selected)


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
