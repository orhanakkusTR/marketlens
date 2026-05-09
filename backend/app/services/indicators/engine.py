"""Indicator Engine — public facade.

Tüm CPU-bound hesapları thread pool'a wrap'ler, sonuçları Redis'e cache'ler.

Kullanım:
    from app.services.indicators.engine import indicator_engine
    bundle = await indicator_engine.compute_all("BTCUSDT", "4H")
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from app.core.cache import cached_call
from app.core.logging import get_logger
from app.data.binance_spot import TF_TO_INTERVAL, TF_TTL
from app.schemas.indicators import (
    IndicatorBundle,
    MomentumIndicators,
    TrendIndicators,
)
from app.services.data_service import data_service
from app.services.indicators.base import klines_to_dataframe, run_cpu_bound
from app.services.indicators.momentum.divergence import detect_divergence
from app.services.indicators.momentum.macd import (
    compute_macd,
    compute_macd_histogram_series,
)
from app.services.indicators.momentum.rsi import compute_rsi, compute_rsi_series
from app.services.indicators.momentum.stoch_rsi import compute_stoch_rsi
from app.services.indicators.trend.ichimoku import compute_ichimoku
from app.services.indicators.trend.market_structure import compute_market_structure
from app.services.indicators.trend.moving_averages import compute_moving_averages

logger = get_logger(__name__)

DEFAULT_KLINE_LIMIT = 300  # Ichimoku 52 + buffer + divergence için yeterli


def _compute_trend_sync(df: pd.DataFrame, timeframe: str) -> TrendIndicators:
    return TrendIndicators(
        moving_averages=compute_moving_averages(df, timeframe),
        ichimoku=compute_ichimoku(df),
        market_structure=compute_market_structure(df),
    )


def _compute_momentum_sync(df: pd.DataFrame) -> MomentumIndicators:
    rsi = compute_rsi(df, period=14, history_len=50)
    macd = compute_macd(df)
    stoch = compute_stoch_rsi(df)

    rsi_series = compute_rsi_series(df, period=14)
    macd_hist_series = compute_macd_histogram_series(df)

    div_rsi = detect_divergence(df, rsi_series, lookback_bars=100, min_swings=2)
    div_macd = detect_divergence(df, macd_hist_series, lookback_bars=100, min_swings=2)

    return MomentumIndicators(
        rsi=rsi,
        macd=macd,
        stoch_rsi=stoch,
        divergence_rsi=div_rsi,
        divergence_macd=div_macd,
    )


class IndicatorEngine:
    """Public facade. Singleton — main.py lifespan'de close edilir."""

    async def _get_klines(
        self, symbol: str, timeframe: str, limit: int = DEFAULT_KLINE_LIMIT
    ) -> list[dict[str, Any]]:
        return await data_service.get_klines(symbol, timeframe, limit)

    async def compute_trend(
        self,
        symbol: str,
        timeframe: str,
        klines: list[dict[str, Any]] | None = None,
    ) -> TrendIndicators:
        if timeframe not in TF_TO_INTERVAL:
            raise ValueError(f"Bilinmeyen timeframe: {timeframe}")

        async def fetch() -> dict[str, Any]:
            kl = klines if klines is not None else await self._get_klines(symbol, timeframe)
            df = klines_to_dataframe(kl)
            result = await run_cpu_bound(_compute_trend_sync, df, timeframe)
            return result.model_dump(mode="json")

        if klines is not None:
            # External klines verildi → cache atla, doğrudan hesapla
            df = klines_to_dataframe(klines)
            return await run_cpu_bound(_compute_trend_sync, df, timeframe)

        raw = await cached_call(
            key=f"indicators:{symbol}:{timeframe}:trend",
            ttl=TF_TTL[timeframe],
            fetch_fn=fetch,
        )
        return TrendIndicators.model_validate(raw)

    async def compute_momentum(
        self,
        symbol: str,
        timeframe: str,
        klines: list[dict[str, Any]] | None = None,
    ) -> MomentumIndicators:
        if timeframe not in TF_TO_INTERVAL:
            raise ValueError(f"Bilinmeyen timeframe: {timeframe}")

        async def fetch() -> dict[str, Any]:
            kl = klines if klines is not None else await self._get_klines(symbol, timeframe)
            df = klines_to_dataframe(kl)
            result = await run_cpu_bound(_compute_momentum_sync, df)
            return result.model_dump(mode="json")

        if klines is not None:
            df = klines_to_dataframe(klines)
            return await run_cpu_bound(_compute_momentum_sync, df)

        raw = await cached_call(
            key=f"indicators:{symbol}:{timeframe}:momentum",
            ttl=TF_TTL[timeframe],
            fetch_fn=fetch,
        )
        return MomentumIndicators.model_validate(raw)

    async def compute_all(
        self,
        symbol: str,
        timeframe: str,
    ) -> IndicatorBundle:
        if timeframe not in TF_TO_INTERVAL:
            raise ValueError(f"Bilinmeyen timeframe: {timeframe}")

        async def fetch() -> dict[str, Any]:
            klines = await self._get_klines(symbol, timeframe)
            df = klines_to_dataframe(klines)

            def _compute() -> dict[str, Any]:
                trend = _compute_trend_sync(df, timeframe)
                momentum = _compute_momentum_sync(df)
                bundle = IndicatorBundle(
                    symbol=symbol,
                    timeframe=timeframe,
                    computed_at=datetime.now(UTC),
                    kline_count=len(df),
                    trend=trend,
                    momentum=momentum,
                )
                return bundle.model_dump(mode="json")

            return await run_cpu_bound(_compute)

        raw = await cached_call(
            key=f"indicators:{symbol}:{timeframe}:all",
            ttl=TF_TTL[timeframe],
            fetch_fn=fetch,
        )
        # cached_call JSON serialize ettiği için datetime string olarak döner — Pydantic parse eder
        return IndicatorBundle.model_validate(raw)

    async def close(self) -> None:
        # Engine kendi resource tutmuyor (data_service ayrıca close edilir)
        pass


# Modül seviyesi singleton
indicator_engine = IndicatorEngine()


__all__ = ["IndicatorEngine", "indicator_engine"]
