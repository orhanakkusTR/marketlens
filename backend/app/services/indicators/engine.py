"""Indicator Engine — public facade.

Modül tipleri: trend, momentum, volatility, volume, fibonacci, levels, futures.

compute_all(symbol, tf, modules=None) — modules=None ise hepsi; aksi halde
sadece seçilenler. Module bazlı separate cache + bundle compose mantığı.

Cache key:
    indicators:{symbol}:{tf}:{kind}     # kind: trend|momentum|volatility|volume|fibonacci|levels
    indicators:{symbol}:futures         # TF-bağımsız (snapshot)
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from app.core.cache import cached_call
from app.core.logging import get_logger
from app.data.binance_spot import TF_TO_INTERVAL, TF_TTL
from app.data.symbols_meta import has_futures as _has_futures
from app.schemas.indicators import (
    FibonacciResult,
    FuturesIndicators,
    IndicatorBundle,
    LevelsResult,
    ModuleName,
    MomentumIndicators,
    TrendIndicators,
    VolatilityIndicators,
    VolumeIndicators,
)
from app.services.data_service import data_service
from app.services.indicators.base import klines_to_dataframe, run_cpu_bound
from app.services.indicators.fibonacci.auto_fib import compute_fibonacci
from app.services.indicators.futures.funding_analysis import (
    compute_funding_analysis,
)
from app.services.indicators.futures.long_short_anomaly import compute_ls_anomaly
from app.services.indicators.futures.oi_change import compute_oi_change
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

DEFAULT_KLINE_LIMIT = 300
FUTURES_CACHE_TTL = 300  # 5dk
LS_PERIOD = "1h"
OI_PERIOD = "5m"

ALL_MODULES: tuple[ModuleName, ...] = (
    "trend",
    "momentum",
    "volatility",
    "volume",
    "fibonacci",
    "levels",
    "futures",
)


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
    market_structure = compute_market_structure(df)
    if fibonacci is None:
        fibonacci = compute_fibonacci(df)
    volume_profile = compute_volume_profile(df, timeframe)
    return _compute_levels_fn(df, market_structure, fibonacci, volume_profile)


def _compute_futures_sync(
    funding_now: dict[str, Any],
    funding_history: list[dict[str, Any]],
    oi_history: list[dict[str, Any]],
    ls_data: list[dict[str, Any]],
) -> FuturesIndicators:
    funding = compute_funding_analysis(
        funding_history,
        current_rate=float(funding_now["funding_rate"]),
        next_funding_time=int(funding_now["next_funding_time"]),
    )
    oi = compute_oi_change(oi_history)
    ls = compute_ls_anomaly(ls_data, period=LS_PERIOD)
    return FuturesIndicators(funding=funding, open_interest=oi, long_short=ls)


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

    # ── futures (TF-bağımsız) ──
    async def compute_futures(self, symbol: str) -> FuturesIndicators | None:
        """has_futures=False ise None. Cache: indicators:{symbol}:futures (TF yok)."""
        if not _has_futures(symbol):
            return None

        async def fetch() -> dict[str, Any]:
            funding_now = await data_service.get_funding(symbol)
            funding_history = await data_service.get_funding_history(symbol, limit=24)
            oi_history = await data_service.get_oi_history(
                symbol, period=OI_PERIOD, limit=300
            )
            ls_data = await data_service.get_long_short_ratio(symbol, period=LS_PERIOD)
            result = await run_cpu_bound(
                _compute_futures_sync,
                funding_now,
                funding_history,
                oi_history,
                ls_data,
            )
            return result.model_dump(mode="json")

        raw = await cached_call(
            key=f"indicators:{symbol}:futures",
            ttl=FUTURES_CACHE_TTL,
            fetch_fn=fetch,
        )
        return FuturesIndicators.model_validate(raw)

    # ── full bundle (with module selector) ──
    async def compute_all(
        self,
        symbol: str,
        timeframe: str,
        modules: list[ModuleName] | None = None,
    ) -> IndicatorBundle:
        """Tüm istenen modülleri parallel-friendly compose eder.

        modules=None → hepsi. Aksi halde sadece seçilenler hesaplanır,
        diğer alanlar None olarak döner. Module bazlı cache key kullanılır.
        """
        if timeframe not in TF_TO_INTERVAL:
            raise ValueError(f"Bilinmeyen timeframe: {timeframe}")

        selected = set(modules) if modules else set(ALL_MODULES)
        unknown = selected - set(ALL_MODULES)
        if unknown:
            raise ValueError(f"Bilinmeyen modüller: {unknown}")

        # Bireysel module compute'ları (cache'li). Hepsi None'dan başlar.
        trend: TrendIndicators | None = None
        momentum: MomentumIndicators | None = None
        volatility: VolatilityIndicators | None = None
        volume: VolumeIndicators | None = None
        fibonacci: FibonacciResult | None = None
        levels: LevelsResult | None = None
        futures: FuturesIndicators | None = None

        if "trend" in selected:
            trend = await self.compute_trend(symbol, timeframe)
        if "momentum" in selected:
            momentum = await self.compute_momentum(symbol, timeframe)
        if "volatility" in selected:
            volatility = await self.compute_volatility(symbol, timeframe)
        if "volume" in selected:
            volume = await self.compute_volume(symbol, timeframe)
        if "fibonacci" in selected or "levels" in selected:
            fibonacci = await self.compute_fibonacci(symbol, timeframe)
        if "levels" in selected:
            levels = await self.compute_levels(symbol, timeframe)
        if "futures" in selected:
            futures = await self.compute_futures(symbol)

        # kline_count: trend hesaplandıysa oradan, yoksa standalone fetch
        kline_count = DEFAULT_KLINE_LIMIT
        if trend is None and "trend" not in selected:
            # Lightweight: kline_count için gerçek değeri almak yerine default
            # (bu alan informational; full bundle için trend zaten hep çağrılır)
            pass

        return IndicatorBundle(
            symbol=symbol,
            timeframe=timeframe,
            computed_at=datetime.now(UTC),
            kline_count=kline_count,
            trend=trend,
            momentum=momentum,
            volatility=volatility,
            volume=volume,
            fibonacci=fibonacci,
            levels=levels,
            futures=futures,
        )

    async def close(self) -> None:
        # Engine kendi resource tutmuyor (data_service ayrıca close edilir)
        pass


# Modül seviyesi singleton
indicator_engine = IndicatorEngine()


__all__ = ["IndicatorEngine", "indicator_engine", "ALL_MODULES"]
