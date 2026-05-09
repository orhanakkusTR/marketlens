"""ATR — Average True Range (14 default).

USDT cinsinden mutlak değer + price'a göre yüzde olarak iki versiyon döner.
Risk hesabında her ikisi de kullanılır (stop mesafesi USDT, position sizing %).
"""
from __future__ import annotations

import pandas as pd
import pandas_ta as ta

from app.schemas.indicators import ATRResult


def compute_atr(df: pd.DataFrame, period: int = 14) -> ATRResult:
    series = ta.atr(df["high"], df["low"], df["close"], length=period)
    if series is None or series.dropna().empty:
        raise ValueError("ATR hesaplanamadı (yetersiz veri)")

    value = float(series.dropna().iloc[-1])
    price = float(df["close"].iloc[-1])
    pct = (value / price) * 100 if price > 0 else 0.0

    return ATRResult(
        value_usdt=value,
        value_pct=pct,
        period=period,
    )
