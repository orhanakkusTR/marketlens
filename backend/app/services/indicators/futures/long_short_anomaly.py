"""Long/Short anomaly — top trader ratio + extreme tespiti.

Binance topLongShortAccountRatio: top hesapların oranı.
Extreme:
    ratio > 3.0  → aşırı kalabalık long → squeeze (short squeeze ters yönde olabilir)
    ratio < 0.33 → aşırı kalabalık short → contrarian long fırsatı
"""
from __future__ import annotations

from typing import Any

from app.schemas.indicators import LongShortAnomalyResult

EXTREME_HIGH = 3.0
EXTREME_LOW = 0.33


def compute_ls_anomaly(
    ls_data: list[dict[str, Any]],
    period: str = "1h",
) -> LongShortAnomalyResult:
    """`ls_data` zaman sırasına göre eski → yeni. En son kayıt aktif değerdir."""
    if not ls_data:
        raise ValueError("Long/short verisi boş")

    latest = ls_data[-1]
    ratio = float(latest["long_short_ratio"])
    long_account = float(latest["long_account"])
    short_account = float(latest["short_account"])

    extreme = ratio > EXTREME_HIGH or ratio < EXTREME_LOW

    return LongShortAnomalyResult(
        ratio=ratio,
        long_account=long_account,
        short_account=short_account,
        extreme=extreme,
        period=period,
    )
