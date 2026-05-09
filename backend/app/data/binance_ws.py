"""Binance WebSocket — minimum implementation.

Tek symbol stream + auto-reconnect on disconnect.
Multi-symbol state management ve callback dispatcher Step 19'da yapılacak.
"""
from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import websockets

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class BinanceWebSocketClient:
    def __init__(self) -> None:
        self.base_url = settings.binance_ws_url

    async def stream_ticker(
        self,
        symbol: str,
        callback: Callable[[dict[str, Any]], Awaitable[None]],
        max_messages: int | None = None,
    ) -> None:
        """`<symbol>@ticker` stream'i dinler. Auto-reconnect on disconnect.

        Args:
            symbol: BTCUSDT, ETHUSDT vs.
            callback: Her mesaj için awaitable.
            max_messages: None (sonsuz) veya N (N mesaj sonra return — test için).
        """
        url = f"{self.base_url}/{symbol.lower()}@ticker"
        message_count = 0

        async for ws in websockets.connect(url):
            try:
                async for raw in ws:
                    data = json.loads(raw)
                    await callback(data)
                    message_count += 1
                    if max_messages is not None and message_count >= max_messages:
                        return
            except websockets.ConnectionClosed:
                logger.warning("ws_disconnected_reconnecting", symbol=symbol)
                continue
