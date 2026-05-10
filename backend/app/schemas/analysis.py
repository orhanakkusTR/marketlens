"""Analysis Orchestrator schemaları — Adım 17.

Tüm modülleri (indicators, confluence, alignment, setup_quality, macro,
correlations, risk_position) tek payload'da birleştirir.

Frontend Adım 18+ için tek endpoint, tek response.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.confluence import AlignmentResult, FinalConfluenceResult
from app.schemas.correlation import SymbolCorrelations
from app.schemas.indicators import IndicatorBundle
from app.schemas.macro import MacroSnapshot
from app.schemas.risk import PositionRiskResult
from app.schemas.setup_quality import SetupQualityResult


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FetchTimings(_Strict):
    """Debug için her phase'in ne kadar sürdüğü (ms)."""

    total_ms: float
    phase1_core_ms: float | None = Field(
        None, description="indicators + final_confluence (sequential)"
    )
    phase2_parallel_ms: float | None = Field(
        None,
        description=(
            "setup_quality + alignment + macro + correlations "
            "(asyncio.gather, max latency)"
        ),
    )
    phase3_risk_ms: float | None = Field(
        None, description="risk_position (scenario'dan türetilir)"
    )


class AnalysisModuleStatus(_Strict):
    """Bir alt modülün başarı durumu (graceful degradation)."""

    name: str = Field(
        ...,
        description=(
            "indicators / final_confluence / setup_quality / alignment / "
            "macro / correlations / risk_position"
        ),
    )
    ok: bool
    error: str | None = None
    duration_ms: float | None = None


class AnalysisFullResult(_Strict):
    """Tüm modüllerin composite çıktısı — Adım 18+ frontend için."""

    # ─── Kimlik ───
    symbol: str
    timeframe: str
    current_price: float
    computed_at: datetime
    cache_hit: bool = Field(..., description="Bu response cache'ten mi geldi")
    fetch_timings: FetchTimings

    # ─── Core (zorunlu — Phase 1 fail → 503) ───
    indicators: IndicatorBundle
    final_confluence: FinalConfluenceResult
    multi_tf_alignment: AlignmentResult

    # ─── Analysis (zorunlu — Phase 2 setup_quality fail → 503) ───
    setup_quality: SetupQualityResult

    # ─── Opsiyonel (graceful degradation) ───
    macro: MacroSnapshot | None = Field(
        None, description="Macro fetch fail → None + warning"
    )
    correlations: SymbolCorrelations | None = Field(
        None, description="GOLD veya tek-sembol failure → None"
    )
    risk_position: PositionRiskResult | None = Field(
        None, description="Neutral direction → None (normal); scenario yoksa None"
    )

    # ─── Status ───
    module_statuses: list[AnalysisModuleStatus] = Field(
        ..., description="Her modül için success/failure raporu (debug)"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="High-level Türkçe uyarılar (UI'da gösterilebilir)",
    )
