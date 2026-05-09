"""Binance Spot — OHLCV mumları + anlık fiyat.

Public endpoints (api/v3/*) — API key gerekmez.
"""
from __future__ import annotations

from typing import Any

from app.core.cache import cached_call
from app.core.config import settings
from app.data.base import AbstractDataClient

# Bizim TF kodu → Binance interval string
TF_TO_INTERVAL: dict[str, str] = {
    "15m": "15m",
    "1H": "1h",
    "4H": "4h",
    "1D": "1d",
    "1W": "1w",
    "1M": "1M",
}

# Cache TTL (saniye) per timeframe — settings'ten + literal'lar
TF_TTL: dict[str, int] = {
    "15m": settings.cache_ttl_kline_15m,
    "1H": settings.cache_ttl_kline_1h,
    "4H": settings.cache_ttl_kline_4h,
    "1D": settings.cache_ttl_kline_1d,
    "1W": 21600,   # 6 saat (literal — .env'de yok)
    "1M": 43200,   # 12 saat
}


class BinanceSpotClient(AbstractDataClient):
    def __init__(self) -> None:
        super().__init__(base_url=settings.binance_spot_url)

    async def get_klines(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """OHLCV mumları çek.

        Returns: list of dict with open_time, open, high, low, close, volume,
                 close_time, quote_volume, trades.
        """
        if timeframe not in TF_TO_INTERVAL:
            raise ValueError(f"Bilinmeyen timeframe: {timeframe}")

        interval = TF_TO_INTERVAL[timeframe]
        ttl = TF_TTL[timeframe]

        return await cached_call(
            key=f"binance:klines:{symbol}:{timeframe}:{limit}",
            ttl=ttl,
            fetch_fn=lambda: self._fetch_klines(symbol, interval, limit),
        )

    async def _fetch_klines(
        self, symbol: str, interval: str, limit: int
    ) -> list[dict[str, Any]]:
        response = await self.request(
            "GET",
            "/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
        )
        # Binance format: [open_time, open, high, low, close, volume, close_time,
        #                  quote_volume, trades, ...]
        return [
            {
                "open_time": k[0],
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "close_time": k[6],
                "quote_volume": float(k[7]),
                "trades": int(k[8]),
            }
            for k in response.json()
        ]

    async def get_ticker_price(self, symbol: str) -> float:
        """Anlık fiyat (5 sn cache)."""
        return await cached_call(
            key=f"binance:price:{symbol}",
            ttl=5,
            fetch_fn=lambda: self._fetch_price(symbol),
        )

    async def _fetch_price(self, symbol: str) -> float:
        response = await self.request(
            "GET",
            "/api/v3/ticker/price",
            params={"symbol": symbol},
        )
        return float(response.json()["price"])
