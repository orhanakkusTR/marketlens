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
    FibonacciResult,
    IndicatorBundle,
    LevelsResult,
    MomentumIndicators,
    TrendIndicators,
    VolatilityIndicators,
    VolumeIndicators,
)
from app.services.data_service import data_service
from app.services.indicators.base import klines_to_dataframe, run_cpu_bound
from app.services.indicators.fibonacci.auto_fib import compute_fibonacci
from app.services.indicators.levels.auto_sr import compute_levels as _compute_levels_fn
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
from app.services.indicators.volatility.atr import compute_atr
from app.services.indicators.volatility.bollinger import compute_bollinger
from app.services.indicators.volume.obv import compute_obv
from app.services.indicators.volume.volume_profile import compute_volume_profile
from app.services.indicators.volume.vwap import compute_vwap

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


def _compute_volatility_sync(df: pd.DataFrame) -> VolatilityIndicators:
    return VolatilityIndicators(
        atr=compute_atr(df, period=14),
        bollinger=compute_bollinger(df, length=20, std=2.0),
    )


def _compute_volume_sync(df: pd.DataFrame, timeframe: str) -> VolumeIndicators:
    return VolumeIndicators(
        obv=compute_obv(df),
        vwap=compute_vwap(df, timeframe),
        volume_profile=compute_volume_profile(df, timeframe),
    )


def _compute_fibonacci_sync(df: pd.DataFrame) -> FibonacciResult | None:
    return compute_fibonacci(df)


def _compute_levels_sync(
    df: pd.DataFrame, timeframe: str, fibonacci: FibonacciResult | None = None
) -> LevelsResult:
    """Levels = market_structure + fibonacci + volume_profile + round numbers."""
    market_structure = compute_market_structure(df)
    if fibonacci is None:
        fibonacci = compute_fibonacci(df)
    volume_profile = compute_volume_profile(df, timeframe)
    return _compute_levels_fn(df, market_structure, fibonacci, volume_profile)


class IndicatorEngine:
    """Public facade. Singleton — main.py lifespan'de close edilir."""

    async def _get_klines(
        self, symbol: str, timeframe: str, limit: int = DEFAULT_KLINE_LIMIT
    ) -> list[dict[str, Any]]:
        return await data_service.get_klines(symbol, timeframe, limit)

    # ── trend ──
    async def compute_trend(
        self,
        symbol: str,
        timeframe: str,
        klines: list[dict[str, Any]] | None = None,
    ) -> TrendIndicators:
        if timeframe not in TF_TO_INTERVAL:
            raise ValueError(f"Bilinmeyen timeframe: {timeframe}")

        if klines is not None:
            df = klines_to_dataframe(klines)
            return await run_cpu_bound(_compute_trend_sync, df, timeframe)

        async def fetch() -> dict[str, Any]:
            kl = await self._get_klines(symbol, timeframe)
            df = klines_to_dataframe(kl)
            result = await run_cpu_bound(_compute_trend_sync, df, timeframe)
            return result.model_dump(mode="json")

        raw = await cached_call(
            key=f"indicators:{symbol}:{timeframe}:trend",
            ttl=TF_TTL[timeframe],
            fetch_fn=fetch,
        )
        return TrendIndicators.model_validate(raw)

    # ── momentum ──
    async def compute_momentum(
        self,
        symbol: str,
        timeframe: str,
        klines: list[dict[str, Any]] | None = None,
    ) -> MomentumIndicators:
        if timeframe not in TF_TO_INTERVAL:
            raise ValueError(f"Bilinmeyen timeframe: {timeframe}")

        if klines is not None:
            df = klines_to_dataframe(klines)
            return await run_cpu_bound(_compute_momentum_sync, df)

        async def fetch() -> dict[str, Any]:
            kl = await self._get_klines(symbol, timeframe)
            df = klines_to_dataframe(kl)
            result = await run_cpu_bound(_compute_momentum_sync, df)
            return result.model_dump(mode="json")

        raw = await cached_call(
            key=f"indicators:{symbol}:{timeframe}:momentum",
            ttl=TF_TTL[timeframe],
            fetch_fn=fetch,
        )
        return MomentumIndicators.model_validate(raw)

    # ── volatility ──
    async def compute_volatility(
        self,
        symbol: str,
        timeframe: str,
        klines: list[dict[str, Any]] | None = None,
    ) -> VolatilityIndicators:
        if timeframe not in TF_TO_INTERVAL:
            raise ValueError(f"Bilinmeyen timeframe: {timeframe}")

        if klines is not None:
            df = klines_to_dataframe(klines)
            return await run_cpu_bound(_compute_volatility_sync, df)

        async def fetch() -> dict[str, Any]:
            kl = await self._get_klines(symbol, timeframe)
            df = klines_to_dataframe(kl)
            result = await run_cpu_bound(_compute_volatility_sync, df)
            return result.model_dump(mode="json")

        raw = await cached_call(
            key=f"indicators:{symbol}:{timeframe}:volatility",
            ttl=TF_TTL[timeframe],
            fetch_fn=fetch,
        )
        return VolatilityIndicators.model_validate(raw)

    # ── volume ──
    async def compute_volume(
        self,
        symbol: str,
        timeframe: str,
        klines: list[dict[str, Any]] | None = None,
    ) -> VolumeIndicators:
        if timeframe not in TF_TO_INTERVAL:
            raise ValueError(f"Bilinmeyen timeframe: {timeframe}")

        if klines is not None:
            df = klines_to_dataframe(klines)
            return await run_cpu_bound(_compute_volume_sync, df, timeframe)

        async def fetch() -> dict[str, Any]:
            kl = await self._get_klines(symbol, timeframe)
            df = klines_to_dataframe(kl)
            result = await run_cpu_bound(_compute_volume_sync, df, timeframe)
            return result.model_dump(mode="json")

        raw = await cached_call(
            key=f"indicators:{symbol}:{timeframe}:volume",
            ttl=TF_TTL[timeframe],
            fetch_fn=fetch,
        )
        return VolumeIndicators.model_validate(raw)

    # ── fibonacci ──
    async def compute_fibonacci(
        self,
        symbol: str,
        timeframe: str,
        klines: list[dict[str, Any]] | None = None,
    ) -> FibonacciResult | None:
        if timeframe not in TF_TO_INTERVAL:
            raise ValueError(f"Bilinmeyen timeframe: {timeframe}")

        if klines is not None:
            df = klines_to_dataframe(klines)
            return await run_cpu_bound(_compute_fibonacci_sync, df)

        async def fetch() -> dict[str, Any] | None:
            kl = await self._get_klines(symbol, timeframe)
            df = klines_to_dataframe(kl)
            result = await run_cpu_bound(_compute_fibonacci_sync, df)
            return result.model_dump(mode="json") if result is not None else None

        raw = await cached_call(
            key=f"indicators:{symbol}:{timeframe}:fibonacci",
            ttl=TF_TTL[timeframe],
            fetch_fn=fetch,
        )
        if raw is None:
            return None
        return FibonacciResult.model_validate(raw)

    # ── levels ──
    async def compute_levels(
        self,
        symbol: str,
        timeframe: str,
        klines: list[dict[str, Any]] | None = None,
    ) -> LevelsResult:
        if timeframe not in TF_TO_INTERVAL:
            raise ValueError(f"Bilinmeyen timeframe: {timeframe}")

        if klines is not None:
            df = klines_to_dataframe(klines)
            return await run_cpu_bound(_compute_levels_sync, df, timeframe)

        async def fetch() -> dict[str, Any]:
            kl = await self._get_klines(symbol, timeframe)
            df = klines_to_dataframe(kl)
            result = await run_cpu_bound(_compute_levels_sync, df, timeframe)
            return result.model_dump(mode="json")

        raw = await cached_call(
            key=f"indicators:{symbol}:{timeframe}:levels",
            ttl=TF_TTL[timeframe],
            fetch_fn=fetch,
        )
        return LevelsResult.model_validate(raw)

    # ── full bundle ──
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
                volatility = _compute_volatility_sync(df)
                volume = _compute_volume_sync(df, timeframe)
                fibonacci = _compute_fibonacci_sync(df)
                # Levels için market_structure ve volume_profile zaten ayrı hesaplandı
                # ama _compute_levels_sync kendi içinde tekrar çağırıyor — kabul edilebilir
                # (yine de cache_all'da tek seferlik). Optimize için ayrı yardımcı:
                # Levels: trend.market_structure + volume.volume_profile + fibonacci'yi
                # tekrar hesaplamadan reuse et
                levels = _compute_levels_fn(
                    df,
                    trend.market_structure,
                    fibonacci,
                    volume.volume_profile,
                )

                bundle = IndicatorBundle(
                    symbol=symbol,
                    timeframe=timeframe,
                    computed_at=datetime.now(UTC),
                    kline_count=len(df),
                    trend=trend,
                    momentum=momentum,
                    volatility=volatility,
                    volume=volume,
                    fibonacci=fibonacci,
                    levels=levels,
                )
                return bundle.model_dump(mode="json")

            return await run_cpu_bound(_compute)

        raw = await cached_call(
            key=f"indicators:{symbol}:{timeframe}:all",
            ttl=TF_TTL[timeframe],
            fetch_fn=fetch,
        )
        return IndicatorBundle.model_validate(raw)

    async def close(self) -> None:
        # Engine kendi resource tutmuyor (data_service ayrıca close edilir)
        pass


# Modül seviyesi singleton
indicator_engine = IndicatorEngine()


__all__ = ["IndicatorEngine", "indicator_engine"]
