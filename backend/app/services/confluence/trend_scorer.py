"""Trend confluence skorlayıcısı.

Toplam: ±100 (1D'de ±110 olabilir, clamp'lenir).

Bileşenler:
    MA dizilimi          ±30
    Fiyat MA200 üstü    ±20
    Ichimoku            ±20  (cloud_state ±20 + tk_cross ±5 → clamp ±20)
    Market structure    ±30
    1D bonus            ±10  (sadece 1D, SMA200 ±5% buffer)
"""
from __future__ import annotations

from app.schemas.indicators import TrendIndicators


def _clamp(value: float, lo: float = -100, hi: float = 100) -> float:
    return max(lo, min(hi, value))


def _ma_alignment_score(trend: TrendIndicators) -> float:
    a = trend.moving_averages.alignment
    if a == "bullish_stack":
        return 30.0
    if a == "bearish_stack":
        return -30.0
    return 0.0


def _ma200_distance_score(trend: TrendIndicators) -> float:
    """Fiyat MA200 (period=200) üstünde mi?

    1D için SMA200, diğer TF'ler için EMA200. period=200 aramayla bul.
    1W/1M için MA200 yerine en uzun (SMA200) mevcut.
    """
    for ma in trend.moving_averages.moving_averages:
        if ma.period == 200:
            if ma.distance_pct > 0:
                return 20.0
            if ma.distance_pct < 0:
                return -20.0
            return 0.0
    return 0.0  # MA200 yoksa nötr


def _ichimoku_score(trend: TrendIndicators) -> float:
    base = 0.0
    if trend.ichimoku.cloud_state == "above":
        base = 20.0
    elif trend.ichimoku.cloud_state == "below":
        base = -20.0

    cross_bonus = 0.0
    if trend.ichimoku.tk_cross == "bullish":
        cross_bonus = 5.0
    elif trend.ichimoku.tk_cross == "bearish":
        cross_bonus = -5.0

    return _clamp(base + cross_bonus, -20, 20)


def _market_structure_score(trend: TrendIndicators) -> float:
    s = trend.market_structure.structure
    if s == "uptrend":
        return 30.0
    if s == "downtrend":
        return -30.0
    return 0.0


def _daily_bonus(trend: TrendIndicators, timeframe: str) -> float:
    """1D'de SMA200'den ±5% uzakta ise ±10 bonus."""
    if timeframe != "1D":
        return 0.0
    for ma in trend.moving_averages.moving_averages:
        if ma.period == 200 and ma.type == "SMA":
            if ma.distance_pct > 5.0:
                return 10.0
            if ma.distance_pct < -5.0:
                return -10.0
            return 0.0
    return 0.0


def score_trend(trend: TrendIndicators, timeframe: str) -> float:
    raw = (
        _ma_alignment_score(trend)
        + _ma200_distance_score(trend)
        + _ichimoku_score(trend)
        + _market_structure_score(trend)
        + _daily_bonus(trend, timeframe)
    )
    return _clamp(raw)
