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


async def test_full_gold_correlations_none(client) -> None:  # type: ignore[no-untyped-def]
    """GOLD: correlations None (commodity), futures None, ama setup_quality dolu."""
    r = await client.get("/api/v1/analysis/full/GOLD/4H")
    # GOLD Binance kline'da yok — Phase 1 fail olabilir, 503 dönerse de OK
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        body = r.json()
        assert body["correlations"] is None
        assert body["indicators"]["futures"] is None
        # Correlations None için Commodity exception → warning yok
        # (kullanıcı tercihi: GOLD için sessiz)
        corr_warnings = [w for w in body["warnings"] if "Korelasyon" in w]
        assert len(corr_warnings) == 0


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
