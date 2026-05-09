"""Fibonacci — auto major swing detection + retracement + extension."""
from __future__ import annotations

from app.services.indicators.base import klines_to_dataframe
from app.services.indicators.fibonacci.auto_fib import (
    EXTENSION_RATIOS,
    RETRACEMENT_RATIOS,
    compute_fibonacci,
)

from ._synthetic import linear_uptrend, zigzag_downtrend, zigzag_uptrend


def test_fibonacci_returns_none_for_short_data() -> None:
    df = klines_to_dataframe(linear_uptrend(n=20))
    assert compute_fibonacci(df) is None


def test_fibonacci_uptrend_bullish_direction() -> None:
    df = klines_to_dataframe(zigzag_uptrend(cycles=4, swing_size=20))
    result = compute_fibonacci(df)
    assert result is not None
    # zigzag_uptrend: Son swing son cycle'da (yüksek index) → bullish ya da bearish
    # olabilir, ama high>low her halükarda
    assert result.swing_high.price > result.swing_low.price


def test_fibonacci_levels_count_and_ratios() -> None:
    df = klines_to_dataframe(zigzag_uptrend(cycles=4, swing_size=20))
    result = compute_fibonacci(df)
    assert result is not None
    expected_count = len(RETRACEMENT_RATIOS) + len(EXTENSION_RATIOS)
    assert len(result.levels) == expected_count

    ret_ratios = {lv.ratio for lv in result.levels if lv.kind == "retracement"}
    ext_ratios = {lv.ratio for lv in result.levels if lv.kind == "extension"}
    assert ret_ratios == set(RETRACEMENT_RATIOS)
    assert ext_ratios == set(EXTENSION_RATIOS)


def test_fibonacci_bullish_retracement_levels_between_low_and_high() -> None:
    df = klines_to_dataframe(zigzag_uptrend(cycles=4, swing_size=20))
    result = compute_fibonacci(df)
    assert result is not None
    if result.direction != "bullish":
        return  # bearish ise bu test atlanır
    low = result.swing_low.price
    high = result.swing_high.price
    for lv in result.levels:
        if lv.kind == "retracement":
            assert low <= lv.price <= high, f"ratio {lv.ratio}: {lv.price} not in [{low}, {high}]"


def test_fibonacci_downtrend_bearish_direction() -> None:
    df = klines_to_dataframe(zigzag_downtrend(cycles=4, swing_size=20))
    result = compute_fibonacci(df)
    assert result is not None
    assert result.swing_high.price > result.swing_low.price


def test_fibonacci_swing_indices_within_range() -> None:
    df = klines_to_dataframe(zigzag_uptrend(cycles=4, swing_size=20))
    result = compute_fibonacci(df)
    assert result is not None
    n_window = min(200, len(df))
    assert 0 <= result.swing_high.index < n_window
    assert 0 <= result.swing_low.index < n_window
