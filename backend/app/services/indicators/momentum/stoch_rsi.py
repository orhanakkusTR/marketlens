"""Stochastic RSI — 14/14/3/3 (rsi_length / stoch_length / k / d)."""
from __future__ import annotations

import pandas as pd
import pandas_ta as ta

from app.schemas.indicators import CrossState, RSIState, StochRSIResult


def _state(k: float) -> RSIState:
    # StochRSI 0-100 arası; klasik 80/20 thresholdu
    if k >= 80:
        return "overbought"
    if k <= 20:
        return "oversold"
    return "neutral"


def _cross(k_series: pd.Series, d_series: pd.Series, lookback: int = 3) -> CrossState:
    if len(k_series) < lookback + 1:
        return "none"
    for i in range(1, lookback + 1):
        k_now, k_prev = k_series.iloc[-i], k_series.iloc[-i - 1]
        d_now, d_prev = d_series.iloc[-i], d_series.iloc[-i - 1]
        if pd.isna(k_now) or pd.isna(k_prev) or pd.isna(d_now) or pd.isna(d_prev):
            continue
        if k_prev <= d_prev and k_now > d_now:
            return "bullish"
        if k_prev >= d_prev and k_now < d_now:
            return "bearish"
    return "none"


def compute_stoch_rsi(
    df: pd.DataFrame,
    rsi_length: int = 14,
    stoch_length: int = 14,
    k: int = 3,
    d: int = 3,
) -> StochRSIResult:
    result = ta.stochrsi(
        df["close"], length=stoch_length, rsi_length=rsi_length, k=k, d=d
    )
    if result is None or result.empty:
        raise ValueError("Stoch RSI hesaplanamadı")

    k_col = f"STOCHRSIk_{stoch_length}_{rsi_length}_{k}_{d}"
    d_col = f"STOCHRSId_{stoch_length}_{rsi_length}_{k}_{d}"

    k_series = result[k_col]
    d_series = result[d_col]

    if k_series.dropna().empty:
        raise ValueError("Stoch RSI K serisi tamamen NaN")

    k_val = float(k_series.iloc[-1])
    d_val = float(d_series.iloc[-1])

    return StochRSIResult(
        k=k_val,
        d=d_val,
        state=_state(k_val),
        cross=_cross(k_series, d_series, lookback=3),
    )
