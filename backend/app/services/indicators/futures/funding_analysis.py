"""Funding analysis — current + 24h_avg + 7d_avg + extreme flag.

Kripto futures funding ödemesi 8 saatte bir (gün=3 ödeme).
- avg_24h = son 3 ödeme ortalaması
- avg_7d = son 21 ödeme ortalaması
- extreme: |current| > 0.0008 (%0.08) — squeeze riski threshold'u
"""
from __future__ import annotations

from typing import Any

from app.schemas.indicators import FundingAnalysisResult

EXTREME_THRESHOLD = 0.0008  # %0.08


def compute_funding_analysis(
    history: list[dict[str, Any]],
    current_rate: float,
    next_funding_time: int,
) -> FundingAnalysisResult:
    """`history` zaman sırasına göre eski → yeni; her item: funding_rate, funding_time."""
    if not history:
        # Tarih yoksa current ile doldur (avg'ler current'a eşit)
        return FundingAnalysisResult(
            current_rate=current_rate,
            avg_24h=current_rate,
            avg_7d=current_rate,
            extreme=abs(current_rate) > EXTREME_THRESHOLD,
            next_funding_time=next_funding_time,
        )

    rates = [float(h["funding_rate"]) for h in history]
    last_3 = rates[-3:]
    last_21 = rates[-21:]
    avg_24h = sum(last_3) / len(last_3)
    avg_7d = sum(last_21) / len(last_21)

    return FundingAnalysisResult(
        current_rate=current_rate,
        avg_24h=avg_24h,
        avg_7d=avg_7d,
        extreme=abs(current_rate) > EXTREME_THRESHOLD,
        next_funding_time=next_funding_time,
    )
