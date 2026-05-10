"""Scenario endpoint integration testleri."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


async def test_scenario_btc_4h(client) -> None:  # type: ignore[no-untyped-def]
    """GET /api/v1/analysis/scenario/BTCUSDT/4H."""
    r = await client.get("/api/v1/analysis/scenario/BTCUSDT/4H")
    # 200 (yön nötr değilse) veya 422 (nötr → ValidationError)
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        body = r.json()
        scenario = body["scenario"]
        position = body["position"]
        assert scenario["symbol"] == "BTCUSDT"
        assert scenario["direction"] in ("long", "short")
        assert "entry" in scenario
        assert "stop" in scenario
        assert len(scenario["targets"]) == 3
        # Pozisyon entegrasyonu
        assert position["symbol"] == "BTCUSDT"
        assert position["direction"] == scenario["direction"]
        assert position["entry"] == scenario["entry"]["mid"]
        assert position["stop"] == scenario["stop"]["price"]
        # Reasoning Türkçe
        assert any(
            tr_word in scenario["reasoning"]
            for tr_word in ("Long", "Short", "Entry")
        )


async def test_scenario_eth_4h(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/analysis/scenario/ETHUSDT/4H")
    assert r.status_code in (200, 422)


async def test_scenario_unknown_symbol(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/analysis/scenario/FOOBAR/4H")
    assert r.status_code == 404


async def test_scenario_invalid_tf(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/analysis/scenario/BTCUSDT/2H")
    assert r.status_code == 422


async def test_scenario_rr_weighted_present(client) -> None:  # type: ignore[no-untyped-def]
    """200 dönerse rr_weighted hesaplanmış olmalı."""
    r = await client.get("/api/v1/analysis/scenario/BTCUSDT/4H")
    if r.status_code == 200:
        body = r.json()
        assert body["scenario"]["rr_weighted"] is not None
        assert body["scenario"]["rr_weighted"] > 0


async def test_setup_quality_includes_scenario(client) -> None:  # type: ignore[no-untyped-def]
    """Setup Quality response'unda scenario alanı + R/R faktörü scenario'ya dayanır."""
    r = await client.get("/api/v1/analysis/quality/BTCUSDT/4H")
    assert r.status_code == 200
    body = r.json()
    # scenario alanı olmalı (neutral değilse dolu)
    assert "scenario" in body
    rr_factor = next(f for f in body["factors"] if f["name"] == "R:R ≥ 3")
    # Notes scenario veya neutral'a referans vermeli
    note = rr_factor["note"].lower()
    assert any(kw in note for kw in ["weighted", "neutral", "üretilemedi"])
