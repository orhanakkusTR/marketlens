"""Risk Management schemaları — Adım 15.

Position sizing + R/R + Liquidation + Funding + Daily tracker.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.confluence import TradeDirection


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


RiskWarningCode = Literal[
    "stop_too_tight",
    "leverage_capped",
    "rr_below_1",
    "volatility_reduced",
    "stop_wrong_side",
    "no_targets",
]

RiskWarningSeverity = Literal["info", "warning", "blocking"]


class RiskWarning(_Strict):
    code: RiskWarningCode
    severity: RiskWarningSeverity
    message: str


class VolatilityAdjustment(_Strict):
    factor: float = Field(..., description="Çarpan: 0.5 / 0.7 / 1.0")
    reason: str = Field(..., description="Türkçe açıklama")
    btc_24h_change_pct: float | None = None
    atr_zscore: float | None = None


class LiquidationPrices(_Strict):
    at_5x: float
    at_10x: float
    actual: float = Field(..., description="Seçilen leverage için tahmini liq fiyatı")


class FundingCosts(_Strict):
    funding_rate: float = Field(..., description="Anlık 8h funding (signed)")
    h24: float = Field(..., description="24h tahmini funding (signed; pozitif=gider)")
    h72: float
    w1: float = Field(..., description="1 hafta tahmini funding (signed)")


class RRBreakdown(_Strict):
    tp1: float | None = None
    tp2: float | None = None
    tp3: float | None = None
    weighted: float | None = Field(
        None,
        description="0.40*TP1 + 0.35*TP2 + 0.25*TP3 (TP eksikse mevcut TP'ler normalize edilir)",
    )


class PositionRiskInput(_Strict):
    symbol: str = Field(..., min_length=3, max_length=20)
    direction: TradeDirection
    balance: float = Field(..., gt=0)
    base_risk_pct: float = Field(..., gt=0, le=10)
    entry: float = Field(..., gt=0)
    stop: float = Field(..., gt=0)
    targets: list[float] = Field(default_factory=list, max_length=3)
    max_leverage: int = Field(default=10, ge=1, le=125)
    funding_rate: float | None = Field(
        None, description="Eksikse 0 alınır; signed (long pos için + = gider)"
    )
    btc_24h_change_pct: float | None = None
    atr_zscore: float | None = None


class PositionRiskResult(_Strict):
    symbol: str
    direction: TradeDirection
    entry: float
    stop: float
    targets: list[float]
    balance: float

    base_risk_pct: float
    adjusted_risk_pct: float
    volatility_adjustment: VolatilityAdjustment

    stop_distance_pct: float = Field(..., description="|entry - stop| / entry * 100")
    risk_amount_usd: float

    position_size_usd: float
    leverage_required: int
    leverage_actual: int
    margin_used: float

    liquidation: LiquidationPrices
    funding_costs: FundingCosts
    rr: RRBreakdown

    warnings: list[RiskWarning]
    computed_at: datetime


# ─── Daily Risk Tracker ───


class DailyRiskStatus(_Strict):
    user_id: str | None = Field(None, description="None: anonymous (global)")
    now_utc: datetime

    current_risk_per_trade_pct: float = Field(
        ..., description="Smart reduction sonrası risk yüzdesi"
    )
    smart_reduction_active: bool
    consecutive_losses: int = Field(..., ge=0)

    trades_today: int = Field(..., ge=0)
    max_trades_per_day: int
    trades_remaining: int = Field(..., ge=0)

    daily_risk_used_pct: float = Field(
        ..., description="MVP: 0.0 placeholder (Adım 17'de gerçek hesap)"
    )
    daily_risk_max_pct: float
    daily_risk_remaining_pct: float

    paused_until: datetime | None = Field(None, description="None: pause aktif değil")
    can_open_new_trade: bool
    block_reason: str | None = Field(None, description="Türkçe; can_open=False ise dolu")


class RiskPauseRequest(_Strict):
    hours: int = Field(..., ge=1, le=48)


class RiskPauseResponse(_Strict):
    paused_until: datetime
    hours: int
    message: str
