"""Binance Depth (Order Book)."""
from __future__ import annotations

from typing import Any

from app.core.cache import cached_call
from app.core.config import settings
from app.data.base import AbstractDataClient


class BinanceDepthClient(AbstractDataClient):
    def __init__(self) -> None:
        super().__init__(base_url=settings.binance_spot_url)

    async def get_orderbook(
        self, symbol: str, limit: int = 1000
    ) -> dict[str, Any]:
        """Order book — bids/asks. limit: 5/10/20/50/100/500/1000/5000."""
        return await cached_call(
            key=f"binance:orderbook:{symbol}:{limit}",
            ttl=settings.cache_ttl_orderbook,
            fetch_fn=lambda: self._fetch_orderbook(symbol, limit),
        )

    async def _fetch_orderbook(
        self, symbol: str, limit: int
    ) -> dict[str, Any]:
        response = await self.request(
            "GET", "/api/v3/depth", params={"symbol": symbol, "limit": limit}
        )
        d = response.json()
        return {
            "last_update_id": d["lastUpdateId"],
            "bids": [[float(p), float(q)] for p, q in d["bids"]],
            "asks": [[float(p), float(q)] for p, q in d["asks"]],
        }
