"""Test için synthetic OHLCV üreticileri."""
from __future__ import annotations

from typing import Any

import numpy as np


def _kline(open_time_ms: int, o: float, h: float, low: float, c: float, v: float = 100.0) -> dict[str, Any]:
    return {
        "open_time": open_time_ms,
        "open": o,
        "high": h,
        "low": low,
        "close": c,
        "volume": v,
        "close_time": open_time_ms + 14_399_000,
        "quote_volume": v * c,
        "trades": 100,
    }


def linear_uptrend(n: int = 200, start: float = 100.0, step: float = 0.5) -> list[dict[str, Any]]:
    base_ms = 1_700_000_000_000
    out: list[dict[str, Any]] = []
    for i in range(n):
        c = start + step * i
        o = c - step * 0.3
        h = c + step * 0.2
        low = o - step * 0.2
        out.append(_kline(base_ms + i * 14_400_000, o, h, low, c))
    return out


def linear_downtrend(n: int = 200, start: float = 200.0, step: float = 0.5) -> list[dict[str, Any]]:
    base_ms = 1_700_000_000_000
    out: list[dict[str, Any]] = []
    for i in range(n):
        c = start - step * i
        o = c + step * 0.3
        h = o + step * 0.2
        low = c - step * 0.2
        out.append(_kline(base_ms + i * 14_400_000, o, h, low, c))
    return out


def accelerating_uptrend(n: int = 200, start: float = 100.0) -> list[dict[str, Any]]:
    """Hızlanan yukarı trend — MACD histogram sürekli pozitif kalır."""
    base_ms = 1_700_000_000_000
    out: list[dict[str, Any]] = []
    for i in range(n):
        # Quadratic + lineer: c = start + 0.3*i + 0.001*i^2
        c = start + 0.3 * i + 0.001 * i * i
        prev_c = out[-1]["close"] if out else c - 0.3
        o = prev_c
        h = max(o, c) + 0.1
        low = min(o, c) - 0.1
        out.append(_kline(base_ms + i * 14_400_000, o, h, low, c))
    return out


def decelerating_downtrend(n: int = 200, start: float = 300.0) -> list[dict[str, Any]]:
    """Quadratic downtrend — MACD histogram sürekli negatif."""
    base_ms = 1_700_000_000_000
    out: list[dict[str, Any]] = []
    for i in range(n):
        c = start - 0.3 * i - 0.001 * i * i
        prev_c = out[-1]["close"] if out else c + 0.3
        o = prev_c
        h = max(o, c) + 0.1
        low = min(o, c) - 0.1
        out.append(_kline(base_ms + i * 14_400_000, o, h, low, c))
    return out


def sideways(n: int = 200, mid: float = 100.0, amp: float = 2.0) -> list[dict[str, Any]]:
    base_ms = 1_700_000_000_000
    out: list[dict[str, Any]] = []
    for i in range(n):
        c = mid + amp * np.sin(i * 0.3)
        o = c - 0.1
        h = c + 0.5
        low = c - 0.5
        out.append(_kline(base_ms + i * 14_400_000, o, h, low, c))
    return out


def custom_path(prices: list[float]) -> list[dict[str, Any]]:
    base_ms = 1_700_000_000_000
    out: list[dict[str, Any]] = []
    for i, c in enumerate(prices):
        prev_c = prices[i - 1] if i > 0 else c
        o = prev_c
        h = max(o, c) + 0.05
        low = min(o, c) - 0.05
        out.append(_kline(base_ms + i * 14_400_000, o, h, low, c))
    return out


def _bar_from_close(c: float, prev_c: float, n_bars: int) -> dict[str, Any]:
    base_ms = 1_700_000_000_000
    # high/low doğrudan close'tan türet — pivot'lar tek bara odaklansın
    return _kline(base_ms + n_bars * 14_400_000, prev_c, c + 0.1, c - 0.1, c)


def zigzag_uptrend(cycles: int = 5, swing_size: int = 20) -> list[dict[str, Any]]:
    """Net HH+HL zigzag: her cycle peak ve dip kademeli yukarı."""
    klines: list[dict[str, Any]] = []
    base_price = 100.0
    step_per_cycle = 5.0

    for cycle in range(cycles):
        cycle_low = base_price + cycle * step_per_cycle
        cycle_high = cycle_low + 8.0
        for i in range(swing_size):
            t = (i + 1) / swing_size
            c = cycle_low + (cycle_high - cycle_low) * t
            prev = klines[-1]["close"] if klines else c
            klines.append(_bar_from_close(c, prev, len(klines)))
        next_low = cycle_low + step_per_cycle
        for i in range(swing_size):
            t = (i + 1) / swing_size
            c = cycle_high - (cycle_high - next_low) * t
            prev = klines[-1]["close"] if klines else c
            klines.append(_bar_from_close(c, prev, len(klines)))

    tail_price = klines[-1]["close"]
    for _ in range(15):
        prev = klines[-1]["close"]
        klines.append(_bar_from_close(tail_price, prev, len(klines)))

    return klines


def zigzag_downtrend(cycles: int = 5, swing_size: int = 20) -> list[dict[str, Any]]:
    """Net LH+LL zigzag."""
    klines: list[dict[str, Any]] = []
    base_price = 200.0
    step_per_cycle = 5.0

    for cycle in range(cycles):
        cycle_high = base_price - cycle * step_per_cycle
        cycle_low = cycle_high - 8.0
        for i in range(swing_size):
            t = (i + 1) / swing_size
            c = cycle_high - (cycle_high - cycle_low) * t
            prev = klines[-1]["close"] if klines else c
            klines.append(_bar_from_close(c, prev, len(klines)))
        next_high = cycle_high - step_per_cycle
        for i in range(swing_size):
            t = (i + 1) / swing_size
            c = cycle_low + (next_high - cycle_low) * t
            prev = klines[-1]["close"] if klines else c
            klines.append(_bar_from_close(c, prev, len(klines)))

    tail_price = klines[-1]["close"]
    for _ in range(15):
        prev = klines[-1]["close"]
        klines.append(_bar_from_close(tail_price, prev, len(klines)))

    return klines


def zigzag_for_divergence(
    pattern: str = "regular_bullish", base: float = 100.0, swing_size: int = 30
) -> tuple[list[dict[str, Any]], list[float]]:
    """Divergence test için zigzag + indikatör serisi.

    Pattern:
        regular_bullish: price LL, indicator HL (price 2. dip < 1. dip; ind 2. dip > 1. dip)
        regular_bearish: price HH, indicator LH (price 2. tepe > 1. tepe; ind 2. tepe < 1. tepe)

    İkinci swing sonuna `lookback + buffer` bar eklenir ki pivot detection yakalayabilsin.
    """
    base_ms = 1_700_000_000_000
    klines: list[dict[str, Any]] = []
    indicator: list[float] = []

    def _push(c: float, ind: float) -> None:
        prev = klines[-1]["close"] if klines else c
        # Tek bar pivot için: low/high doğrudan close'tan türet (prev'den bağımsız)
        h = c + 0.05
        low = c - 0.05
        klines.append(_kline(base_ms + len(klines) * 14_400_000, prev, h, low, c))
        indicator.append(ind)

    if pattern == "regular_bullish":
        # Faz 1: dipten tepeye
        peak = base + 5.0
        for i in range(swing_size):
            t = (i + 1) / swing_size
            _push(base + (peak - base) * t, 50 + t * 10)  # ind 50→60
        # Faz 2: tepe → ilk dip (low1 = base - 10)
        first_low = base - 10
        for i in range(swing_size):
            t = (i + 1) / swing_size
            _push(peak + (first_low - peak) * t, 60 + (30 - 60) * t)  # ind 60→30
        # Faz 3: ilk dipten tepeye
        for i in range(swing_size):
            t = (i + 1) / swing_size
            _push(first_low + (peak - first_low) * t, 30 + (55 - 30) * t)  # ind 30→55
        # Faz 4: tepe → ikinci dip (low2 = base - 15, daha düşük)
        second_low = base - 15
        for i in range(swing_size):
            t = (i + 1) / swing_size
            _push(peak + (second_low - peak) * t, 55 + (38 - 55) * t)  # ind 55→38 (HL: 38 > 30)
        # Tail buffer — pivot detection için ikinci dip etrafında bar olmalı
        for _ in range(15):
            _push(second_low + 1.0, 40.0)

    elif pattern == "regular_bearish":
        # Faz 1: dipten ilk tepeye (high1 = base + 10)
        first_high = base + 10
        for i in range(swing_size):
            t = (i + 1) / swing_size
            _push(base + (first_high - base) * t, 40 + (70 - 40) * t)
        # Faz 2: tepe → dip
        valley = base
        for i in range(swing_size):
            t = (i + 1) / swing_size
            _push(first_high + (valley - first_high) * t, 70 + (50 - 70) * t)
        # Faz 3: dipten ikinci tepeye (high2 = base + 15, daha yüksek)
        second_high = base + 15
        for i in range(swing_size):
            t = (i + 1) / swing_size
            _push(valley + (second_high - valley) * t, 50 + (60 - 50) * t)  # ind 50→60 (LH: 60 < 70)
        # Faz 4: tepe → dip
        for i in range(swing_size):
            t = (i + 1) / swing_size
            _push(second_high + (valley - second_high) * t, 60 + (45 - 60) * t)
        for _ in range(15):
            _push(valley - 1.0, 40.0)
    else:
        raise ValueError(f"Bilinmeyen pattern: {pattern}")

    return klines, indicator
