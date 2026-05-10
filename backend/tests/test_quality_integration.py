"""Setup Quality integration testleri."""
from __future__ import annotations

import time

import pytest

from app.core.redis_client import redis_client
from app.services.quality.setup_quality import setup_quality_engine

pytestmark = pytest.mark.integration


async def test_btc_4h_quality_real() -> None:
    result = await setup_quality_engine.evaluate("BTCUSDT", "4H")
    assert result.symbol == "BTCUSDT"
    assert result.timeframe == "4H"
    assert 0 <= result.raw_score <= 100
    assert result.base_grade in ("A", "B", "C", "D")
    assert result.grade in ("A", "B", "C", "D", "NO_TRADE")

    # 10 base factor
    assert len(result.factors) == 10

    # Confidence — trade boş → VERY_LOW
    assert result.confidence.level == "VERY_LOW"
    assert result.confidence.trade_count == 0

    # Counter-trend max 5
    assert len(result.counter_trend_warnings) <= 5

    # Trade quality 5 factor + Türkçe names
    assert len(result.trade_quality.factors) == 5
    names = {f.name for f in result.trade_quality.factors}
    assert names == {"ATR makul", "ADX güçlü", "Macro net", "Hacim artıyor", "Yol açık"}
    assert result.trade_quality.verdict in ("EXCELLENT", "GOOD", "WEAK", "AVOID")


async def test_eth_4h_quality_real() -> None:
    result = await setup_quality_engine.evaluate("ETHUSDT", "4H")
    assert result.symbol == "ETHUSDT"
    assert result.grade in ("A", "B", "C", "D", "NO_TRADE")


async def test_endpoint_btc(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/analysis/quality/BTCUSDT/4H")
    assert r.status_code == 200
    body = r.json()
    assert "raw_score" in body
    assert "base_grade" in body
    assert "grade" in body
    assert "confidence" in body
    assert "counter_trend_warnings" in body
    assert "trade_quality" in body


async def test_endpoint_unknown_symbol(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/analysis/quality/FOOBAR/4H")
    assert r.status_code == 404


async def test_endpoint_invalid_tf(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/analysis/quality/BTCUSDT/2H")
    assert r.status_code == 422


async def test_quality_cache_hit() -> None:
    """2. çağrı cache'ten hızlı."""
    async for k in redis_client.scan_iter(match="marketlens:setup_quality:ETHUSDT:1H"):
        await redis_client.delete(k)

    t0 = time.perf_counter()
    await setup_quality_engine.evaluate("ETHUSDT", "1H")
    first = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    await setup_quality_engine.evaluate("ETHUSDT", "1H")
    second = (time.perf_counter() - t0) * 1000

    print(f"\n  1st: {first:.1f}ms  2nd: {second:.1f}ms  speedup: {first/second:.1f}x")
    assert second < 50
