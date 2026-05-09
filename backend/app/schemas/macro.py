"""Macro module schemaları (Adım 10).

Snapshot tüm macro metrikleri tek call'da döner:
- Crypto caps (TOTAL/TOTAL2/TOTAL3, BTC.D, ETH.D — current only)
- BTC market cap (trend dahil — CoinGecko historical)
- ETH/BTC ratio (trend dahil — Binance klines)
- TradFi (DXY/SP500/NASDAQ/VIX/US10Y/GOLD — yfinance trend)
- Fear & Greed (current + 7d değişim)
- Market regime (5 sınıf, türkçe label, hangi trigger'lar aktif)
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


TrendDirection = Literal["up", "down", "flat"]


class MetricTrend(_Strict):
    """Tek metrik + 24h/7d/30d trend.

    Yetersiz history varsa ilgili change_*_pct ve direction_* None olabilir.
    """

    current: float
    change_24h_pct: float | None = None
    change_7d_pct: float | None = None
    change_30d_pct: float | None = None
    direction_24h: TrendDirection
    direction_7d: TrendDirection
    direction_30d: TrendDirection


class CryptoCapsSnapshot(_Strict):
    """CoinGecko /global — current only (free tier'da global history yok)."""

    total: float
    total2: float
    total3: float
    btc_dominance: float
    eth_dominance: float


class FearGreedSnapshot(_Strict):
    value: int
    classification: str
    timestamp: str
    value_7d_ago: int | None = None
    change_7d: int | None = Field(None, description="Puan farkı (current - 7d_ago)")


MarketRegime = Literal[
    "ALT_BULL",
    "BTC_BULL",
    "RISK_OFF",
    "ALT_SEASON_EARLY",
    "MIXED",
]


class RegimeResult(_Strict):
    regime: MarketRegime
    label: str = Field(..., description="Türkçe açıklama (UI için)")
    triggers: dict[str, bool] = Field(
        ..., description="Hangi koşullar aktif — tooltip 'neden bu rejim?'"
    )


class MacroSnapshot(_Strict):
    crypto_caps: CryptoCapsSnapshot
    btc_market_cap: MetricTrend
    eth_btc_ratio: MetricTrend
    dxy: MetricTrend
    sp500: MetricTrend
    nasdaq: MetricTrend
    vix: MetricTrend
    us10y: MetricTrend
    gold: MetricTrend
    fear_greed: FearGreedSnapshot
    market_regime: RegimeResult
    computed_at: datetime
