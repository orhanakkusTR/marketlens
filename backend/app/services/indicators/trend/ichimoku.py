"""Ichimoku Cloud (9-26-52).

Tenkan-sen (Conversion): (high_9 + low_9) / 2
Kijun-sen (Base): (high_26 + low_26) / 2
Senkou Span A: (Tenkan + Kijun) / 2  (26 ileri)
Senkou Span B: (high_52 + low_52) / 2  (26 ileri)
Chikou Span: close (26 geri)

Cloud state:
    above  — price > max(senkou_a, senkou_b)
    below  — price < min(senkou_a, senkou_b)
    inside — arada
"""
from __future__ import annotations

import pandas as pd

from app.schemas.indicators import CloudState, CrossState, IchimokuResult


def _last_valid(series: pd.Series) -> float | None:
    """NaN olmayan en son değer."""
    valid = series.dropna()
    if valid.empty:
        return None
    return float(valid.iloc[-1])


def _tk_cross(tenkan: pd.Series, kijun: pd.Series, lookback: int = 3) -> CrossState:
    """Son `lookback` mumda Tenkan/Kijun crossover."""
    if len(tenkan) < lookback + 1 or len(kijun) < lookback + 1:
        return "none"

    for i in range(1, lookback + 1):
        idx_now = -i
        idx_prev = -i - 1
        t_now, t_prev = tenkan.iloc[idx_now], tenkan.iloc[idx_prev]
        k_now, k_prev = kijun.iloc[idx_now], kijun.iloc[idx_prev]
        if pd.isna(t_now) or pd.isna(t_prev) or pd.isna(k_now) or pd.isna(k_prev):
            continue
        if t_prev <= k_prev and t_now > k_now:
            return "bullish"
        if t_prev >= k_prev and t_now < k_now:
            return "bearish"
    return "none"


def compute_ichimoku(df: pd.DataFrame) -> IchimokuResult:
    """Klasik 9-26-52 Ichimoku.

    pandas-ta `ichimoku` projected span'ları ayrı DF'de döner; biz manuel hesaplıyoruz
    çünkü `tk_cross` ve "current" senkou değerleri için tutarlı index gerekli.
    """
    if len(df) < 52:
        raise ValueError(f"Ichimoku için en az 52 mum gerekli, {len(df)} verildi")

    high = df["high"]
    low = df["low"]
    close = df["close"]

    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
    senkou_a_raw = (tenkan + kijun) / 2  # current — projection için kaydırılmaz
    senkou_b_raw = (high.rolling(52).max() + low.rolling(52).min()) / 2
    chikou_raw = close  # display amacıyla 26 geri kaydırılır, current = close

    t_val = _last_valid(tenkan)
    k_val = _last_valid(kijun)
    sa_val = _last_valid(senkou_a_raw)
    sb_val = _last_valid(senkou_b_raw)
    ch_val = _last_valid(chikou_raw)

    if any(v is None for v in (t_val, k_val, sa_val, sb_val, ch_val)):
        raise ValueError("Ichimoku hesaplanamadı — yetersiz veri")

    price = float(close.iloc[-1])
    cloud_top = max(sa_val, sb_val)  # type: ignore[type-var]
    cloud_bottom = min(sa_val, sb_val)  # type: ignore[type-var]

    cloud_state: CloudState
    if price > cloud_top:
        cloud_state = "above"
    elif price < cloud_bottom:
        cloud_state = "below"
    else:
        cloud_state = "inside"

    cross: CrossState = _tk_cross(tenkan, kijun, lookback=3)

    return IchimokuResult(
        tenkan=t_val,  # type: ignore[arg-type]
        kijun=k_val,  # type: ignore[arg-type]
        senkou_a=sa_val,  # type: ignore[arg-type]
        senkou_b=sb_val,  # type: ignore[arg-type]
        chikou=ch_val,  # type: ignore[arg-type]
        cloud_state=cloud_state,
        tk_cross=cross,
    )
