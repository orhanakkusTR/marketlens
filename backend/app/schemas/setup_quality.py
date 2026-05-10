"""Setup Quality Engine schemaları (Adım 13).

4 modülün composite çıktısı:
1. Base score + grade (faktör bazlı)
2. Confidence (trade journal lookup)
3. Counter-trend warnings (sistem kendi sinyalini sorgular)
4. Trade quality filter (5-faktör vasat filtreleme)
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.confluence import TradeDirection
from app.schemas.no_trade_zone import NoTradeZoneResult


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


SetupGrade = Literal["A", "B", "C", "D", "NO_TRADE"]
ConfidenceLevel = Literal["VERY_LOW", "LOW", "MEDIUM", "HIGH", "VERY_HIGH"]
CounterTrendSeverity = Literal["low", "medium", "high"]
TradeQualityVerdict = Literal["EXCELLENT", "GOOD", "WEAK", "AVOID"]


# ─── Base score factors ───


class SetupFactor(_Strict):
    name: str
    passed: bool
    points: int
    note: str | None = None


# ─── Confidence ───


class ConfidenceResult(_Strict):
    level: ConfidenceLevel
    label: str = Field(..., description="Türkçe açıklama (UI için)")
    trade_count: int
    actual_win_rate: float | None = Field(None, ge=0, le=1)
    advice: str
    setup_signature: str = Field(
        ..., description="Bu setup tipinin imzası (kategori:rejim:grade:yön)"
    )


# ─── Counter-trend ───


class CounterTrendWarning(_Strict):
    type: str
    severity: CounterTrendSeverity
    message: str
    advice: str | None = None


# ─── Trade Quality Filter ───


class TradeQualityFactor(_Strict):
    name: str = Field(..., description="Türkçe label (örn. 'ATR makul')")
    passed: bool
    value: str | None = Field(None, description="Human readable değer (örn. 'ATR %1.5')")
    note: str


class TradeQualityResult(_Strict):
    score: int = Field(..., ge=0, le=5)
    verdict: TradeQualityVerdict
    quality_modifier: int = Field(..., description="-2..+1 grade adjustment")
    factors: list[TradeQualityFactor]


# ─── Composite result ───


class SetupQualityResult(_Strict):
    symbol: str
    timeframe: str
    direction: TradeDirection
    final_score: float

    raw_score: int
    base_grade: SetupGrade
    grade: SetupGrade
    factors: list[SetupFactor]

    grade_modifiers: dict[str, int] = Field(
        ..., description="Uygulanan grade değişimleri (örn. {'macro': +1, 'counter_trend': -1})"
    )

    confidence: ConfidenceResult
    counter_trend_warnings: list[CounterTrendWarning]
    trade_quality: TradeQualityResult
    no_trade_zones: NoTradeZoneResult

    computed_at: datetime
