"""Moving Averages (EMA + SMA) — TF-aware.

CLAUDE.md tablosu:
    15m, 1H, 4H → EMA 50/100/200
    1D          → EMA 50/100 + SMA 200
    1W, 1M      → SMA 50/100/200
"""
from __future__ import annotations

import pandas as pd
import pandas_ta as ta

from app.schemas.indicators import (
    Alignment,
    MovingAverage,
    MovingAveragesResult,
)

# TF → {periyot: ma_tipi}
MA_STRATEGY: dict[str, dict[int, str]] = {
    "15m": {50: "EMA", 100: "EMA", 200: "EMA"},
    "1H":  {50: "EMA", 100: "EMA", 200: "EMA"},
    "4H":  {50: "EMA", 100: "EMA", 200: "EMA"},
    "1D":  {50: "EMA", 100: "EMA", 200: "SMA"},
    "1W":  {50: "SMA", 100: "SMA", 200: "SMA"},
    "1M":  {50: "SMA", 100: "SMA", 200: "SMA"},
}


def _alignment(price: float, mas: list[MovingAverage]) -> Alignment:
    """Bullish stack: price > MA50 > MA100 > MA200. Tersi: bearish_stack."""
    if len(mas) < 3:
        return "mixed"
    by_period = {ma.period: ma.value for ma in mas}
    if 50 not in by_period or 100 not in by_period or 200 not in by_period:
        return "mixed"

    m50 = by_period[50]
    m100 = by_period[100]
    m200 = by_period[200]

    if price > m50 > m100 > m200:
        return "bullish_stack"
    if price < m50 < m100 < m200:
        return "bearish_stack"
    return "mixed"


def compute_moving_averages(df: pd.DataFrame, timeframe: str) -> MovingAveragesResult:
    """TF-uygun EMA/SMA setini hesapla.

    `df` index DatetimeIndex, close kolonu olmalı.
    NaN'lı periyot (data yetersiz) → o MA atlanır.
    """
    if timeframe not in MA_STRATEGY:
        raise ValueError(f"Bilinmeyen timeframe: {timeframe}")

    strategy = MA_STRATEGY[timeframe]
    close = df["close"]
    price = float(close.iloc[-1])

    mas: list[MovingAverage] = []
    for period, ma_type in strategy.items():
        if ma_type == "EMA":
            series = ta.ema(close, length=period)
        else:
            series = ta.sma(close, length=period)

        if series is None or series.empty:
            continue

        last = series.iloc[-1]
        if pd.isna(last):
            continue

        value = float(last)
        distance_pct = ((price - value) / value) * 100
        mas.append(
            MovingAverage(
                period=period,
                type=ma_type,  # type: ignore[arg-type]
                value=value,
                distance_pct=distance_pct,
            )
        )

    return MovingAveragesResult(
        timeframe=timeframe,
        price=price,
        moving_averages=mas,
        alignment=_alignment(price, mas),
    )
