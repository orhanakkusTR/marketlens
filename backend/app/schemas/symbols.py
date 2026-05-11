"""Sembol toplu durum schemaları — Adım 19.

Sidebar için lightweight grade + direction snapshot (27 sembol).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


GradeLetter = Literal["A", "B", "C", "D", "NO_TRADE"]
Direction = Literal["long", "short", "neutral"]


class GradeSummary(_Strict):
    symbol: str
    grade: GradeLetter | None = Field(None, description="Hesaplanamadıysa null")
    direction: Direction | None = None
    final_score: float | None = None
    is_blocking: bool = Field(
        default=False, description="no_trade_zones.is_blocking"
    )
    error: str | None = Field(
        None, description="Yetersiz veri / hesap hatası varsa kısa Türkçe açıklama"
    )


class GradesResponse(_Strict):
    computed_at: datetime
    timeframe: str
    items: list[GradeSummary]
