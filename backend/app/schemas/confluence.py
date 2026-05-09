"""Confluence schema'ları — Lokal skor (Adım 9).

Macro modifier (Adım 11) ayrı schema'da olacak. Bu dosya sadece local layer.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# 5 label — gücü ayırt eder (+45 vs +75 farklı)
ConfluenceLabel = Literal[
    "strong_bullish",
    "bullish",
    "neutral",
    "bearish",
    "strong_bearish",
]

# 3 direction — pozisyon yönü önerisi
TradeDirection = Literal["long", "short", "neutral"]


class ScoreBreakdown(_Strict):
    """Her modülün ham skoru (clamp [-100, +100])."""

    trend: float
    momentum: float
    volume: float
    volatility: float
    futures: float | None = Field(
        None, description="Sembol futures desteklemiyorsa (GOLD) None"
    )


class LocalConfluenceResult(_Strict):
    """Tek TF için lokal confluence skoru.

    `final_score`: weighted sum, [-100, +100].
    `label`: skor gücü (strong_bullish/bullish/neutral/bearish/strong_bearish).
    `direction`: pozisyon yönü önerisi (long/short/neutral) — label'dan ayrı.
    `weights_applied`: GOLD'da renormalize edilmiş ağırlıklar gösterilir.
    """

    symbol: str
    timeframe: str
    final_score: float = Field(..., ge=-100, le=100)
    label: ConfluenceLabel
    direction: TradeDirection
    components: ScoreBreakdown
    weights_applied: dict[str, float]
    computed_at: datetime
