"""Trend hesabı: 24h / 7d / 30d.

`series` formatı: list[(timestamp_ms, value)] eski → yeni.
Daily granularity'de 24h ≈ 1 bar geri, 7d ≈ 7 bar geri, 30d ≈ 30 bar geri.
Yetersiz history → ilgili alan None.
"""
from __future__ import annotations

from app.schemas.macro import MetricTrend, TrendDirection

DIRECTION_THRESHOLD_PCT = 0.5  # ±0.5% altı flat


def _direction(change_pct: float | None) -> TrendDirection:
    if change_pct is None:
        return "flat"
    if change_pct > DIRECTION_THRESHOLD_PCT:
        return "up"
    if change_pct < -DIRECTION_THRESHOLD_PCT:
        return "down"
    return "flat"


def _change_pct(series: list[tuple[int, float]], bars_back: int) -> float | None:
    """En yeni değer ile `bars_back` önceki değer arasında %değişim.

    Yetersiz history → None.
    """
    if len(series) < bars_back + 1:
        return None
    new = series[-1][1]
    old = series[-1 - bars_back][1]
    if old <= 0:
        return None
    return ((new - old) / old) * 100


def compute_metric_trend(
    series: list[tuple[int, float]],
    bars_per_day: int = 1,
) -> MetricTrend:
    """Daily granularity için bars_per_day=1 (1 bar = 1 gün).

    24h: 1 bar geri
    7d:  7 bar geri
    30d: 30 bar geri (varsa)
    """
    if not series:
        raise ValueError("Trend hesabı için en az 1 bar gerekli")

    current = float(series[-1][1])
    change_24h = _change_pct(series, 1 * bars_per_day)
    change_7d = _change_pct(series, 7 * bars_per_day)
    change_30d = _change_pct(series, 30 * bars_per_day)

    return MetricTrend(
        current=current,
        change_24h_pct=change_24h,
        change_7d_pct=change_7d,
        change_30d_pct=change_30d,
        direction_24h=_direction(change_24h),
        direction_7d=_direction(change_7d),
        direction_30d=_direction(change_30d),
    )


def yfinance_history_to_series(history: list[dict]) -> list[tuple[int, float]]:
    """yfinance get_history → (ts_ms, close) tuple list."""
    series: list[tuple[int, float]] = []
    for row in history:
        # Date veya Datetime kolonu var, ISO string
        ts_str = row.get("Date") or row.get("Datetime")
        if ts_str is None or "Close" not in row:
            continue
        # ISO string → ms
        from datetime import datetime, timezone

        try:
            dt = datetime.fromisoformat(str(ts_str).replace(" ", "T"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            ts_ms = int(dt.timestamp() * 1000)
        except ValueError:
            continue
        try:
            close = float(row["Close"])
        except (ValueError, TypeError):
            continue
        series.append((ts_ms, close))
    return series
