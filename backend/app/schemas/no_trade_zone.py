"""No-Trade Zone Detector schemaları (Adım 14).

Sistem belirli durumlarda işlem **önerilmemesini** söyler. 9 zone tipi:

Active triggers (MVP):
- weekend                  blocking   — Cuma 22:00 UTC → Pzt 02:00 UTC
- low_liquidity_session    warning    — Asya seansı 00:00-08:00 UTC
- high_volatility          warning    — BTC 24h |%| ≥ 8 veya ATR z-score ≥ 2
- range_market             warning    — BB squeeze + flat OBV (sembol özel)
- tilt                     blocking   — son 24h ≥3 ardışık SL (DB query)

Future-ready (MVP'de info severity, gerçek implementasyon sonra):
- daily_risk_cap           info       — Adım 15 (risk_tracker)
- major_event_proximity    info       — economic calendar future
- news_recent              info       — CryptoPanic future
- correlation_risk         info       — open positions future

Severity desc: blocking → warning → info.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


NoTradeZoneType = Literal[
    "weekend",
    "low_liquidity_session",
    "high_volatility",
    "range_market",
    "tilt",
    "daily_risk_cap",
    "major_event_proximity",
    "news_recent",
    "correlation_risk",
]

NoTradeZoneSeverity = Literal["blocking", "warning", "info"]


class NoTradeZone(_Strict):
    type: NoTradeZoneType
    severity: NoTradeZoneSeverity
    message: str = Field(..., description="Türkçe; UTC + TR saati paralel")
    advice: str | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class SeveritySummary(_Strict):
    blocking: int = 0
    warning: int = 0
    info: int = 0


class NoTradeZoneResult(_Strict):
    symbol: str
    timeframe: str
    is_blocking: bool = Field(..., description="≥1 blocking zone varsa True")
    has_warning: bool = Field(..., description="≥1 warning (veya blocking) varsa True")
    severity_summary: SeveritySummary
    zones: list[NoTradeZone] = Field(
        ..., description="Severity desc sıralı (blocking → warning → info)"
    )
    computed_at: datetime
    now_utc: datetime = Field(..., description="Hesaplama anındaki UTC zamanı")
