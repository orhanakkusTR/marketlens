"""Indicator engine Pydantic v2 modelleri.

Trend + Momentum sonuçları. Volatility/Volume/Fibonacci/SMC bir sonraki
adımlarda eklenir.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ─── Ortak tipler ───

MAType = Literal["EMA", "SMA"]
Alignment = Literal["bullish_stack", "bearish_stack", "mixed"]
CloudState = Literal["above", "below", "inside"]
CrossState = Literal["bullish", "bearish", "none"]
SwingKind = Literal["HH", "HL", "LH", "LL"]
StructureState = Literal["uptrend", "downtrend", "ranging"]
RSIState = Literal["overbought", "oversold", "neutral"]
DivergenceType = Literal[
    "regular_bullish",
    "regular_bearish",
    "hidden_bullish",
    "hidden_bearish",
    "none",
]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ─── Trend ───


class MovingAverage(_Strict):
    period: int
    type: MAType
    value: float
    distance_pct: float = Field(
        ...,
        description="(price - ma) / ma * 100 — pozitif: fiyat MA üstünde",
    )


class MovingAveragesResult(_Strict):
    timeframe: str
    price: float
    moving_averages: list[MovingAverage]
    alignment: Alignment


class IchimokuResult(_Strict):
    tenkan: float
    kijun: float
    senkou_a: float
    senkou_b: float
    chikou: float
    cloud_state: CloudState
    tk_cross: CrossState


class SwingPoint(_Strict):
    index: int
    timestamp_ms: int
    price: float
    kind: SwingKind


class MarketStructureResult(_Strict):
    structure: StructureState
    recent_swings: list[SwingPoint]
    last_swing_high: SwingPoint | None
    last_swing_low: SwingPoint | None


class TrendIndicators(_Strict):
    moving_averages: MovingAveragesResult
    ichimoku: IchimokuResult
    market_structure: MarketStructureResult


# ─── Momentum ───


class RSIResult(_Strict):
    current: float
    history: list[float] = Field(..., description="Son N RSI değeri (eski → yeni)")
    state: RSIState


class MACDResult(_Strict):
    macd: float
    signal: float
    histogram: float
    histogram_direction: Literal["rising", "falling", "flat"]
    cross: CrossState = Field(..., description="Son 3 mumda crossover var mı")


class StochRSIResult(_Strict):
    k: float
    d: float
    state: RSIState
    cross: CrossState


class IndicatorSwing(_Strict):
    index: int
    value: float


class DivergenceResult(_Strict):
    detected: bool
    type: DivergenceType
    price_swings: list[SwingPoint] = Field(default_factory=list)
    indicator_swings: list[IndicatorSwing] = Field(default_factory=list)


class MomentumIndicators(_Strict):
    rsi: RSIResult
    macd: MACDResult
    stoch_rsi: StochRSIResult
    divergence_rsi: DivergenceResult
    divergence_macd: DivergenceResult


# ─── Bundle ───


class IndicatorBundle(_Strict):
    symbol: str
    timeframe: str
    computed_at: datetime
    kline_count: int
    trend: TrendIndicators
    momentum: MomentumIndicators
