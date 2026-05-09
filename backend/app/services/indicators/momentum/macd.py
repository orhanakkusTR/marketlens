"""MACD — 12/26/9 default."""
from __future__ import annotations

from typing import Literal

import pandas as pd
import pandas_ta as ta

from app.schemas.indicators import CrossState, MACDResult


def _histogram_direction(hist: pd.Series, lookback: int = 3) -> Literal["rising", "falling", "flat"]:
    valid = hist.dropna().tail(lookback)
    if len(valid) < 2:
        return "flat"
    diff = valid.iloc[-1] - valid.iloc[0]
    threshold = abs(valid).mean() * 0.05  # %5 threshold (gürültü için)
    if diff > threshold:
        return "rising"
    if diff < -threshold:
        return "falling"
    return "flat"


def _cross(macd: pd.Series, signal: pd.Series, lookback: int = 3) -> CrossState:
    if len(macd) < lookback + 1:
        return "none"
    for i in range(1, lookback + 1):
        m_now, m_prev = macd.iloc[-i], macd.iloc[-i - 1]
        s_now, s_prev = signal.iloc[-i], signal.iloc[-i - 1]
        if pd.isna(m_now) or pd.isna(m_prev) or pd.isna(s_now) or pd.isna(s_prev):
            continue
        if m_prev <= s_prev and m_now > s_now:
            return "bullish"
        if m_prev >= s_prev and m_now < s_now:
            return "bearish"
    return "none"


def compute_macd(
    df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
) -> MACDResult:
    macd_df = ta.macd(df["close"], fast=fast, slow=slow, signal=signal)
    if macd_df is None or macd_df.empty:
        raise ValueError("MACD hesaplanamadı")

    macd_col = f"MACD_{fast}_{slow}_{signal}"
    signal_col = f"MACDs_{fast}_{slow}_{signal}"
    hist_col = f"MACDh_{fast}_{slow}_{signal}"

    macd_series = macd_df[macd_col]
    signal_series = macd_df[signal_col]
    hist_series = macd_df[hist_col]

    if macd_series.dropna().empty:
        raise ValueError("MACD seri tamamen NaN")

    return MACDResult(
        macd=float(macd_series.iloc[-1]),
        signal=float(signal_series.iloc[-1]),
        histogram=float(hist_series.iloc[-1]),
        histogram_direction=_histogram_direction(hist_series, lookback=3),
        cross=_cross(macd_series, signal_series, lookback=3),
    )


def compute_macd_histogram_series(
    df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.Series:
    """Divergence detection için MACD histogram serisi."""
    macd_df = ta.macd(df["close"], fast=fast, slow=slow, signal=signal)
    if macd_df is None:
        raise ValueError("MACD seri hesaplanamadı")
    return macd_df[f"MACDh_{fast}_{slow}_{signal}"]
