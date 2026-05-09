"""yfinance — geleneksel finans verileri (GOLD, DXY, SP500, NASDAQ, VIX, US10Y).

yfinance senkron — `loop.run_in_executor` ile thread pool'a wrap'lanır.
Tenacity retry async wrapper'da; pybreaker call_async ile.
"""
from __future__ import annotations

import asyncio
from typing import Any

import yfinance as yf
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.cache import cached_call
from app.core.circuit_breaker import AsyncCircuitBreaker, CircuitBreakerError
from app.core.logging import get_logger

logger = get_logger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    """yfinance bazen rate limit veya geçici network hatası verir."""
    if isinstance(exc, CircuitBreakerError):
        return False
    # yfinance internal exceptions geniş — sadece breaker hatasını filtrele,
    # diğerlerini retry et
    return True


class YFinanceClient:
    """Geleneksel finans tickerları.

    Ticker mapping bizim sembol kodu → yahoo ticker:
        GOLD → GC=F (Gold futures)
        DXY  → DX-Y.NYB (Dollar Index)
        SP500→ ^GSPC
        NASDAQ→ ^IXIC
        VIX  → ^VIX
        US10Y→ ^TNX (10-year Treasury yield)
    """

    TICKERS: dict[str, str] = {
        "GOLD": "GC=F",
        "DXY": "DX-Y.NYB",
        "SP500": "^GSPC",
        "NASDAQ": "^IXIC",
        "VIX": "^VIX",
        "US10Y": "^TNX",
    }

    def __init__(self) -> None:
        self.breaker = AsyncCircuitBreaker(
            fail_max=5,
            reset_timeout=30.0,
            name="YFinanceClient",
        )

    async def get_history(
        self,
        symbol: str,
        period: str = "30d",
        interval: str = "1d",
    ) -> list[dict[str, Any]]:
        """Geçmiş fiyat serisi."""
        if symbol not in self.TICKERS:
            raise ValueError(f"Bilinmeyen yfinance symbol: {symbol}")

        ticker = self.TICKERS[symbol]
        return await cached_call(
            key=f"yf:{symbol}:{period}:{interval}",
            ttl=300,  # 5 dk
            fetch_fn=lambda: self._fetch_history(ticker, period, interval),
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    async def _fetch_history(
        self, ticker: str, period: str, interval: str
    ) -> list[dict[str, Any]]:
        loop = asyncio.get_event_loop()

        def _sync_fetch() -> list[dict[str, Any]]:
            t = yf.Ticker(ticker)
            df = t.history(period=period, interval=interval)
            if df.empty:
                return []
            df = df.reset_index()
            # Date/Datetime column'unu ISO string'e çevir (JSON serializable)
            for col in ("Date", "Datetime"):
                if col in df.columns:
                    df[col] = df[col].astype(str)
            return df.to_dict("records")

        async def _async_wrap() -> list[dict[str, Any]]:
            return await loop.run_in_executor(None, _sync_fetch)

        return await self.breaker.call(_async_wrap)

    async def get_current_price(self, symbol: str) -> float:
        """En son kapanış fiyatı."""
        history = await self.get_history(symbol, period="5d", interval="1d")
        if not history:
            raise RuntimeError(f"{symbol} için yfinance veri yok")
        return float(history[-1]["Close"])

    async def close(self) -> None:
        # yfinance persistent connection tutmuyor
        pass
