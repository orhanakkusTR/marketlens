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
