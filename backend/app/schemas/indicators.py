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


# ─── Volatility ───


class ATRResult(_Strict):
    value_usdt: float = Field(..., description="ATR mutlak değeri (fiyat birimi)")
    value_pct: float = Field(..., description="ATR / price * 100")
    period: int


class BollingerResult(_Strict):
    upper: float
    middle: float
    lower: float
    width_pct: float = Field(..., description="(upper - lower) / middle * 100")
    squeeze: bool = Field(..., description="Width son 100 mumun en alt %25'inde mi")


class VolatilityIndicators(_Strict):
    atr: ATRResult
    bollinger: BollingerResult


# ─── Volume ───


VolumeSlope = Literal["rising", "falling", "flat"]


class OBVResult(_Strict):
    current: float
    slope: VolumeSlope = Field(..., description="Son 20 mumun trend yönü")


class VWAPResult(_Strict):
    """4H+ TF için None döner (intraday-only)."""

    value: float
    distance_pct: float = Field(..., description="(price - vwap) / vwap * 100")
    session_start_ms: int


class VolumeProfileResult(_Strict):
    poc: float = Field(..., description="Point of Control — en çok hacim olan fiyat")
    vah: float = Field(..., description="Value Area High — %70 hacim üst sınırı")
    val: float = Field(..., description="Value Area Low — %70 hacim alt sınırı")
    total_volume: float
    bin_count: int
    window_bars: int


class VolumeIndicators(_Strict):
    obv: OBVResult
    vwap: VWAPResult | None = Field(
        None, description="4H ve üstü TF için None — intraday only"
    )
    volume_profile: VolumeProfileResult


# ─── Fibonacci ───


FibKind = Literal["retracement", "extension"]
FibDirection = Literal["bullish", "bearish"]


class FibLevel(_Strict):
    ratio: float = Field(..., description="0.382, 0.5, 0.618, 1.618 vb.")
    price: float
    kind: FibKind


class FibSwing(_Strict):
    price: float
    index: int
    timestamp_ms: int


class FibonacciResult(_Strict):
    direction: FibDirection
    swing_high: FibSwing
    swing_low: FibSwing
    levels: list[FibLevel]


# ─── Auto S/R Levels ───


LevelSource = Literal[
    "pivot_high",
    "pivot_low",
    "fib_0.382",
    "fib_0.5",
    "fib_0.618",
    "fib_0.786",
    "fib_ext_1.272",
    "fib_ext_1.618",
    "fib_ext_2.618",
    "vp_poc",
    "vp_vah",
    "vp_val",
    "round_major",
    "round_minor",
]
LevelKind = Literal["support", "resistance"]


class LevelEntry(_Strict):
    price: float
    kind: LevelKind
    sources: list[LevelSource]
    confluence_count: int
    strength_score: float


class LevelsResult(_Strict):
    current_price: float
    supports: list[LevelEntry]
    resistances: list[LevelEntry]


# ─── Bundle ───


class IndicatorBundle(_Strict):
    symbol: str
    timeframe: str
    computed_at: datetime
    kline_count: int
    trend: TrendIndicators
    momentum: MomentumIndicators
    volatility: VolatilityIndicators
    volume: VolumeIndicators
    fibonacci: FibonacciResult | None = Field(
        None, description="Major swing tespit edilemezse None"
    )
    levels: LevelsResult
