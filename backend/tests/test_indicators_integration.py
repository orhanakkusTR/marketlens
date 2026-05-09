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

    # Volatility
    assert bundle.volatility.atr.value_usdt > 0
    assert bundle.volatility.atr.value_pct > 0
    assert bundle.volatility.bollinger.upper > bundle.volatility.bollinger.lower
    assert isinstance(bundle.volatility.bollinger.squeeze, bool)

    # Volume
    assert bundle.volume.obv.slope in ("rising", "falling", "flat")
    assert bundle.volume.vwap is None  # 4H intraday değil
    assert bundle.volume.volume_profile.poc > 0
    assert (
        bundle.volume.volume_profile.val
        <= bundle.volume.volume_profile.poc
        <= bundle.volume.volume_profile.vah
    )

    # Fibonacci (None olabilir)
    if bundle.fibonacci is not None:
        assert bundle.fibonacci.swing_high.price > bundle.fibonacci.swing_low.price
        assert len(bundle.fibonacci.levels) == 8  # 5 retracement + 3 extension

    # Levels
    assert 0 < len(bundle.levels.supports) <= 5
    assert 0 < len(bundle.levels.resistances) <= 5
    for s in bundle.levels.supports:
        assert s.price < bundle.levels.current_price
    for r in bundle.levels.resistances:
        assert r.price >= bundle.levels.current_price


async def test_indicators_real_btc_1h_has_vwap() -> None:
    """1H intraday → VWAP None olmamalı."""
    bundle = await indicator_engine.compute_all("BTCUSDT", "1H")
    assert bundle.volume.vwap is not None
    assert bundle.volume.vwap.value > 0


async def test_levels_endpoint_real(client) -> None:  # type: ignore[no-untyped-def]
    """GET /api/v1/levels/BTCUSDT/4H çalışmalı."""
    r = await client.get("/api/v1/levels/BTCUSDT/4H")
    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "BTCUSDT"
    assert body["timeframe"] == "4H"
    assert "levels" in body
    assert "fibonacci" in body
    assert len(body["levels"]["supports"]) > 0
    assert len(body["levels"]["resistances"]) > 0


async def test_levels_endpoint_includes_round_numbers(client) -> None:  # type: ignore[no-untyped-def]
    """BTC için levels listesinde round_major veya round_minor görünmeli."""
    r = await client.get("/api/v1/levels/BTCUSDT/4H")
    assert r.status_code == 200
    body = r.json()
    all_sources: list[str] = []
    for lv in body["levels"]["supports"] + body["levels"]["resistances"]:
        all_sources.extend(lv["sources"])
    has_round = any(s.startswith("round_") for s in all_sources)
    assert has_round, f"Hiç round number tespit edilmedi: {all_sources}"


# ─── Step 8: Futures + Module Selector ───


async def test_futures_btc_real() -> None:
    """BTC futures snapshot — funding/OI/L-S real data."""
    from app.services.indicators.engine import indicator_engine

    fut = await indicator_engine.compute_futures("BTCUSDT")
    assert fut is not None
    # Funding makul aralık
    assert -0.01 < fut.funding.current_rate < 0.01
    assert isinstance(fut.funding.extreme, bool)
    # OI pozitif
    assert fut.open_interest.current > 0
    # L/S oranı pozitif
    assert fut.long_short.ratio > 0
    assert 0 < fut.long_short.long_account < 1
    assert 0 < fut.long_short.short_account < 1
    # period field
    assert fut.long_short.period == "1h"


async def test_indicators_endpoint_with_modules_selector(client) -> None:  # type: ignore[no-untyped-def]
    """?modules=trend,futures → sadece trend ve futures dolu."""
    r = await client.get("/api/v1/indicators/BTCUSDT/4H?modules=trend,futures")
    assert r.status_code == 200
    body = r.json()
    assert body["trend"] is not None
    assert body["futures"] is not None
    # Diğerleri None
    assert body["momentum"] is None
    assert body["volatility"] is None
    assert body["volume"] is None
    assert body["fibonacci"] is None
    assert body["levels"] is None


async def test_indicators_endpoint_invalid_module(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/indicators/BTCUSDT/4H?modules=foo,bar")
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "validation_error"


async def test_indicators_endpoint_full_includes_futures(client) -> None:  # type: ignore[no-untyped-def]
    """Modules belirtilmeden full bundle → futures dolu olmalı (BTC)."""
    r = await client.get("/api/v1/indicators/BTCUSDT/4H")
    assert r.status_code == 200
    body = r.json()
    assert body["futures"] is not None
    assert "funding" in body["futures"]
    assert "open_interest" in body["futures"]
    assert "long_short" in body["futures"]


async def test_futures_cache_hit_under_50ms() -> None:
    """compute_futures 2. çağrı cache'ten <50ms.

    Hem indicators hem data layer cache'lerini temizle (gerçek miss simüle).
    """
    import time

    from app.core.redis_client import redis_client
    from app.services.indicators.engine import indicator_engine

    # İndikatör + alt veri katmanı cache'lerini temizle
    patterns = [
        "marketlens:indicators:ETHUSDT:futures",
        "marketlens:binance:funding:ETHUSDT",
        "marketlens:binance:funding_hist:ETHUSDT:*",
        "marketlens:binance:oi:ETHUSDT",
        "marketlens:binance:oi_hist:ETHUSDT:*",
        "marketlens:binance:lsr:ETHUSDT:*",
    ]
    for p in patterns:
        async for k in redis_client.scan_iter(match=p):
            await redis_client.delete(k)

    t0 = time.perf_counter()
    await indicator_engine.compute_futures("ETHUSDT")
    first = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    await indicator_engine.compute_futures("ETHUSDT")
    second = (time.perf_counter() - t0) * 1000

    print(f"\n  1st (miss): {first:.1f}ms")
    print(f"  2nd (hit):  {second:.1f}ms")

    assert second < 50, f"2. çağrı {second:.1f}ms"
    assert second * 10 < first, f"Speedup yetersiz: 1st={first:.1f}ms, 2nd={second:.1f}ms"


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
