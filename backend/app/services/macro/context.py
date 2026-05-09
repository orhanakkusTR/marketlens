"""MacroService — tüm macro metrikleri toplu çek.

Paralel fetch:
- CoinGecko global (current caps + dominance)
- CoinGecko BTC market cap history (30 gün)
- yfinance × 6 (DXY, SP500, NASDAQ, VIX, US10Y, GOLD) — her biri 30d daily
- Binance ETHUSDT/BTCUSDT 1D klines (30 bar) → ETH/BTC ratio
- Alternative.me F&G history (8 günlük)

Cache: marketlens:macro:snapshot, TTL 300sn (5dk — spec).
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from app.core.cache import cached_call
from app.core.logging import get_logger
from app.schemas.macro import (
    CryptoCapsSnapshot,
    FearGreedSnapshot,
    MacroSnapshot,
    MetricTrend,
)
from app.services.data_service import data_service
from app.services.macro.regime import detect_market_regime
from app.services.macro.trends import compute_metric_trend, yfinance_history_to_series

logger = get_logger(__name__)

CACHE_KEY = "macro:snapshot"
CACHE_TTL = 300  # 5 dk

YF_SYMBOLS: tuple[str, ...] = ("DXY", "SP500", "NASDAQ", "VIX", "US10Y", "GOLD")


async def _fetch_yf_trend(symbol: str) -> MetricTrend:
    history = await data_service.get_yfinance_history(
        symbol, period="35d", interval="1d"
    )
    series = yfinance_history_to_series(history)
    if not series:
        # Fallback — current price ile boş trend
        current = await _safe_current_yf(symbol)
        return MetricTrend(
            current=current,
            change_24h_pct=None,
            change_7d_pct=None,
            change_30d_pct=None,
            direction_24h="flat",
            direction_7d="flat",
            direction_30d="flat",
        )
    return compute_metric_trend(series, bars_per_day=1)


async def _safe_current_yf(symbol: str) -> float:
    try:
        return await data_service.yfinance.get_current_price(symbol)
    except Exception:
        return 0.0


async def _fetch_btc_mcap_trend() -> MetricTrend:
    series = await data_service.get_btc_market_cap_history(days=30)
    if not series:
        raise RuntimeError("BTC market cap history boş")
    return compute_metric_trend(series, bars_per_day=1)


async def _fetch_eth_btc_trend() -> MetricTrend:
    """ETHUSDT/BTCUSDT 1D klines → ratio per bar."""
    eth_klines = await data_service.get_klines("ETHUSDT", "1D", limit=35)
    btc_klines = await data_service.get_klines("BTCUSDT", "1D", limit=35)

    # Aynı timestamp'lar üzerinden eşleştir (basitleştirme: pozisyona göre)
    n = min(len(eth_klines), len(btc_klines))
    if n == 0:
        raise RuntimeError("ETH/BTC kline yetersiz")

    series: list[tuple[int, float]] = []
    for i in range(-n, 0):
        eth_close = float(eth_klines[i]["close"])
        btc_close = float(btc_klines[i]["close"])
        if btc_close <= 0:
            continue
        ratio = eth_close / btc_close
        ts = int(eth_klines[i]["close_time"])
        series.append((ts, ratio))

    return compute_metric_trend(series, bars_per_day=1)


async def _fetch_crypto_caps() -> CryptoCapsSnapshot:
    cg = data_service.coingecko
    total = await cg.get_total()
    total2 = await cg.get_total2()
    total3 = await cg.get_total3()
    btc_d = await cg.get_btc_dominance()
    eth_d = await cg.get_eth_dominance()
    return CryptoCapsSnapshot(
        total=total,
        total2=total2,
        total3=total3,
        btc_dominance=btc_d,
        eth_dominance=eth_d,
    )


async def _fetch_fear_greed() -> FearGreedSnapshot:
    history = await data_service.get_fear_greed_history(limit=8)
    if not history:
        # Fallback — current only
        cur = await data_service.get_fear_greed()
        return FearGreedSnapshot(
            value=int(cur["value"]),
            classification=cur["classification"],
            timestamp=str(cur["timestamp"]),
            value_7d_ago=None,
            change_7d=None,
        )

    current = history[-1]
    value_7d_ago: int | None = None
    if len(history) >= 8:
        value_7d_ago = int(history[0]["value"])
    change_7d: int | None = None
    if value_7d_ago is not None:
        change_7d = int(current["value"]) - value_7d_ago

    return FearGreedSnapshot(
        value=int(current["value"]),
        classification=current["classification"],
        timestamp=str(current["timestamp"]),
        value_7d_ago=value_7d_ago,
        change_7d=change_7d,
    )


async def _build_snapshot() -> MacroSnapshot:
    """Tüm metrikleri paralel çek, snapshot oluştur."""
    (
        crypto_caps,
        btc_mcap,
        eth_btc,
        dxy,
        sp500,
        nasdaq,
        vix,
        us10y,
        gold,
        fear_greed,
    ) = await asyncio.gather(
        _fetch_crypto_caps(),
        _fetch_btc_mcap_trend(),
        _fetch_eth_btc_trend(),
        _fetch_yf_trend("DXY"),
        _fetch_yf_trend("SP500"),
        _fetch_yf_trend("NASDAQ"),
        _fetch_yf_trend("VIX"),
        _fetch_yf_trend("US10Y"),
        _fetch_yf_trend("GOLD"),
        _fetch_fear_greed(),
    )

    regime = detect_market_regime(
        btc_market_cap=btc_mcap,
        eth_btc_ratio=eth_btc,
        vix=vix,
        fear_greed=fear_greed,
    )

    return MacroSnapshot(
        crypto_caps=crypto_caps,
        btc_market_cap=btc_mcap,
        eth_btc_ratio=eth_btc,
        dxy=dxy,
        sp500=sp500,
        nasdaq=nasdaq,
        vix=vix,
        us10y=us10y,
        gold=gold,
        fear_greed=fear_greed,
        market_regime=regime,
        computed_at=datetime.now(UTC),
    )


class MacroService:
    """Public facade — Redis cache'li snapshot döner."""

    async def get_snapshot(self) -> MacroSnapshot:
        async def fetch() -> dict[str, Any]:
            snapshot = await _build_snapshot()
            return snapshot.model_dump(mode="json")

        raw = await cached_call(key=CACHE_KEY, ttl=CACHE_TTL, fetch_fn=fetch)
        return MacroSnapshot.model_validate(raw)

    async def get_regime(self) -> "RegimeResult":  # noqa: F821
        """Sadece regime — snapshot'a delegete (cache shared)."""
        snapshot = await self.get_snapshot()
        return snapshot.market_regime


macro_service = MacroService()


__all__ = ["MacroService", "macro_service"]
