"""Integration testler — gerçek external API'lere çağrı yapar.

Çalıştırma: docker compose exec backend uv run pytest -m integration -v
Default `pytest` çalıştırmasında skip edilir (pyproject.toml addopts).
"""
from __future__ import annotations

import time

import pytest

from app.core.redis_client import redis_client
from app.services.data_service import data_service

pytestmark = pytest.mark.integration


async def test_binance_klines_real_btc() -> None:
    klines = await data_service.get_klines("BTCUSDT", "4H", limit=10)
    assert len(klines) == 10

    for k in klines:
        assert "open_time" in k
        assert isinstance(k["close"], float)
        assert k["close"] > 0
        assert k["high"] >= k["low"]

    # Son mum recent (24h içinde)
    last = klines[-1]
    now_ms = time.time() * 1000
    assert (now_ms - last["close_time"]) < 24 * 3600 * 1000


async def test_binance_funding_real_btc() -> None:
    funding = await data_service.get_funding("BTCUSDT")
    assert funding["symbol"] == "BTCUSDT"
    assert isinstance(funding["funding_rate"], float)
    # Makul aralık: -1% ile +1% arası (anormal piyasada bile)
    assert -0.01 < funding["funding_rate"] < 0.01
    assert funding["mark_price"] > 0


async def test_coingecko_total_real() -> None:
    total = await data_service.get_total()
    # 2026 itibariyle TOTAL ~$2T-10T arası
    assert 1e12 < total < 20e12


async def test_yfinance_gold_real() -> None:
    price = await data_service.get_gold()
    # GOLD futures ~$1500-5000 (geniş aralık, geleceğe esnek)
    assert 1500 < price < 10000


async def test_fear_greed_real() -> None:
    fg = await data_service.get_fear_greed()
    assert 0 <= fg["value"] <= 100
    assert fg["classification"] in [
        "Extreme Fear",
        "Fear",
        "Neutral",
        "Greed",
        "Extreme Greed",
    ]


async def test_binance_klines_cache_hit_under_50ms() -> None:
    """Bonus: cache hit testi.

    1. çağrı: Binance API'ya gider (~200-500ms)
    2. çağrı: Redis cache'ten okur (<50ms ve >=10x hızlı)
    """
    # Bu test'e özel cache key'ini temizle (önceki testlerden kalmasın)
    async for key in redis_client.scan_iter(
        match="marketlens:binance:klines:BTCUSDT:1H:*"
    ):
        await redis_client.delete(key)

    # 1. çağrı: cache miss
    t0 = time.perf_counter()
    await data_service.get_klines("BTCUSDT", "1H", limit=20)
    first_ms = (time.perf_counter() - t0) * 1000

    # 2. çağrı: cache hit
    t0 = time.perf_counter()
    await data_service.get_klines("BTCUSDT", "1H", limit=20)
    second_ms = (time.perf_counter() - t0) * 1000

    print(f"\n  1st (miss): {first_ms:.1f}ms")
    print(f"  2nd (hit):  {second_ms:.1f}ms")
    print(f"  Speedup:    {first_ms / second_ms:.1f}x")

    assert second_ms < 50, f"2. çağrı {second_ms:.1f}ms (limit 50ms)"
    assert second_ms * 10 < first_ms, (
        f"2. çağrı en az 10x hızlı olmalı: 1st={first_ms:.1f}ms, 2nd={second_ms:.1f}ms"
    )
