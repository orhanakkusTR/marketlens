"""Futures confluence skorlayıcısı — long perspektifi.

Toplam ±100:
    Funding aşırı           ±30
    OI + fiyat 24h uyumu    ±30
    L/S ratio aşırı         ±15

Long perspektifi: pozitif skor long fırsatı, negatif short fırsatı.
"""
from __future__ import annotations

from typing import Literal

from app.schemas.indicators import FuturesIndicators

Price24hDirection = Literal["up", "down", "flat"]

FUNDING_EXTREME = 0.0008  # %0.08
LS_EXTREME_HIGH = 3.0
LS_EXTREME_LOW = 0.33


def _clamp(value: float, lo: float = -100, hi: float = 100) -> float:
    return max(lo, min(hi, value))


def _funding_score(futures: FuturesIndicators) -> float:
    """Long perspektifi:
    - rate çok pozitif → longlar kalabalık → squeeze riski → -30
    - rate çok negatif → shortlar kalabalık → short squeeze fırsatı → +30
    """
    rate = futures.funding.current_rate
    if rate > FUNDING_EXTREME:
        return -30.0
    if rate < -FUNDING_EXTREME:
        return 30.0
    return 0.0


def _oi_price_alignment_score(
    futures: FuturesIndicators, price_dir_24h: Price24hDirection
) -> float:
    """OI 24h değişim + price 24h değişim uyumu."""
    oi_change = futures.open_interest.change_24h_pct

    # Eşik: ±0.5% (gürültü filtresi)
    oi_up = oi_change > 0.5
    oi_down = oi_change < -0.5

    if oi_up and price_dir_24h == "up":
        return 30.0  # gerçek alım (yeni longlar)
    if oi_up and price_dir_24h == "down":
        return -30.0  # gerçek satış (yeni shortlar)
    if oi_down and price_dir_24h == "up":
        return 10.0  # short covering, zayıf bullish
    if oi_down and price_dir_24h == "down":
        return -10.0  # long unwind, zayıf bearish
    return 0.0


def _ls_score(futures: FuturesIndicators) -> float:
    """Long perspektifi:
    - ratio > 3.0 → kalabalık long → squeeze riski → -15
    - ratio < 0.33 → kalabalık short → short squeeze fırsatı → +15
    """
    r = futures.long_short.ratio
    if r > LS_EXTREME_HIGH:
        return -15.0
    if r < LS_EXTREME_LOW:
        return 15.0
    return 0.0


def score_futures(
    futures: FuturesIndicators, price_dir_24h: Price24hDirection
) -> float:
    raw = (
        _funding_score(futures)
        + _oi_price_alignment_score(futures, price_dir_24h)
        + _ls_score(futures)
    )
    return _clamp(raw)
