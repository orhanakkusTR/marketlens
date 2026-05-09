"""Confluence integration testler — gerçek BTC + GOLD."""
from __future__ import annotations

import time

import pytest

from app.core.redis_client import redis_client
from app.services.indicators.engine import indicator_engine

pytestmark = pytest.mark.integration


async def test_btc_4h_local_confluence() -> None:
    result = await indicator_engine.compute_local_confluence("BTCUSDT", "4H")
    assert result.symbol == "BTCUSDT"
    assert result.timeframe == "4H"
    assert -100 <= result.final_score <= 100
    assert result.label in (
        "strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"
    )
    assert result.direction in ("long", "short", "neutral")
    # Components: hepsi ham skor [-100, +100] (volatility -50..+30)
    c = result.components
    assert -100 <= c.trend <= 100
    assert -100 <= c.momentum <= 100
    assert -100 <= c.volume <= 100
    assert -50 <= c.volatility <= 30
    # BTC futures destekliyor
    assert c.futures is not None
    assert -100 <= c.futures <= 100


async def test_btc_all_timeframes_compute() -> None:
    """6 TF için skor üretilebilmeli — sadece çalışıyor mu kontrol."""
    timeframes = ["15m", "1H", "4H", "1D", "1W", "1M"]
    results = {}
    for tf in timeframes:
        r = await indicator_engine.compute_local_confluence("BTCUSDT", tf)
        results[tf] = r
        assert -100 <= r.final_score <= 100
    # En azından 4H ve 1D'nin skoru farklı olmalı (farklı pencere → farklı sinyal)
    assert results["4H"].final_score != results["1D"].final_score


async def test_confluence_endpoint(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/confluence/local/BTCUSDT/4H")
    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "BTCUSDT"
    assert body["timeframe"] == "4H"
    assert "final_score" in body
    assert body["label"] in (
        "strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"
    )
    assert body["direction"] in ("long", "short", "neutral")
    assert "components" in body
    assert "weights_applied" in body


async def test_confluence_endpoint_unknown_symbol(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/confluence/local/FOOBAR/4H")
    assert r.status_code == 404


async def test_confluence_endpoint_invalid_tf(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/confluence/local/BTCUSDT/2H")
    assert r.status_code == 422


async def test_confluence_cache_hit_under_50ms() -> None:
    async for k in redis_client.scan_iter(
        match="marketlens:confluence:local:ETHUSDT:1H"
    ):
        await redis_client.delete(k)

    t0 = time.perf_counter()
    await indicator_engine.compute_local_confluence("ETHUSDT", "1H")
    first = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    await indicator_engine.compute_local_confluence("ETHUSDT", "1H")
    second = (time.perf_counter() - t0) * 1000

    print(f"\n  1st: {first:.1f}ms  2nd: {second:.1f}ms  speedup: {first / second:.1f}x")
    assert second < 50
    assert second * 10 < first
