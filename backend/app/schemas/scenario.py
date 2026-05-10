"""Scenario Generator schemaları — Adım 16.

Sistem auto entry/stop/TP üretir. Direction-aware, levels-based.

Action Summary (kullanıcı dostu metin özet) Adım 21'de Aksiyon Özeti UI
ile birlikte yazılır — bu modülün çıktısından beslenir.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.confluence import TradeDirection
from app.schemas.risk import PositionRiskResult


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


ScenarioDirection = Literal["long", "short"]


class EntryBand(_Strict):
    low: float = Field(..., description="current_price - 0.3 * ATR")
    mid: float = Field(..., description="current_price")
    high: float = Field(..., description="current_price + 0.3 * ATR")
    width_atr: float = Field(..., description="Toplam genişlik ATR cinsinden (0.6)")


class StopLevel(_Strict):
    price: float
    source: str = Field(
        ...,
        description="Stop kaynağı: 'level (kaynaklar)' veya 'ATR×1.5 fallback'",
    )
    distance_atr: float = Field(..., description="|entry_mid - price| / atr")
    distance_pct: float = Field(..., description="|entry_mid - price| / entry_mid * 100")
    reasoning: str


class TPLevel(_Strict):
    price: float
    source: str = Field(
        ...,
        description="TP kaynağı: 'level (kaynaklar)' veya 'ATR×N fallback'",
    )
    distance_atr: float
    distance_pct: float
    rr: float = Field(..., description="Direction-aware reward/risk")
    reasoning: str


class ScenarioResult(_Strict):
    symbol: str
    timeframe: str
    direction: ScenarioDirection = Field(
        ..., description="long veya short (neutral → senaryo None döner)"
    )
    entry: EntryBand
    stop: StopLevel
    targets: list[TPLevel] = Field(..., max_length=3, min_length=1)
    rr_weighted: float | None = Field(
        None,
        description="0.40*tp1 + 0.35*tp2 + 0.25*tp3 (mevcut TP'ler renormalize)",
    )
    final_confluence: float = Field(..., description="Context — direction nedeni")
    reasoning: str = Field(..., description="Türkçe, kısa açıklama")
    computed_at: datetime


class ScenarioWithPosition(_Strict):
    scenario: ScenarioResult
    position: PositionRiskResult = Field(
        ..., description="entry.mid + stop + TP'ler ile hesaplanmış pozisyon"
    )
