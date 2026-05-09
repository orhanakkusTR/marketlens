"""Macro trends helper testleri."""
from __future__ import annotations

import pytest

from app.services.macro.trends import (
    DIRECTION_THRESHOLD_PCT,
    _change_pct,
    _direction,
    compute_metric_trend,
    yfinance_history_to_series,
)


def test_direction_up_above_threshold() -> None:
    assert _direction(DIRECTION_THRESHOLD_PCT + 0.1) == "up"


def test_direction_down_below_threshold() -> None:
    assert _direction(-DIRECTION_THRESHOLD_PCT - 0.1) == "down"


def test_direction_flat_in_band() -> None:
    assert _direction(0.0) == "flat"
    assert _direction(0.4) == "flat"
    assert _direction(-0.4) == "flat"


def test_direction_none_returns_flat() -> None:
    assert _direction(None) == "flat"


def test_change_pct_basic() -> None:
    series = [(1, 100.0), (2, 110.0)]
    assert _change_pct(series, 1) == pytest.approx(10.0)


def test_change_pct_insufficient_history_returns_none() -> None:
    series = [(1, 100.0)]
    assert _change_pct(series, 7) is None


def test_change_pct_zero_old_returns_none() -> None:
    series = [(1, 0.0), (2, 100.0)]
    assert _change_pct(series, 1) is None


def test_compute_metric_trend_full_history() -> None:
    # 31 günlük seri: günde 1% artış
    series = [(i * 86400_000, 100.0 * (1.01 ** i)) for i in range(31)]
    trend = compute_metric_trend(series, bars_per_day=1)

    assert trend.current == pytest.approx(100.0 * (1.01 ** 30))
    assert trend.change_24h_pct == pytest.approx(1.0, abs=0.01)
    # 7d ≈ 1.01^7 - 1 = ~7.2%
    assert trend.change_7d_pct is not None
    assert trend.change_7d_pct > 5
    # 30d ≈ 34.8%
    assert trend.change_30d_pct is not None
    assert trend.change_30d_pct > 30
    assert trend.direction_24h == "up"
    assert trend.direction_7d == "up"
    assert trend.direction_30d == "up"


def test_compute_metric_trend_partial_history() -> None:
    # Sadece 5 bar — 7d ve 30d None
    series = [(i, 100.0 + i) for i in range(5)]
    trend = compute_metric_trend(series, bars_per_day=1)
    assert trend.change_24h_pct is not None
    assert trend.change_7d_pct is None
    assert trend.change_30d_pct is None
    assert trend.direction_7d == "flat"
    assert trend.direction_30d == "flat"


def test_compute_metric_trend_empty_raises() -> None:
    with pytest.raises(ValueError, match="en az 1 bar"):
        compute_metric_trend([])


def test_yfinance_history_to_series_iso_string() -> None:
    history = [
        {"Date": "2026-05-01", "Close": 100.0},
        {"Date": "2026-05-02", "Close": 102.0},
    ]
    series = yfinance_history_to_series(history)
    assert len(series) == 2
    assert series[0][1] == 100.0
    assert series[1][1] == 102.0
    assert series[0][0] < series[1][0]


def test_yfinance_history_to_series_skips_invalid() -> None:
    history = [
        {"Date": "bad-date", "Close": 100.0},
        {"Close": 200.0},  # eksik Date
        {"Date": "2026-05-01", "Close": 300.0},
    ]
    series = yfinance_history_to_series(history)
    assert len(series) == 1
    assert series[0][1] == 300.0
