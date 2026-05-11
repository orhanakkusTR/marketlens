"""PriceHub unit testleri — subscribe/unsubscribe/fan-out/normalize."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ws.price_hub import (
    FUTURES_SYMBOLS,
    SPOT_SYMBOLS,
    PriceHub,
    _normalize_ticker,
)


def test_spot_futures_partition() -> None:
    """SPOT 26 sembol + FUTURES sadece XAUUSDT."""
    assert "BTCUSDT" in SPOT_SYMBOLS
    assert "ETHUSDT" in SPOT_SYMBOLS
    assert "XAUUSDT" not in SPOT_SYMBOLS
    assert FUTURES_SYMBOLS == ["XAUUSDT"]
    assert len(SPOT_SYMBOLS) == 26


def test_normalize_ticker_happy_path() -> None:
    data = {"s": "BTCUSDT", "c": "80627.40", "P": "2.4", "E": 1234567890}
    msg = _normalize_ticker(data)
    assert msg is not None
    assert msg["type"] == "price"
    assert msg["symbol"] == "BTCUSDT"
    assert msg["price"] == 80627.40
    assert msg["change_24h_pct"] == 2.4
    assert msg["ts"] == 1234567890


def test_normalize_ticker_missing_fields() -> None:
    """Eksik field → None."""
    assert _normalize_ticker({"s": "BTC"}) is None
    assert _normalize_ticker({"c": "100"}) is None
    assert _normalize_ticker({}) is None


def test_normalize_ticker_invalid_numbers() -> None:
    assert _normalize_ticker({"s": "BTCUSDT", "c": "not-a-number", "P": "1"}) is None


async def test_subscribe_unknown_symbol_ignored() -> None:
    hub = PriceHub()
    ws = MagicMock()
    snapshot = await hub.subscribe(ws, ["FOOBAR", "BTCUSDT"])
    # BTC bilinen ama latest_prices'ta yok → snapshot boş
    assert snapshot == []
    # BTC subscribe edildi ama FOOBAR edilmedi
    assert ws in hub.clients["BTCUSDT"]
    assert "FOOBAR" not in hub.clients


async def test_subscribe_returns_warmup_snapshot() -> None:
    hub = PriceHub()
    ws = MagicMock()
    # latest_prices'i seed et
    hub.latest["BTCUSDT"] = {
        "type": "price", "symbol": "BTCUSDT", "price": 80000.0,
        "change_24h_pct": 1.5, "ts": 1,
    }
    hub.latest["ETHUSDT"] = {
        "type": "price", "symbol": "ETHUSDT", "price": 2500.0,
        "change_24h_pct": 0.8, "ts": 2,
    }
    snapshot = await hub.subscribe(ws, ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    # SOL latest'ta yok → snapshot'ta yok
    symbols = {p["symbol"] for p in snapshot}
    assert symbols == {"BTCUSDT", "ETHUSDT"}


async def test_unsubscribe_all_when_none() -> None:
    hub = PriceHub()
    ws = MagicMock()
    await hub.subscribe(ws, ["BTCUSDT", "ETHUSDT"])
    assert ws in hub.clients["BTCUSDT"]
    assert ws in hub.clients["ETHUSDT"]

    await hub.unsubscribe(ws, None)
    assert ws not in hub.clients.get("BTCUSDT", set())
    assert ws not in hub.clients.get("ETHUSDT", set())


async def test_unsubscribe_specific_symbols() -> None:
    hub = PriceHub()
    ws = MagicMock()
    await hub.subscribe(ws, ["BTCUSDT", "ETHUSDT"])

    await hub.unsubscribe(ws, ["BTCUSDT"])
    assert ws not in hub.clients["BTCUSDT"]
    assert ws in hub.clients["ETHUSDT"]


async def test_fan_out_to_multiple_clients() -> None:
    hub = PriceHub()
    ws1 = MagicMock()
    ws1.send_json = AsyncMock()
    ws2 = MagicMock()
    ws2.send_json = AsyncMock()
    await hub.subscribe(ws1, ["BTCUSDT"])
    await hub.subscribe(ws2, ["BTCUSDT"])

    msg = {"type": "price", "symbol": "BTCUSDT", "price": 80000, "change_24h_pct": 1, "ts": 1}
    await hub._fan_out("BTCUSDT", msg)

    ws1.send_json.assert_awaited_once_with(msg)
    ws2.send_json.assert_awaited_once_with(msg)


async def test_fan_out_skips_dead_clients() -> None:
    """send_json raise olan client'lar temizlenir."""
    hub = PriceHub()
    alive = MagicMock()
    alive.send_json = AsyncMock()
    dead = MagicMock()
    dead.send_json = AsyncMock(side_effect=Exception("connection closed"))
    await hub.subscribe(alive, ["BTCUSDT"])
    await hub.subscribe(dead, ["BTCUSDT"])

    msg = {"type": "price", "symbol": "BTCUSDT", "price": 1, "change_24h_pct": 0, "ts": 1}
    await hub._fan_out("BTCUSDT", msg)

    # Alive client mesaj aldı, dead temizlendi
    alive.send_json.assert_awaited_once()
    assert dead not in hub.clients["BTCUSDT"]
    assert alive in hub.clients["BTCUSDT"]


async def test_fan_out_no_clients_silent() -> None:
    """Subscribe olmayan sembolde fan_out sessiz."""
    hub = PriceHub()
    msg = {"type": "price", "symbol": "BTCUSDT", "price": 1, "change_24h_pct": 0, "ts": 1}
    # Hata fırlatmamalı
    await hub._fan_out("BTCUSDT", msg)
