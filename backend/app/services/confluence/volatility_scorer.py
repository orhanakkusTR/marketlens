"""Volatility confluence skorlayıcısı — asimetrik [-50, +30].

Bileşenler:
    BB squeeze + bias    +30 (price > middle) / -30 (price < middle)
    ATR aşırı           -20 (>5%) / -10 (<0.3%) / 0 (normal)

Asimetrik yapı kasıtlı (spec): bearish exhaustion daha sert (panik anı).
Ağırlık 0.10 olduğu için toplam confluence'a etkisi sınırlı.
"""
from __future__ import annotations

from app.schemas.indicators import VolatilityIndicators


def _clamp(value: float, lo: float = -100, hi: float = 100) -> float:
    return max(lo, min(hi, value))


def _squeeze_score(volatility: VolatilityIndicators, price: float) -> float:
    """Squeeze + price middle'ın ne tarafında olduğuna göre yön."""
    if not volatility.bollinger.squeeze:
        return 0.0
    middle = volatility.bollinger.middle
    if price > middle:
        return 30.0
    if price < middle:
        return -30.0
    return 0.0


def _atr_score(volatility: VolatilityIndicators) -> float:
    """ATR % aşırılık penaltısı (yön-bağımsız risk uyarısı)."""
    pct = volatility.atr.value_pct
    if pct > 5.0:
        return -20.0  # parabolik / exhaustion
    if pct < 0.3:
        return -10.0  # ölü piyasa
    return 0.0


def score_volatility(volatility: VolatilityIndicators, price: float) -> float:
    raw = _squeeze_score(volatility, price) + _atr_score(volatility)
    return _clamp(raw, lo=-50, hi=30)
