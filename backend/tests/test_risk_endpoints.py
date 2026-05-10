"""Risk Management endpoint integration testleri."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


async def test_calculate_position_btc_long(client) -> None:  # type: ignore[no-untyped-def]
    """POST /api/v1/risk/calculate-position — BTC 80500/79500/3000USDT/2%."""
    payload = {
        "symbol": "BTCUSDT",
        "direction": "long",
        "balance": 3000.0,
        "base_risk_pct": 2.0,
        "entry": 80500.0,
        "stop": 79500.0,
        "targets": [83500.0, 85500.0, 88500.0],
        "max_leverage": 10,
    }
    r = await client.post("/api/v1/risk/calculate-position", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "BTCUSDT"
    assert body["direction"] == "long"
    assert body["risk_amount_usd"] > 0
    assert body["position_size_usd"] > 0
    assert body["leverage_actual"] >= 1
    assert body["rr"]["tp1"] is not None
    assert body["rr"]["weighted"] is not None
    assert "liquidation" in body
    assert "funding_costs" in body
    assert "volatility_adjustment" in body


async def test_calculate_position_unknown_symbol(client) -> None:  # type: ignore[no-untyped-def]
    payload = {
        "symbol": "FOOBAR",
        "direction": "long",
        "balance": 3000.0,
        "base_risk_pct": 2.0,
        "entry": 100.0,
        "stop": 99.0,
        "targets": [105.0],
        "max_leverage": 10,
    }
    r = await client.post("/api/v1/risk/calculate-position", json=payload)
    assert r.status_code == 404


async def test_auto_risk_btc_4h(client) -> None:  # type: ignore[no-untyped-def]
    """GET /api/v1/analysis/risk/BTCUSDT/4H — auto entry/stop/TP."""
    r = await client.get("/api/v1/analysis/risk/BTCUSDT/4H")
    # 200 (yön nötr değilse) veya 422 (nötr → ValidationError)
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        body = r.json()
        assert body["symbol"] == "BTCUSDT"
        assert body["direction"] in ("long", "short")
        assert len(body["targets"]) == 3
        assert body["position_size_usd"] >= 0


async def test_auto_risk_invalid_tf(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/analysis/risk/BTCUSDT/2H")
    assert r.status_code == 422


async def test_auto_risk_unknown_symbol(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/analysis/risk/FOOBAR/4H")
    assert r.status_code == 404


async def test_daily_status_anonymous(client) -> None:  # type: ignore[no-untyped-def]
    """GET /api/v1/risk/daily-status — auth yok → global state."""
    # Önce pause'u temizle (önceki testten kalmış olabilir)
    from app.services.risk.daily_tracker import daily_risk_tracker
    await daily_risk_tracker.unpause(user_id=None)

    r = await client.get("/api/v1/risk/daily-status")
    assert r.status_code == 200
    body = r.json()
    # Boş DB → defaults
    assert body["max_trades_per_day"] == 5
    assert body["daily_risk_max_pct"] == 4.0
    assert body["current_risk_per_trade_pct"] in (2.0, 1.5, 1.0)
    assert "now_utc" in body


async def test_pause_and_status(client) -> None:  # type: ignore[no-untyped-def]
    """POST pause → daily-status'ta paused_until ve can_open=false."""
    from app.services.risk.daily_tracker import daily_risk_tracker
    await daily_risk_tracker.unpause(user_id=None)

    r_pause = await client.post("/api/v1/risk/pause", json={"hours": 4})
    assert r_pause.status_code == 200
    body_pause = r_pause.json()
    assert body_pause["hours"] == 4
    assert "paused_until" in body_pause

    r_status = await client.get("/api/v1/risk/daily-status")
    assert r_status.status_code == 200
    status = r_status.json()
    assert status["can_open_new_trade"] is False
    assert status["paused_until"] is not None
    assert status["block_reason"] is not None

    await daily_risk_tracker.unpause(user_id=None)
