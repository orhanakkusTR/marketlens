"""Macro integration testler — gerçek API'ler."""
from __future__ import annotations

import time

import pytest

from app.core.redis_client import redis_client
from app.services.macro.context import macro_service

pytestmark = pytest.mark.integration


async def test_macro_snapshot_real() -> None:
    snapshot = await macro_service.get_snapshot()

    # Crypto caps
    assert snapshot.crypto_caps.total > 1e12  # >$1T
    assert 0 < snapshot.crypto_caps.btc_dominance < 100
    assert 0 < snapshot.crypto_caps.eth_dominance < 100

    # BTC market cap
    assert snapshot.btc_market_cap.current > 1e11  # >$100B
    # En azından 7d ve 30d trend'leri olmalı
    assert snapshot.btc_market_cap.change_7d_pct is not None
    assert snapshot.btc_market_cap.change_30d_pct is not None

    # ETH/BTC ratio (kripto, makul aralık 0.01-0.10)
    assert 0.005 < snapshot.eth_btc_ratio.current < 0.2
    assert snapshot.eth_btc_ratio.change_7d_pct is not None

    # TradFi (yfinance)
    assert 70 < snapshot.dxy.current < 130  # tarihsel aralık
    assert snapshot.sp500.current > 1000
    assert snapshot.nasdaq.current > 5000
    assert 5 < snapshot.vix.current < 100
    assert 0 < snapshot.us10y.current < 10  # %0-10 yield
    assert 1000 < snapshot.gold.current < 10000

    # Fear & Greed
    assert 0 <= snapshot.fear_greed.value <= 100
    assert snapshot.fear_greed.classification in (
        "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
    )

    # Regime
    assert snapshot.market_regime.regime in (
        "ALT_BULL", "BTC_BULL", "RISK_OFF", "ALT_SEASON_EARLY", "MIXED"
    )
    assert len(snapshot.market_regime.label) > 0
    assert len(snapshot.market_regime.triggers) == 8


async def test_macro_endpoint_snapshot(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/macro/snapshot")
    assert r.status_code == 200
    body = r.json()
    assert "crypto_caps" in body
    assert "btc_market_cap" in body
    assert "eth_btc_ratio" in body
    assert "vix" in body
    assert "fear_greed" in body
    assert "market_regime" in body


async def test_macro_endpoint_regime(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/macro/regime")
    assert r.status_code == 200
    body = r.json()
    assert body["regime"] in (
        "ALT_BULL", "BTC_BULL", "RISK_OFF", "ALT_SEASON_EARLY", "MIXED"
    )
    assert "triggers" in body
    assert len(body["label"]) > 0


async def test_macro_cache_hit_under_50ms() -> None:
    """2. çağrı cache'ten <50ms ve >=10x hızlı."""
    async for k in redis_client.scan_iter(match="marketlens:macro:snapshot"):
        await redis_client.delete(k)

    t0 = time.perf_counter()
    await macro_service.get_snapshot()
    first = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    await macro_service.get_snapshot()
    second = (time.perf_counter() - t0) * 1000

    print(f"\n  1st: {first:.1f}ms  2nd: {second:.1f}ms  speedup: {first / second:.1f}x")

    assert second < 50
    assert second * 10 < first
