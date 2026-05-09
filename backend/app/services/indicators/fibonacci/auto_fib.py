"""Auto Fibonacci — major swing tespit + retracement + extension.

Algoritma:
    1. Independent ZigZag, lookback=10 (market_structure'ın 5'inden büyük: major swing)
    2. Son 200 mum içinde son 2 swing pivot'unu bul
    3. İki pivot'tan en yenisi swing_high mı swing_low mu? Direction belirle:
        - Son pivot high, ondan önceki low → bullish leg (low → high)
        - Son pivot low, ondan önceki high → bearish leg (high → low)
    4. Retracement seviyeleri swing aralığı içinde
    5. Extension seviyeleri swing yönünde projeksiyon

Retracement ratios: 0.236, 0.382, 0.5, 0.618, 0.786
Extension ratios:   1.272, 1.618, 2.618
"""
from __future__ import annotations

import pandas as pd

from app.schemas.indicators import (
    FibDirection,
    FibLevel,
    FibonacciResult,
    FibSwing,
)

MAJOR_LOOKBACK = 10
DEFAULT_BARS_WINDOW = 200

RETRACEMENT_RATIOS: tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786)
EXTENSION_RATIOS: tuple[float, ...] = (1.272, 1.618, 2.618)


def _find_pivots(
    df: pd.DataFrame, lookback: int = MAJOR_LOOKBACK
) -> tuple[list[int], list[int]]:
    """Tek-bar uniqueness kontrolü ile high/low pivot index'leri."""
    n = len(df)
    if n < 2 * lookback + 1:
        return [], []

    high = df["high"].values
    low = df["low"].values

    high_pivots: list[int] = []
    low_pivots: list[int] = []

    for i in range(lookback, n - lookback):
        h_window = high[i - lookback : i + lookback + 1]
        l_window = low[i - lookback : i + lookback + 1]

        h_max = h_window.max()
        l_min = l_window.min()

        if high[i] == h_max and int((h_window == h_max).sum()) == 1:
            high_pivots.append(i)
        if low[i] == l_min and int((l_window == l_min).sum()) == 1:
            low_pivots.append(i)

    return high_pivots, low_pivots


def detect_major_swing(
    df: pd.DataFrame, bars_window: int = DEFAULT_BARS_WINDOW
) -> tuple[FibSwing, FibSwing, FibDirection] | None:
    """Son `bars_window` mum içinde son major swing high + swing low'u dön.

    Direction: hangi pivot daha yakın index'e? Son olan target, eski olan origin.
    Returns: (swing_low, swing_high, direction) — düzen sabit; direction yön söyler.
    """
    sub = df.tail(bars_window)
    high_pivots, low_pivots = _find_pivots(sub, lookback=MAJOR_LOOKBACK)

    if not high_pivots or not low_pivots:
        return None

    last_high_idx = high_pivots[-1]
    last_low_idx = low_pivots[-1]

    high_swing = FibSwing(
        price=float(sub["high"].iloc[last_high_idx]),
        index=int(last_high_idx),
        timestamp_ms=int(sub["open_time_ms"].iloc[last_high_idx]),
    )
    low_swing = FibSwing(
        price=float(sub["low"].iloc[last_low_idx]),
        index=int(last_low_idx),
        timestamp_ms=int(sub["open_time_ms"].iloc[last_low_idx]),
    )

    # En yeni pivot hangisi?
    direction: FibDirection
    if last_high_idx > last_low_idx:
        # Önce dip, sonra tepe → bullish leg (low → high)
        direction = "bullish"
    else:
        direction = "bearish"

    return low_swing, high_swing, direction


def _build_levels(
    low_price: float, high_price: float, direction: FibDirection
) -> list[FibLevel]:
    diff = high_price - low_price
    if diff <= 0:
        return []

    levels: list[FibLevel] = []

    # Retracement: bullish'te yukarıdan aşağı (high - r*diff), bearish'te tersine
    for r in RETRACEMENT_RATIOS:
        if direction == "bullish":
            price = high_price - r * diff
        else:  # bearish
            price = low_price + r * diff
        levels.append(FibLevel(ratio=r, price=price, kind="retracement"))

    # Extension: swing yönünde projeksiyon
    for r in EXTENSION_RATIOS:
        if direction == "bullish":
            price = low_price + r * diff  # 1.0 = high, 1.618 = high üstü
        else:
            price = high_price - r * diff
        levels.append(FibLevel(ratio=r, price=price, kind="extension"))

    return levels


def compute_fibonacci(df: pd.DataFrame) -> FibonacciResult | None:
    detected = detect_major_swing(df)
    if detected is None:
        return None

    low_swing, high_swing, direction = detected
    levels = _build_levels(low_swing.price, high_swing.price, direction)

    return FibonacciResult(
        direction=direction,
        swing_high=high_swing,
        swing_low=low_swing,
        levels=levels,
    )
