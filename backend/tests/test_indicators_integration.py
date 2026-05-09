"""Integration testler — gerçek Binance kline ile indicator engine.

Çalıştırma: docker compose exec backend uv run pytest -m integration -v
Default `pytest` çalıştırmasında skip edilir.
"""
from __future__ import annotations

import time

import pytest

from app.core.redis_client import redis_client
from app.services.indicators.engine import indicator_engine

pytestmark = pytest.mark.integration


async def test_indicators_real_btc_4h() -> None:
    """BTC 4H için tüm indikatör bundle'ı çalışmalı."""
    bundle = await indicator_engine.compute_all("BTCUSDT", "4H")

    assert bundle.symbol == "BTCUSDT"
    assert bundle.timeframe == "4H"
    assert bundle.kline_count >= 100

    # Trend
    assert len(bundle.trend.moving_averages.moving_averages) == 3
    assert bundle.trend.ichimoku.cloud_state in ("above", "below", "inside")
    assert bundle.trend.market_structure.structure in ("uptrend", "downtrend", "ranging")

    # Momentum
    assert 0 <= bundle.momentum.rsi.current <= 100
    assert bundle.momentum.rsi.state in ("overbought", "oversold", "neutral")
    assert isinstance(bundle.momentum.macd.histogram, float)
    assert 0 <= bundle.momentum.stoch_rsi.k <= 100


async def test_indicators_endpoint_real(client) -> None:  # type: ignore[no-untyped-def]
    """HTTP endpoint çalışmalı — schema valid."""
    r = await client.get("/api/v1/indicators/BTCUSDT/4H")
    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "BTCUSDT"
    assert body["timeframe"] == "4H"
    assert "trend" in body
    assert "momentum" in body
    assert "moving_averages" in body["trend"]
    assert "rsi" in body["momentum"]


async def test_indicators_endpoint_unknown_symbol(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/indicators/FOOBAR/4H")
    assert r.status_code == 404
    body = r.json()
    assert body["error"] == "not_found"


async def test_indicators_endpoint_invalid_timeframe(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/indicators/BTCUSDT/2H")
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "validation_error"


async def test_indicators_cache_hit_under_50ms() -> None:
    """1. çağrı: hesap (~100-300ms). 2. çağrı: Redis cache (<50ms ve >=10x hızlı)."""
    # Bu test'e özel cache key'ini temizle
    async for key in redis_client.scan_iter(match="marketlens:indicators:BTCUSDT:1H:*"):
        await redis_client.delete(key)
    # Kline cache de temiz olsun (ilk çağrı baştan compute olsun)
    async for key in redis_client.scan_iter(match="marketlens:binance:klines:BTCUSDT:1H:*"):
        await redis_client.delete(key)

    t0 = time.perf_counter()
    await indicator_engine.compute_all("BTCUSDT", "1H")
    first_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    await indicator_engine.compute_all("BTCUSDT", "1H")
    second_ms = (time.perf_counter() - t0) * 1000

    print(f"\n  1st (miss): {first_ms:.1f}ms")
    print(f"  2nd (hit):  {second_ms:.1f}ms")
    print(f"  Speedup:    {first_ms / second_ms:.1f}x")

    assert second_ms < 50, f"2. çağrı {second_ms:.1f}ms (limit 50ms)"
    assert second_ms * 10 < first_ms, (
        f"2. çağrı en az 10x hızlı olmalı: 1st={first_ms:.1f}ms, 2nd={second_ms:.1f}ms"
    )
