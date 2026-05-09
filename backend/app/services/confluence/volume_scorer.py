"""Volume confluence skorlayıcısı.

Toplam ±100:
    OBV slope            ±25
    Hacim/ortalama       ±25  (son bar / 20-bar mean ile yön kombinasyonu)
    POC pozisyonu        ±20
    VWAP pozisyonu       ±30  (4H+ TF'lerde 0)

`volume_ratio` ve `price_direction` aux'lerini orchestrator hesaplar
(scorer pure function — df'e bakmaz).
"""
from __future__ import annotations

from typing import Literal

from app.schemas.indicators import VolumeIndicators

PriceDirection = Literal["up", "down", "flat"]


def _clamp(value: float, lo: float = -100, hi: float = 100) -> float:
    return max(lo, min(hi, value))


def _obv_score(volume: VolumeIndicators) -> float:
    s = volume.obv.slope
    if s == "rising":
        return 25.0
    if s == "falling":
        return -25.0
    return 0.0


def _volume_ratio_score(volume_ratio: float, price_direction: PriceDirection) -> float:
    """Yüksek hacim trend yönünde teyit; düşük hacim zayıf sinyal."""
    if volume_ratio >= 1.5:
        # Trend yönünde amplify
        if price_direction == "up":
            return 25.0
        if price_direction == "down":
            return -25.0
        return 0.0
    if volume_ratio < 0.7:
        # Zayıf sinyal — yöne ters küçük penalty
        if price_direction == "up":
            return -10.0  # yükseliş ama hacim yok
        if price_direction == "down":
            return 10.0
        return 0.0
    return 0.0


def _poc_position_score(volume: VolumeIndicators, price: float) -> float:
    """POC/VAH/VAL'a göre fiyatın konumu."""
    vp = volume.volume_profile
    if price > vp.vah:
        return 20.0
    if price < vp.val:
        return -20.0
    # Value Area içinde
    if price > vp.poc:
        return 5.0
    if price < vp.poc:
        return -5.0
    return 0.0


def _vwap_score(volume: VolumeIndicators) -> float:
    """4H+ TF'lerde VWAP None → 0."""
    if volume.vwap is None:
        return 0.0
    d = volume.vwap.distance_pct
    if d > 1.0:
        return 30.0
    if d > 0:
        return 15.0
    if d > -1.0:
        return -15.0
    return -30.0


def score_volume(
    volume: VolumeIndicators,
    price: float,
    volume_ratio: float,
    price_direction: PriceDirection,
) -> float:
    raw = (
        _obv_score(volume)
        + _volume_ratio_score(volume_ratio, price_direction)
        + _poc_position_score(volume, price)
        + _vwap_score(volume)
    )
    return _clamp(raw)
