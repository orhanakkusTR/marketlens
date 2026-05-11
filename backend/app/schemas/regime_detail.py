"""Piyasa Rejimi detayı — Adım 20 polish.

Tek endpoint composite:
- regime + Türkçe label + reasoning
- macro özeti (UI'da kompakt göstermek için kritik alanlar)
- setup_distribution (27 sembolün grade + direction sayıları)
- warnings (frontend'in conditional gösterebileceği max 3 Türkçe mesaj)
- strategy (rejim + setup distribution kombinasyonu → dinamik Türkçe öneri)
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.macro import MarketRegime


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegimeMacroSummary(_Strict):
    btc_trend_7d_pct: float | None = Field(
        ..., description="BTC market cap 7g değişim yüzdesi"
    )
    eth_btc_change_pct: float | None = Field(
        ..., description="ETH/BTC ratio 7g değişim yüzdesi"
    )
    btc_dominance: float
    fear_greed_value: int
    fear_greed_label_tr: str = Field(
        ..., description="Aşırı Korku / Korku / Nötr / Açgözlü / Aşırı Açgözlü"
    )
    tradfi_signal: str = Field(
        ..., description="bullish / neutral / bearish — DXY+SP500+VIX kombinasyonu"
    )


class SetupGradeCounts(_Strict):
    A: int = 0
    B: int = 0
    C: int = 0
    D: int = 0
    NO_TRADE: int = 0
    none: int = Field(
        default=0, description="Grade hesaplanamamış (yetersiz veri vb.)"
    )


class SetupDirectionCounts(_Strict):
    long: int = 0
    short: int = 0
    neutral: int = 0
    none: int = Field(default=0, description="Yön hesaplanamamış")


class SetupDistribution(_Strict):
    grade_counts: SetupGradeCounts
    direction_counts: SetupDirectionCounts
    total_symbols: int


class RecommendationTr(_Strict):
    summary: str = Field(..., description="1-2 cümle ana tavsiye")
    bullets: list[str] = Field(
        default_factory=list, description="Aksiyon maddeleri (UI'da bullet list)"
    )


class DetailedAnalysisTr(_Strict):
    """İnsan dilinde Türkçe yorum — UI'da rejim detay açıkken gösterilir."""

    market_state: str = Field(
        ..., description="Piyasa durumu (1 paragraf, regime + macro)"
    )
    system_state: str = Field(
        ..., description="27 sembol analizi (setup distribution yorumu)"
    )
    risk_factors: list[str] = Field(
        default_factory=list, description="Risk faktörleri (her biri 1 satır)"
    )
    recommendation: RecommendationTr


class RegimeDetailResponse(_Strict):
    regime: MarketRegime
    regime_label_tr: str = Field(
        ..., description="UI başlığı (KARARSIZ, BTC YÜKSELİŞ, ...)"
    )
    reasoning_tr: str = Field(
        ..., description="Kısa Türkçe açıklama (backend label'dan)"
    )

    macro_summary: RegimeMacroSummary
    setup_distribution: SetupDistribution

    warnings_tr: list[str] = Field(
        default_factory=list, description="Max 3, conditional"
    )
    strategy_tr: str
    detailed_analysis_tr: DetailedAnalysisTr

    computed_at: datetime
