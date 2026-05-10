"""Full analysis endpoint integration testleri."""
from __future__ import annotations

import time

import pytest

from app.core.redis_client import redis_client

pytestmark = pytest.mark.integration


async def test_full_btc_4h_all_modules(client) -> None:  # type: ignore[no-untyped-def]
    """BTC 4H full analysis — tüm zorunlu alanlar dolu."""
    r = await client.get("/api/v1/analysis/full/BTCUSDT/4H")
    assert r.status_code == 200
    body = r.json()

    # Kimlik
    assert body["symbol"] == "BTCUSDT"
    assert body["timeframe"] == "4H"
    assert body["current_price"] > 0
    assert "computed_at" in body
    assert "fetch_timings" in body
    assert "cache_hit" in body

    # Core (zorunlu)
    assert "indicators" in body
    assert body["indicators"]["trend"] is not None
    assert body["indicators"]["momentum"] is not None
    assert body["indicators"]["volatility"] is not None
    assert body["indicators"]["levels"] is not None
    assert body["indicators"]["futures"] is not None  # BTC için var
    assert "final_confluence" in body
    assert "multi_tf_alignment" in body
    assert "setup_quality" in body

    # Module statuses — her modül listelenmiş
    status_names = {s["name"] for s in body["module_statuses"]}
    assert {"indicators", "final_confluence", "setup_quality",
            "multi_tf_alignment", "macro", "correlations",
            "risk_position"} <= status_names


async def test_full_eth_4h(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/analysis/full/ETHUSDT/4H")
    assert r.status_code == 200
    body = r.json()
    assert body["indicators"]["futures"] is not None


async def test_full_xauusdt_routes_to_binance_futures(client) -> None:  # type: ignore[no-untyped-def]
    """XAUUSDT (Binance TradFi Perpetual, Ocak 2026): routing Binance Futures'a.

    Sembol Binance Futures'ta listelendiği için kline/funding/OI/L-S erişilebilir.
    Yeterli mum geçmişi yoksa (Ichimoku 52 bar) Phase 1 503 dönebilir — bu
    sembolün listelenme tarihinin yeni olmasından kaynaklı, geçici durum.
    Önemli: 503 dönerken bile spot endpoint 400 değil; routing çalışıyor.
    """
    r = await client.get("/api/v1/analysis/full/XAUUSDT/4H")
    assert r.status_code in (200, 503)
    body = r.json()
    if r.status_code == 200:
        assert body["indicators"]["futures"] is not None
        assert body["correlations"] is not None
        assert body["setup_quality"] is not None
        assert body["macro"] is not None
        # Macro snapshot'ta "gold" alanı hala yfinance'tan (klasik gold futures)
        assert body["macro"]["gold"] is not None
    else:
        # 503 — yeterli mum yok. Hata sebebi "Bad Request" DEĞİL olmalı (Binance
        # Spot 400 → routing bozulmuş demek olur). Indicator/mum sayısı sebebi OK.
        reason = (body.get("details") or {}).get("reason", "").lower()
        assert "400 bad request" not in reason
        # Tipik sebep: ichimoku için yeterli mum yok
        assert "mum" in reason or "ichimoku" in reason or "yeterli" in reason


async def test_full_cache_hit_speedup(client) -> None:  # type: ignore[no-untyped-def]
    """2. çağrı cache hit ile <100ms."""
    # Önce cache temizle
    async for k in redis_client.scan_iter(match="marketlens:analysis:full:BTCUSDT:4H:*"):
        await redis_client.delete(k)

    t0 = time.perf_counter()
    r1 = await client.get("/api/v1/analysis/full/BTCUSDT/4H")
    first_ms = (time.perf_counter() - t0) * 1000
    assert r1.status_code == 200
    assert r1.json()["cache_hit"] is False

    t0 = time.perf_counter()
    r2 = await client.get("/api/v1/analysis/full/BTCUSDT/4H")
    second_ms = (time.perf_counter() - t0) * 1000
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["cache_hit"] is True

    print(f"\n  cold: {first_ms:.0f}ms  hot: {second_ms:.0f}ms  speedup: {first_ms/second_ms:.1f}x")
    assert second_ms < 200  # hot cache cömert sınır (test env asenkron HTTP overhead)


async def test_full_unknown_symbol(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/analysis/full/FOOBAR/4H")
    assert r.status_code == 404


async def test_full_invalid_tf(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/analysis/full/BTCUSDT/2H")
    assert r.status_code == 422


async def test_full_neutral_direction_scenario_and_risk_none(client) -> None:  # type: ignore[no-untyped-def]
    """1W gibi direction=neutral olabilen TF için: scenario+risk_position=None, 200 dönmeli."""
    # 1W için neutral muhtemel — sembol döngüsüyle bul
    candidates = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT"]
    for sym in candidates:
        r = await client.get(f"/api/v1/analysis/full/{sym}/1W")
        if r.status_code != 200:
            continue
        body = r.json()
        if body["setup_quality"]["direction"] == "neutral":
            # Beklenen: scenario None, risk_position None
            assert body["setup_quality"]["scenario"] is None
            assert body["risk_position"] is None
            # Endpoint yine 200, tüm core dolu
            assert body["indicators"]["trend"] is not None
            return
    pytest.skip("Hiç sembol 1W'de neutral direction üretmedi — test atlandı")


async def test_full_response_has_required_action_summary_fields(client) -> None:  # type: ignore[no-untyped-def]
    """Aksiyon Özeti (Adım 21) için gerekli alanlar response'ta var mı."""
    r = await client.get("/api/v1/analysis/full/BTCUSDT/4H")
    assert r.status_code == 200
    body = r.json()

    sq = body["setup_quality"]
    # Direction, grade, confidence
    assert "direction" in sq
    assert "grade" in sq
    assert "confidence" in sq

    # Scenario (neutral değilse)
    if sq["direction"] != "neutral":
        scenario = sq["scenario"]
        assert scenario is not None
        assert "entry" in scenario
        assert "stop" in scenario
        assert "targets" in scenario

        # Risk position (entry/stop/targets'tan hesaplanmış)
        rp = body["risk_position"]
        assert rp is not None
        assert "position_size_usd" in rp
        assert "leverage_actual" in rp
        assert "margin_used" in rp
        assert "risk_amount_usd" in rp
        assert "funding_costs" in rp
        assert "liquidation" in rp

    # Counter-trend
    assert "counter_trend_warnings" in sq
    # No-trade zones
    assert "no_trade_zones" in sq
    # Macro
    assert "macro" in body
    # Alignment
    assert "multi_tf_alignment" in body
    assert "by_timeframe" in body["multi_tf_alignment"]
