"""Divergence detection (regular + hidden) — RSI ve MACD histogram üzerinde.

Tipler:
    Regular bullish:  price LL + indicator HL  → dönüş yukarı
    Regular bearish:  price HH + indicator LH  → dönüş aşağı
    Hidden bullish:   price HL + indicator LL  → devam yukarı
    Hidden bearish:   price LH + indicator HH  → devam aşağı

Algoritma:
    1. Son `lookback` mum içinde fiyat swing high/low pivot'ları (lookback_bars=5)
    2. İndikatörden, fiyatın swing index'lerindeki değerleri al
    3. Son `min_swings` (default 2) high'ı ve low'ı karşılaştır
"""
from __future__ import annotations

from typing import Literal

import pandas as pd

from app.schemas.indicators import (
    DivergenceResult,
    DivergenceType,
    IndicatorSwing,
    SwingPoint,
)
from app.services.indicators.trend.market_structure import LOOKBACK as PIVOT_LOOKBACK


def _find_pivot_highs(prices: pd.Series, lookback: int) -> list[int]:
    """Pivot high index'leri (sol+sağ `lookback` window'da TEK maks bar)."""
    indices: list[int] = []
    n = len(prices)
    if n < 2 * lookback + 1:
        return indices
    values = prices.values
    for i in range(lookback, n - lookback):
        window = values[i - lookback : i + lookback + 1]
        max_val = window.max()
        if values[i] == max_val and int((window == max_val).sum()) == 1:
            indices.append(i)
    return indices


def _find_pivot_lows(prices: pd.Series, lookback: int) -> list[int]:
    indices: list[int] = []
    n = len(prices)
    if n < 2 * lookback + 1:
        return indices
    values = prices.values
    for i in range(lookback, n - lookback):
        window = values[i - lookback : i + lookback + 1]
        min_val = window.min()
        if values[i] == min_val and int((window == min_val).sum()) == 1:
            indices.append(i)
    return indices


def _classify_high(
    p_prev: float, p_curr: float, i_prev: float, i_curr: float
) -> DivergenceType | None:
    """High noktalarda divergence kontrolü."""
    price_higher = p_curr > p_prev
    price_lower = p_curr < p_prev
    ind_higher = i_curr > i_prev
    ind_lower = i_curr < i_prev

    if price_higher and ind_lower:
        return "regular_bearish"  # price HH + indicator LH
    if price_lower and ind_higher:
        return "hidden_bearish"  # price LH + indicator HH
    return None


def _classify_low(
    p_prev: float, p_curr: float, i_prev: float, i_curr: float
) -> DivergenceType | None:
    """Low noktalarda divergence kontrolü."""
    price_higher = p_curr > p_prev
    price_lower = p_curr < p_prev
    ind_higher = i_curr > i_prev
    ind_lower = i_curr < i_prev

    if price_lower and ind_higher:
        return "regular_bullish"  # price LL + indicator HL
    if price_higher and ind_lower:
        return "hidden_bullish"  # price HL + indicator LL
    return None


def detect_divergence(
    df: pd.DataFrame,
    indicator_series: pd.Series,
    lookback_bars: int = 100,
    min_swings: int = 2,
    pivot_lookback: int = PIVOT_LOOKBACK,
) -> DivergenceResult:
    """Son `lookback_bars` mum içinde divergence ara.

    `min_swings`: kaç swing geriye karşılaştır (default 2 = son ile bir öncesi).
    """
    if len(df) < lookback_bars:
        lookback_bars = len(df)

    sub_df = df.iloc[-lookback_bars:]
    sub_ind = indicator_series.iloc[-lookback_bars:]

    high_pivots = _find_pivot_highs(sub_df["high"], pivot_lookback)
    low_pivots = _find_pivot_lows(sub_df["low"], pivot_lookback)

    detected_type: DivergenceType = "none"
    price_swings: list[SwingPoint] = []
    ind_swings: list[IndicatorSwing] = []

    # High taraf — son min_swings high'ı kontrol et
    if len(high_pivots) >= min_swings:
        last_highs = high_pivots[-min_swings:]
        # En eski/en yeni karşılaştır (ilk ve son)
        prev_idx = last_highs[0]
        curr_idx = last_highs[-1]
        p_prev = float(sub_df["high"].iloc[prev_idx])
        p_curr = float(sub_df["high"].iloc[curr_idx])
        i_prev_val = sub_ind.iloc[prev_idx] if prev_idx < len(sub_ind) else None
        i_curr_val = sub_ind.iloc[curr_idx] if curr_idx < len(sub_ind) else None

        if i_prev_val is not None and i_curr_val is not None:
            if not (pd.isna(i_prev_val) or pd.isna(i_curr_val)):
                cls = _classify_high(p_prev, p_curr, float(i_prev_val), float(i_curr_val))
                if cls is not None:
                    detected_type = cls
                    price_swings = [
                        SwingPoint(
                            index=int(prev_idx),
                            timestamp_ms=int(sub_df["open_time_ms"].iloc[prev_idx]),
                            price=p_prev,
                            kind="HH" if p_curr > p_prev else "LH",
                        ),
                        SwingPoint(
                            index=int(curr_idx),
                            timestamp_ms=int(sub_df["open_time_ms"].iloc[curr_idx]),
                            price=p_curr,
                            kind="HH" if p_curr > p_prev else "LH",
                        ),
                    ]
                    ind_swings = [
                        IndicatorSwing(index=int(prev_idx), value=float(i_prev_val)),
                        IndicatorSwing(index=int(curr_idx), value=float(i_curr_val)),
                    ]

    # Low taraf — daha güçlü sinyal genelde dipte (regular bullish), high'tan sonra kontrol
    # Eğer high'ta divergence yoksa low'a bak
    if detected_type == "none" and len(low_pivots) >= min_swings:
        last_lows = low_pivots[-min_swings:]
        prev_idx = last_lows[0]
        curr_idx = last_lows[-1]
        p_prev = float(sub_df["low"].iloc[prev_idx])
        p_curr = float(sub_df["low"].iloc[curr_idx])
        i_prev_val = sub_ind.iloc[prev_idx] if prev_idx < len(sub_ind) else None
        i_curr_val = sub_ind.iloc[curr_idx] if curr_idx < len(sub_ind) else None

        if i_prev_val is not None and i_curr_val is not None:
            if not (pd.isna(i_prev_val) or pd.isna(i_curr_val)):
                cls = _classify_low(p_prev, p_curr, float(i_prev_val), float(i_curr_val))
                if cls is not None:
                    detected_type = cls
                    price_swings = [
                        SwingPoint(
                            index=int(prev_idx),
                            timestamp_ms=int(sub_df["open_time_ms"].iloc[prev_idx]),
                            price=p_prev,
                            kind="LL" if p_curr < p_prev else "HL",
                        ),
                        SwingPoint(
                            index=int(curr_idx),
                            timestamp_ms=int(sub_df["open_time_ms"].iloc[curr_idx]),
                            price=p_curr,
                            kind="LL" if p_curr < p_prev else "HL",
                        ),
                    ]
                    ind_swings = [
                        IndicatorSwing(index=int(prev_idx), value=float(i_prev_val)),
                        IndicatorSwing(index=int(curr_idx), value=float(i_curr_val)),
                    ]

    return DivergenceResult(
        detected=(detected_type != "none"),
        type=detected_type,
        price_swings=price_swings,
        indicator_swings=ind_swings,
    )
