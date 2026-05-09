"""CoinGecko — TOTAL, TOTAL2, TOTAL3, BTC.D, ETH.D.

Free tier: 30 call/dk. Cache 5 dk → bol bol limit içinde.
"""
from __future__ import annotations

from typing import Any

from app.core.cache import redis_cache
from app.core.config import settings
from app.data.base import AbstractDataClient


class CoinGeckoClient(AbstractDataClient):
    def __init__(self) -> None:
        super().__init__(base_url=settings.coingecko_base_url)

    @redis_cache("cg:global", ttl=settings.cache_ttl_macro)
    async def get_global(self) -> dict[str, Any]:
        """Tüm kripto pazar verileri tek call. Diğer helper'lar bunu kullanır."""
        response = await self.request("GET", "/global")
        return response.json()["data"]

    async def get_total(self) -> float:
        data = await self.get_global()
        return float(data["total_market_cap"]["usd"])

    async def get_btc_dominance(self) -> float:
        data = await self.get_global()
        return float(data["market_cap_percentage"]["btc"])

    async def get_eth_dominance(self) -> float:
        data = await self.get_global()
        return float(data["market_cap_percentage"]["eth"])

    async def get_total2(self) -> float:
        """TOTAL eksi BTC. TOTAL * (1 - BTC.D/100)."""
        data = await self.get_global()
        total = float(data["total_market_cap"]["usd"])
        btc_d = float(data["market_cap_percentage"]["btc"])
        return total * (1 - btc_d / 100)

    async def get_total3(self) -> float:
        """TOTAL eksi BTC eksi ETH."""
        data = await self.get_global()
        total = float(data["total_market_cap"]["usd"])
        btc_d = float(data["market_cap_percentage"]["btc"])
        eth_d = float(data["market_cap_percentage"]["eth"])
        return total * (1 - (btc_d + eth_d) / 100)

    @redis_cache("cg:mcap_history:{coin_id}:{days}", ttl=3600)  # 1 saat
    async def get_market_cap_history(
        self, coin_id: str = "bitcoin", days: int = 30
    ) -> list[tuple[int, float]]:
        """Coin market cap historical timeseries.

        Returns: [(ts_ms, market_cap_usd), ...] eski → yeni.
        Free tier: günlük granularity (days >= 2 için), saatlik (days <= 1).
        """
        response = await self.request(
            "GET",
            f"/coins/{coin_id}/market_chart",
            params={"vs_currency": "usd", "days": days, "interval": "daily"},
        )
        data = response.json()
        # market_caps: [[timestamp_ms, value], ...]
        return [(int(ts), float(val)) for ts, val in data["market_caps"]]
