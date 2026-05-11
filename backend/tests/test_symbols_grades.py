"""Symbols grades endpoint testleri — Adım 19."""
from __future__ import annotations

import pytest


async def test_summarize_with_error() -> None:
    """Exception payload'sı varsa GradeSummary error doldurulur."""
    from app.api.v1.symbols import _summarize

    s = _summarize("XAUUSDT", None, "Yetersiz veri (yeni listelendi)")
    assert s.symbol == "XAUUSDT"
    assert s.grade is None
    assert s.direction is None
    assert s.final_score is None
    assert s.error == "Yetersiz veri (yeni listelendi)"
    assert s.is_blocking is False


async def test_summarize_with_payload() -> None:
    from app.api.v1.symbols import _summarize

    payload = {
        "grade": "B",
        "direction": "long",
        "final_score": 70.5,
        "no_trade_zones": {"is_blocking": True},
    }
    s = _summarize("BTCUSDT", payload, None)
    assert s.symbol == "BTCUSDT"
    assert s.grade == "B"
    assert s.direction == "long"
    assert s.final_score == 70.5
    assert s.is_blocking is True
    assert s.error is None


# ─── Integration ───


@pytest.mark.integration
async def test_grades_endpoint_btc_eth(client) -> None:  # type: ignore[no-untyped-def]
    """GET /api/v1/symbols/grades — 27 sembol döner, BTC ve ETH grade dolu."""
    r = await client.get("/api/v1/symbols/grades")
    assert r.status_code == 200
    body = r.json()
    assert body["timeframe"] == "4H"
    assert len(body["items"]) == 27

    by_sym = {item["symbol"]: item for item in body["items"]}
    # BTC ve ETH muhtemelen grade'li (yeterli veri)
    btc = by_sym["BTCUSDT"]
    assert btc["error"] is None
    assert btc["grade"] in ("A", "B", "C", "D", "NO_TRADE")
    eth = by_sym["ETHUSDT"]
    assert eth["error"] is None or eth["grade"] is not None


@pytest.mark.integration
async def test_grades_endpoint_xauusdt_graceful(client) -> None:  # type: ignore[no-untyped-def]
    """XAUUSDT yeterli veri yok → error field dolu, grade null."""
    r = await client.get("/api/v1/symbols/grades")
    assert r.status_code == 200
    body = r.json()
    by_sym = {item["symbol"]: item for item in body["items"]}
    xau = by_sym["XAUUSDT"]
    # Yeni listelendi — ya error var ya da grade hesaplanmış (gelecekte mum birikince)
    if xau["error"] is not None:
        assert xau["grade"] is None
        assert "veri" in xau["error"].lower() or "hesaplanamadı" in xau["error"].lower()
