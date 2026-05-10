"""Korelasyon Engine schemaları (Adım 12).

Pearson coefficient kategorisi abs(r) tabanlı, sign ayrı alan.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


CorrelationCategory = Literal["strong", "moderate", "weak", "decoupled"]
CorrelationSign = Literal["positive", "negative"]


class CorrelationPair(_Strict):
    """A sembolünün B sembolüyle korelasyonu."""

    symbol: str
    coefficient: float = Field(..., ge=-1.0, le=1.0)
    category: CorrelationCategory
    sign: CorrelationSign


class SymbolCorrelations(_Strict):
    """Tek sembolün diğer tüm sembollerle + tradfi referanslarıyla korelasyonu.

    `all`: abs(coefficient) desc sıralı tüm korelasyonlar.
    `vs_*`: cross-asset referanslar (sembol kendisi BTC/ETH ise None).
    `by_sector_avg`: sektör ortalaması (kendi sektörü hariç değil — kendisini
        out etmek için aşağıda not açıklanıyor: kendisi her zaman matrix dışında
        bırakılır).
    """

    symbol: str
    period_days: int
    timeframe: str

    all: list[CorrelationPair]

    strong: list[CorrelationPair]
    moderate: list[CorrelationPair]
    weak: list[CorrelationPair]
    decoupled: list[CorrelationPair]

    by_sector_avg: dict[str, float] = Field(
        ...,
        description=(
            "Sektör başına ortalama korelasyon. Sembolün kendi sektör avg'inde "
            "kendi katkısı hariç tutulur."
        ),
    )

    vs_btc: float | None = None
    vs_eth: float | None = None
    vs_dxy: float | None = None
    vs_sp500: float | None = None

    computed_at: datetime


class CorrelationMatrix(_Strict):
    """27 sembol için full matrix (kare, simetrik).

    `matrix[A][B]` → A ile B arasındaki Pearson r.
    Diagonal = 1.0. NaN değerler None döner.
    """

    symbols: list[str]
    matrix: dict[str, dict[str, float | None]]
    period_days: int
    timeframe: str
    computed_at: datetime
