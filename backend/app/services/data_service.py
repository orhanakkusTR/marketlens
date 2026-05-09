"""Unified data service facade.

Tüm external client'ları tek nokta üzerinden expose eder. Endpoint'ler ve
servisler bu facade'ı kullanır, doğrudan client'a bağlanmaz.
"""
from __future__ import annotations

import asyncio
from typing import Any

from app.data.binance_depth import BinanceDepthClient
from app.data.binance_futures import BinanceFuturesClient
from app.data.binance_spot import BinanceSpotClient
from app.data.binance_ws import BinanceWebSocketClient
from app.data.coingecko import CoinGeckoClient
from app.data.fear_greed import AlternativeMeClient
from app.data.yfinance_client import YFinanceClient


class DataService:
    def __init__(self) -> None:
        self.binance_spot = BinanceSpotClient()
        self.binance_futures = BinanceFuturesClient()
        self.binance_depth = BinanceDepthClient()
        self.binance_ws = BinanceWebSocketClient()
        self.coingecko = CoinGeckoClient()
        self.yfinance = YFinanceClient()
        self.fear_greed = AlternativeMeClient()

    # ─── Binance Spot ───
    async def get_klines(
        self, symbol: str, timeframe: str, limit: int = 500
    ) -> list[dict[str, Any]]:
        return await self.binance_spot.get_klines(symbol, timeframe, limit)

    async def get_ticker_price(self, symbol: str) -> float:
        return await self.binance_spot.get_ticker_price(symbol)

    # ─── Binance Futures ───
    async def get_funding(self, symbol: str) -> dict[str, Any]:
        return await self.binance_futures.get_funding_rate(symbol)

    async def get_oi(self, symbol: str) -> dict[str, Any]:
        return await self.binance_futures.get_open_interest(symbol)

    async def get_long_short_ratio(
        self, symbol: str, period: str = "1h"
    ) -> list[dict[str, Any]]:
        return await self.binance_futures.get_long_short_ratio(symbol, period)

    # ─── Order Book ───
    async def get_orderbook(self, symbol: str, limit: int = 1000) -> dict[str, Any]:
        return await self.binance_depth.get_orderbook(symbol, limit)

    # ─── CoinGecko (Macro — Crypto) ───
    async def get_total(self) -> float:
        return await self.coingecko.get_total()

    async def get_total2(self) -> float:
        return await self.coingecko.get_total2()

    async def get_total3(self) -> float:
        return await self.coingecko.get_total3()

    async def get_btc_dominance(self) -> float:
        return await self.coingecko.get_btc_dominance()

    async def get_eth_dominance(self) -> float:
        return await self.coingecko.get_eth_dominance()

    # ─── yfinance (Macro — TradFi) ───
    async def get_dxy(self) -> float:
        return await self.yfinance.get_current_price("DXY")

    async def get_sp500(self) -> float:
        return await self.yfinance.get_current_price("SP500")

    async def get_nasdaq(self) -> float:
        return await self.yfinance.get_current_price("NASDAQ")

    async def get_vix(self) -> float:
        return await self.yfinance.get_current_price("VIX")

    async def get_gold(self) -> float:
        return await self.yfinance.get_current_price("GOLD")

    async def get_us10y(self) -> float:
        return await self.yfinance.get_current_price("US10Y")

    # ─── Fear & Greed ───
    async def get_fear_greed(self) -> dict[str, Any]:
        return await self.fear_greed.get_fear_greed()

    # ─── Lifecycle ───
    async def close(self) -> None:
        await asyncio.gather(
            self.binance_spot.close(),
            self.binance_futures.close(),
            self.binance_depth.close(),
            self.coingecko.close(),
            self.fear_greed.close(),
            self.yfinance.close(),
            return_exceptions=True,
        )


# Modül seviyesi singleton — main.py lifespan'de close edilir.
data_service = DataService()
