"""Momentum confluence skorlayıcısı.

Toplam ±100:
    RSI            ±25
    MACD           ±30  (histogram ±20 + direction ±10)
    StochRSI       ±25  (k vs d konum + extreme)
    Divergence     ±20  (RSI veya MACD'den en güçlü)
"""
from __future__ import annotations

from app.schemas.indicators import (
    DivergenceResult,
    MACDResult,
    MomentumIndicators,
    RSIResult,
    StochRSIResult,
)


def _clamp(value: float, lo: float = -100, hi: float = 100) -> float:
    return max(lo, min(hi, value))


def _rsi_score(rsi: RSIResult) -> float:
    v = rsi.current
    if v >= 70:
        return 10.0  # overbought — momentum güçlü ama exhaustion riski
    if v >= 60:
        return 25.0  # en sağlıklı bullish
    if v >= 50:
        return 15.0
    if v >= 40:
        return -15.0
    if v >= 30:
        return -25.0
    return -10.0  # oversold — bearish ama dönüş riski


def _macd_score(macd: MACDResult) -> float:
    sign = 20.0 if macd.histogram > 0 else (-20.0 if macd.histogram < 0 else 0.0)
    direction_bonus = 0.0
    if macd.histogram_direction == "rising":
        direction_bonus = 10.0
    elif macd.histogram_direction == "falling":
        direction_bonus = -10.0
    return _clamp(sign + direction_bonus, -30, 30)


def _stoch_rsi_score(stoch: StochRSIResult) -> float:
    """k vs d + extreme bölgeler."""
    k = stoch.k
    d = stoch.d
    bullish_cross = k > d
    bearish_cross = k < d

    # Extreme bölgeler
    if k >= 80:
        return 10.0  # overbought
    if k <= 20:
        return -10.0  # oversold

    # Mid range — k vs d ile bullish/bearish
    if 50 <= k < 80 and bullish_cross:
        return 25.0
    if 20 < k < 50 and bearish_cross:
        return -25.0
    if 50 <= k < 80 and bearish_cross:
        return 5.0  # üst yarı ama momentum zayıflıyor
    if 20 < k < 50 and bullish_cross:
        return -5.0
    return 0.0


def _divergence_value(div: DivergenceResult) -> float:
    if div.type == "regular_bullish":
        return 20.0
    if div.type == "hidden_bullish":
        return 10.0
    if div.type == "regular_bearish":
        return -20.0
    if div.type == "hidden_bearish":
        return -10.0
    return 0.0


def _divergence_score(rsi_div: DivergenceResult, macd_div: DivergenceResult) -> float:
    """RSI ve MACD divergence'ından mutlak değeri en yüksek olanı al."""
    a = _divergence_value(rsi_div)
    b = _divergence_value(macd_div)
    return a if abs(a) >= abs(b) else b


def score_momentum(momentum: MomentumIndicators) -> float:
    raw = (
        _rsi_score(momentum.rsi)
        + _macd_score(momentum.macd)
        + _stoch_rsi_score(momentum.stoch_rsi)
        + _divergence_score(momentum.divergence_rsi, momentum.divergence_macd)
    )
    return _clamp(raw)
