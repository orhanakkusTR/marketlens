"""Alternative.me Fear & Greed Index."""
from __future__ import annotations

from typing import Any

from app.core.cache import cached_call
from app.core.config import settings
from app.data.base import AbstractDataClient


class AlternativeMeClient(AbstractDataClient):
    def __init__(self) -> None:
        super().__init__(base_url="https://api.alternative.me")

    async def get_fear_greed(self) -> dict[str, Any]:
        """Son F&G değeri (0-100, classification: Extreme Fear/Fear/Neutral/Greed/Extreme Greed)."""
        return await cached_call(
            key="fng:latest",
            ttl=settings.cache_ttl_fear_greed,
            fetch_fn=self._fetch,
        )

    async def _fetch(self) -> dict[str, Any]:
        response = await self.request("GET", "/fng/", params={"limit": 1})
        d = response.json()["data"][0]
        return {
            "value": int(d["value"]),
            "classification": d["value_classification"],
            "timestamp": d["timestamp"],
        }

    async def get_history(self, limit: int = 8) -> list[dict[str, Any]]:
        """Son `limit` günlük F&G geçmişi. limit=8 → bugün + 7 gün önce.

        Alternative.me yeniden eskiye sırada döner; biz eski → yeni çeviriyoruz.
        """
        return await cached_call(
            key=f"fng:history:{limit}",
            ttl=3600,  # 1 saat
            fetch_fn=lambda: self._fetch_history(limit),
        )

    async def _fetch_history(self, limit: int) -> list[dict[str, Any]]:
        response = await self.request("GET", "/fng/", params={"limit": limit})
        items = response.json()["data"]
        # API yeniden eskiye sıralı — ters çevir (eski → yeni)
        items.reverse()
        return [
            {
                "value": int(item["value"]),
                "classification": item["value_classification"],
                "timestamp": item["timestamp"],
            }
            for item in items
        ]
