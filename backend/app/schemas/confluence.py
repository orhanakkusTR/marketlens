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


# ─── Adım 11: Macro Modifier + Final + Alignment ───

SymbolType = Literal["btc", "alt", "commodity"]
AlignmentLabel = Literal["strong", "aligned", "weak", "conflicted"]


class ModifierBreakdown(_Strict):
    """Macro modifier'ın component'leri.

    None değerler ilgili sembol tipine uygulanmıyor demek:
    - btc: eth_btc_inverse + sp500 + dxy + vix (regime, total3 None)
    - alt: eth_btc_direct + sp500 + dxy + vix + regime (total3 None — history yok)
    - commodity: dxy + vix (kalan tümü None)
    """

    eth_btc: float | None = Field(
        None, description="BTC için ETH/BTC inverse, ALT için direct. GOLD için None."
    )
    sp500: float | None = Field(None, description="Risk-on göstergesi (kripto için)")
    dxy: float = Field(..., description="DXY 7d değişim (negatif korelasyon)")
    vix: float = Field(..., description="VIX seviyesi (level-based threshold)")
    regime: float | None = Field(
        None, description="Sadece ALT için: rejim-bazlı ek modifier"
    )
    total3: float | None = Field(
        None, description="ALT için future — şimdilik history yok"
    )


class FinalConfluenceResult(_Strict):
    """Local + macro modifier = Final."""

    symbol: str
    timeframe: str
    symbol_type: SymbolType
    local_score: float
    macro_modifier: float = Field(..., ge=-25, le=25)
    final_score: float = Field(..., ge=-100, le=100)
    label: ConfluenceLabel
    direction: TradeDirection
    components: ScoreBreakdown
    macro_breakdown: ModifierBreakdown
    weights_applied: dict[str, float]
    market_regime: str = Field(..., description="ALT_BULL / BTC_BULL / RISK_OFF / ALT_SEASON_EARLY / MIXED")
    computed_at: datetime


class TimeframeScore(_Strict):
    timeframe: str
    final_score: float
    label: ConfluenceLabel
    direction: TradeDirection


class AlignmentResult(_Strict):
    """6 TF için final score'ların ağırlıklı toplamı.

    `consistent_direction`: tüm TF'ler aynı yönlüyse o yön, değilse None.
    """

    symbol: str
    alignment_score: float = Field(..., ge=-100, le=100)
    label: AlignmentLabel
    consistent_direction: TradeDirection | None = None
    by_timeframe: list[TimeframeScore]
    weights: dict[str, float]
    computed_at: datetime
