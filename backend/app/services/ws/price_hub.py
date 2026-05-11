"""PriceHub — Adım 19.

Multi-symbol fiyat akışı için tek upstream + N client fan-out pattern.

Upstream'ler:
- spot:    26 USDT crypto (Binance Spot combined stream)
- futures: XAUUSDT (Binance Futures combined stream — TradFi Perpetual)

İki upstream paralel `asyncio.gather` ile çalışır. Hub her ikisini de
aynı message format'a normalize edip latest_prices + clients'a push'lar.

Lifespan: app.main `start()` çağırır, shutdown'da `stop()`.
Endpoint: /api/v1/ws/prices — clients hub'a subscribe olur.

Latency hedefi: <500ms (Binance → backend ~50ms, backend → frontend ~50ms).
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import time
from typing import Any

import httpx
import websockets
from fastapi import WebSocket

from app.core.config import settings
from app.core.logging import get_logger
from app.data.symbols_meta import ALL_SYMBOLS

logger = get_logger(__name__)

# Spot/Futures bölümlemesi
SPOT_SYMBOLS: list[str] = [s for s in ALL_SYMBOLS if s != "XAUUSDT"]
FUTURES_SYMBOLS: list[str] = ["XAUUSDT"]

UPSTREAM_RECONNECT_DELAY = 5.0  # saniye (Binance reset sonrası bekleme)

# XAUUSDT yeni listelendi — Binance Futures @ticker WS stream'i henüz aktif
# değil, ama REST endpoint dolu. Polling fallback: 5sn'de bir 24h ticker.
XAUUSDT_REST_POLL_INTERVAL = 5.0  # saniye


def _spot_combined_url() -> str:
    """wss://stream.binance.com:9443/stream?streams=btcusdt@ticker/..."""
    base = settings.binance_ws_url.replace("/ws", "/stream")
    streams = "/".join(f"{s.lower()}@ticker" for s in SPOT_SYMBOLS)
    return f"{base}?streams={streams}"


def _futures_combined_url() -> str:
    """wss://fstream.binance.com/stream?streams=xauusdt@ticker"""
    base = settings.binance_futures_ws_url.replace("/ws", "/stream")
    streams = "/".join(f"{s.lower()}@ticker" for s in FUTURES_SYMBOLS)
    return f"{base}?streams={streams}"


def _normalize_ticker(data: dict[str, Any]) -> dict[str, Any] | None:
    """Binance @ticker payload → standart frontend message.

    Binance fields:
      s = symbol, c = last close, P = 24h price change percent, E = event time
    """
    symbol = data.get("s")
    close = data.get("c")
    change_pct = data.get("P")
    event_time = data.get("E")
    if not symbol or close is None or change_pct is None:
        return None
    try:
        return {
            "type": "price",
            "symbol": str(symbol),
            "price": float(close),
            "change_24h_pct": float(change_pct),
            "ts": int(event_time) if event_time is not None else int(time.time() * 1000),
        }
    except (TypeError, ValueError):
        return None


class PriceHub:
    """Singleton — 2 upstream task + fan-out registry."""

    def __init__(self) -> None:
        self.clients: dict[str, set[WebSocket]] = {}
        self.latest: dict[str, dict[str, Any]] = {}
        self._tasks: list[asyncio.Task[None]] = []
        self._stop_event = asyncio.Event()
        self._lock = asyncio.Lock()  # clients/latest mutation safety

    # ─── Lifecycle ───

    async def start(self) -> None:
        """Lifespan startup'ta çağrılır."""
        if self._tasks:
            return  # idempotent
        self._stop_event.clear()
        self._tasks = [
            asyncio.create_task(
                self._run_upstream("spot", _spot_combined_url()), name="ws_upstream_spot"
            ),
            # XAUUSDT için Binance Futures @ticker WS stream'i yayın yapmıyor
            # (yeni sembol, henüz aktif değil). REST polling fallback kullanıyoruz.
            asyncio.create_task(
                self._run_xauusdt_rest_poller(), name="rest_poller_xauusdt"
            ),
        ]
        logger.info("price_hub_started", spot=len(SPOT_SYMBOLS), futures_rest_poll=True)

    async def stop(self) -> None:
        """Lifespan shutdown'ta çağrılır."""
        self._stop_event.set()
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await t
        self._tasks = []
        # Tüm açık client'ları temizle (graceful disconnect)
        async with self._lock:
            self.clients.clear()
        logger.info("price_hub_stopped")

    # ─── Subscriptions ───

    async def subscribe(self, ws: WebSocket, symbols: list[str]) -> list[dict[str, Any]]:
        """Client'i sembollere subscribe eder; warmup için latest_prices snapshot döner."""
        snapshot: list[dict[str, Any]] = []
        async with self._lock:
            for s in symbols:
                s_upper = s.upper()
                if s_upper not in ALL_SYMBOLS:
                    logger.warning("ws_subscribe_unknown_symbol", symbol=s_upper)
                    continue
                self.clients.setdefault(s_upper, set()).add(ws)
                latest = self.latest.get(s_upper)
                if latest is not None:
                    snapshot.append(latest)
        return snapshot

    async def unsubscribe(
        self, ws: WebSocket, symbols: list[str] | None = None
    ) -> None:
        """None → tüm subscription'ları temizle (disconnect senaryosu)."""
        async with self._lock:
            if symbols is None:
                for clients in self.clients.values():
                    clients.discard(ws)
            else:
                for s in symbols:
                    self.clients.get(s.upper(), set()).discard(ws)

    # ─── Upstream loop ───

    async def _run_upstream(self, name: str, url: str) -> None:
        """Binance combined stream loop with auto-reconnect."""
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(
                    url, ping_interval=20, ping_timeout=10, max_queue=64
                ) as ws:
                    logger.info("ws_upstream_connected", upstream=name)
                    async for raw in ws:
                        if self._stop_event.is_set():
                            return
                        try:
                            payload = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        # Combined stream format: {"stream": "...@ticker", "data": {...}}
                        data = payload.get("data") if "data" in payload else payload
                        if not isinstance(data, dict):
                            continue
                        msg = _normalize_ticker(data)
                        if msg is None:
                            continue
                        self.latest[msg["symbol"]] = msg
                        await self._fan_out(msg["symbol"], msg)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if self._stop_event.is_set():
                    return
                logger.warning(
                    "ws_upstream_error", upstream=name, error=str(e),
                )
                # Backoff before reconnect
                await asyncio.sleep(UPSTREAM_RECONNECT_DELAY)

    async def _run_xauusdt_rest_poller(self) -> None:
        """XAUUSDT için Binance Futures REST polling fallback.

        WS @ticker stream'i bu sembol için yayın yapmıyor (yeni listelendi).
        Her 5sn'de fapi/v1/ticker/24hr çağırır, normalize edip fan_out.
        """
        url = f"{settings.binance_futures_url}/fapi/v1/ticker/24hr"
        params = {"symbol": "XAUUSDT"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            while not self._stop_event.is_set():
                try:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    msg = {
                        "type": "price",
                        "symbol": str(data["symbol"]),
                        "price": float(data["lastPrice"]),
                        "change_24h_pct": float(data["priceChangePercent"]),
                        "ts": int(data.get("closeTime") or time.time() * 1000),
                    }
                    self.latest[msg["symbol"]] = msg
                    await self._fan_out(msg["symbol"], msg)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.warning("xauusdt_rest_poll_failed", error=str(e))
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=XAUUSDT_REST_POLL_INTERVAL,
                    )
                    # stop_event set'lendi → çık
                    return
                except asyncio.TimeoutError:
                    continue  # döngüyü sürdür

    async def _fan_out(self, symbol: str, msg: dict[str, Any]) -> None:
        """Subscribed client'lara mesajı dağıt."""
        # Lock altında client listesini snapshot et (mutation safety)
        async with self._lock:
            subscribed = list(self.clients.get(symbol, set()))
        if not subscribed:
            return

        dead: list[WebSocket] = []
        for client in subscribed:
            try:
                await client.send_json(msg)
            except Exception as e:
                logger.debug("ws_client_send_failed", error=str(e))
                dead.append(client)

        if dead:
            async with self._lock:
                for s_clients in self.clients.values():
                    for d in dead:
                        s_clients.discard(d)


# Singleton instance
price_hub = PriceHub()
