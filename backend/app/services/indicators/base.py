"""Indicator engine — ortak yardımcılar.

- klines (list[dict]) → pandas.DataFrame builder
- CPU-bound senkron hesapları thread pool'da çalıştıran async wrapper
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, TypeVar

import pandas as pd

T = TypeVar("T")


def klines_to_dataframe(klines: list[dict[str, Any]]) -> pd.DataFrame:
    """Binance kline list → DataFrame.

    Index: open_time (DatetimeIndex, UTC).
    Columns: open, high, low, close, volume + open_time_ms (raw ms).
    """
    if not klines:
        raise ValueError("klines boş — DataFrame oluşturulamaz")

    df = pd.DataFrame(klines)
    required = {"open_time", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"klines içinde eksik kolonlar: {missing}")

    df["open_time_ms"] = df["open_time"].astype("int64")
    df["dt"] = pd.to_datetime(df["open_time_ms"], unit="ms", utc=True)
    df = df.set_index("dt")
    return df


async def run_cpu_bound(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Senkron CPU-bound fonksiyonu thread pool'da çalıştır."""
    loop = asyncio.get_running_loop()
    if kwargs:
        def _call() -> T:
            return fn(*args, **kwargs)

        return await loop.run_in_executor(None, _call)
    return await loop.run_in_executor(None, fn, *args)
