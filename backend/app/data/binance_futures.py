"""Binance Futures — funding rate, open interest, long/short ratio.

Public endpoints (fapi/v1/*) — API key gerekmez.
Likidasyon stream'i public REST'te yok; Coinglass entegrasyonunda (Adım 23).
"""
from __future__ import annotations

from typing import Any

from app.core.cache import cached_call
from app.core.config import settings
from app.data.base import AbstractDataClient
from app.data.binance_spot import TF_TO_INTERVAL, TF_TTL


class BinanceFuturesClient(AbstractDataClient):
    def __init__(self) -> None:
        super().__init__(base_url=settings.binance_futures_url)

    async def get_klines(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Futures OHLCV mumları (fapi/v1/klines).

        Spot pair'de listelenmemiş ama Binance Futures'ta listelenmiş sembollerin
        (ör. TradFi Perpetual XAUUSDT) kline'ları için. Yanıt formatı spot ile aynı.
        """
        if timeframe not in TF_TO_INTERVAL:
            raise ValueError(f"Bilinmeyen timeframe: {timeframe}")
        interval = TF_TO_INTERVAL[timeframe]
        ttl = TF_TTL[timeframe]
        return await cached_call(
            key=f"binance_futures:klines:{symbol}:{timeframe}:{limit}",
            ttl=ttl,
            fetch_fn=lambda: self._fetch_klines(symbol, interval, limit),
        )

    async def _fetch_klines(
        self, symbol: str, interval: str, limit: int
    ) -> list[dict[str, Any]]:
        response = await self.request(
            "GET",
            "/fapi/v1/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
        )
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

    async def get_funding_rate(self, symbol: str) -> dict[str, Any]:
        """Premium index — current funding + mark/index price."""
        return await cached_call(
            key=f"binance:funding:{symbol}",
            ttl=settings.cache_ttl_funding,
            fetch_fn=lambda: self._fetch_funding(symbol),
        )

    async def _fetch_funding(self, symbol: str) -> dict[str, Any]:
        response = await self.request(
            "GET", "/fapi/v1/premiumIndex", params={"symbol": symbol}
        )
        d = response.json()
        return {
            "symbol": d["symbol"],
            "mark_price": float(d["markPrice"]),
            "index_price": float(d["indexPrice"]),
            "funding_rate": float(d["lastFundingRate"]),
            "next_funding_time": d["nextFundingTime"],
        }

    async def get_open_interest(self, symbol: str) -> dict[str, Any]:
        """Anlık open interest."""
        return await cached_call(
            key=f"binance:oi:{symbol}",
            ttl=settings.cache_ttl_oi,
            fetch_fn=lambda: self._fetch_oi(symbol),
        )

    async def _fetch_oi(self, symbol: str) -> dict[str, Any]:
        response = await self.request(
            "GET", "/fapi/v1/openInterest", params={"symbol": symbol}
        )
        d = response.json()
        return {
            "symbol": d["symbol"],
            "open_interest": float(d["openInterest"]),
            "time": d["time"],
        }

    async def get_long_short_ratio(
        self, symbol: str, period: str = "1h"
    ) -> list[dict[str, Any]]:
        """Top trader long/short account ratio. period: 5m/15m/30m/1h/2h/4h/6h/12h/1d."""
        return await cached_call(
            key=f"binance:lsr:{symbol}:{period}",
            ttl=300,  # 5 dk
            fetch_fn=lambda: self._fetch_lsr(symbol, period),
        )

    async def _fetch_lsr(self, symbol: str, period: str) -> list[dict[str, Any]]:
        response = await self.request(
            "GET",
            "/futures/data/topLongShortAccountRatio",
            params={"symbol": symbol, "period": period, "limit": 30},
        )
        return [
            {
                "symbol": item["symbol"],
                "long_short_ratio": float(item["longShortRatio"]),
                "long_account": float(item["longAccount"]),
                "short_account": float(item["shortAccount"]),
                "timestamp": item["timestamp"],
            }
            for item in response.json()
        ]

    async def get_funding_history(
        self, symbol: str, limit: int = 24
    ) -> list[dict[str, Any]]:
        """Geçmiş funding ödemeleri (1 ödeme/8h). 24 = ~8 gün."""
        return await cached_call(
            key=f"binance:funding_hist:{symbol}:{limit}",
            ttl=300,  # 5dk
            fetch_fn=lambda: self._fetch_funding_history(symbol, limit),
        )

    async def _fetch_funding_history(
        self, symbol: str, limit: int
    ) -> list[dict[str, Any]]:
        response = await self.request(
            "GET",
            "/fapi/v1/fundingRate",
            params={"symbol": symbol, "limit": limit},
        )
        return [
            {
                "symbol": item["symbol"],
                "funding_rate": float(item["fundingRate"]),
                "funding_time": item["fundingTime"],
            }
            for item in response.json()
        ]

    async def get_oi_history(
        self, symbol: str, period: str = "5m", limit: int = 300
    ) -> list[dict[str, Any]]:
        """Open Interest geçmişi. period: 5m/15m/30m/1h/2h/4h/6h/12h/1d."""
        return await cached_call(
            key=f"binance:oi_hist:{symbol}:{period}:{limit}",
            ttl=300,
            fetch_fn=lambda: self._fetch_oi_history(symbol, period, limit),
        )

    async def _fetch_oi_history(
        self, symbol: str, period: str, limit: int
    ) -> list[dict[str, Any]]:
        response = await self.request(
            "GET",
            "/futures/data/openInterestHist",
            params={"symbol": symbol, "period": period, "limit": limit},
        )
        return [
            {
                "symbol": item["symbol"],
                "open_interest": float(item["sumOpenInterest"]),
                "open_interest_value": float(item["sumOpenInterestValue"]),
                "timestamp": item["timestamp"],
            }
            for item in response.json()
        ]
