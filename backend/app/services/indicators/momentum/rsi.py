"""RSI (Relative Strength Index) — 14 period default."""
from __future__ import annotations

import pandas as pd
import pandas_ta as ta

from app.schemas.indicators import RSIResult, RSIState


def _state(value: float) -> RSIState:
    if value >= 70:
        return "overbought"
    if value <= 30:
        return "oversold"
    return "neutral"


def compute_rsi(df: pd.DataFrame, period: int = 14, history_len: int = 50) -> RSIResult:
    rsi = ta.rsi(df["close"], length=period)
    if rsi is None or rsi.dropna().empty:
        raise ValueError("RSI hesaplanamadı (yetersiz veri)")

    rsi_clean = rsi.dropna()
    current = float(rsi_clean.iloc[-1])
    history = [float(v) for v in rsi_clean.tail(history_len).tolist()]

    return RSIResult(
        current=current,
        history=history,
        state=_state(current),
    )


def compute_rsi_series(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Divergence detection için tam seri."""
    series = ta.rsi(df["close"], length=period)
    if series is None:
        raise ValueError("RSI seri hesaplanamadı")
    return series
