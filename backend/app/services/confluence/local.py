"""Local confluence orchestrator — bundle + aux'lerden final skor üretir.

Ağırlıklar (CLAUDE.md / spec):
    trend       0.40
    momentum    0.20
    volume      0.15
    volatility  0.10
    futures     0.15

Futures None ise (GOLD): kalan ağırlıklar normalize edilir.

Label thresholds (kullanıcı isteği — 5 seviye):
    > +60        → strong_bullish
    +30..+60     → bullish
    -30..+30     → neutral
    -60..-30     → bearish
    < -60        → strong_bearish

Direction (label'dan ayrı):
    > +20        → long
    < -20        → short
    -20..+20     → neutral
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

import pandas as pd

from app.data.binance_spot import TF_TO_INTERVAL
from app.schemas.confluence import (
    ConfluenceLabel,
    LocalConfluenceResult,
    ScoreBreakdown,
    TradeDirection,
)
from app.schemas.indicators import (
    FuturesIndicators,
    MomentumIndicators,
    TrendIndicators,
    VolatilityIndicators,
    VolumeIndicators,
)
from app.services.confluence.futures_scorer import score_futures
from app.services.confluence.momentum_scorer import score_momentum
from app.services.confluence.trend_scorer import score_trend
from app.services.confluence.volatility_scorer import score_volatility
from app.services.confluence.volume_scorer import score_volume

DEFAULT_WEIGHTS: dict[str, float] = {
    "trend": 0.40,
    "momentum": 0.20,
    "volume": 0.15,
    "volatility": 0.10,
    "futures": 0.15,
}

# Bars per 24h per timeframe — futures OI/price alignment için
BARS_PER_24H: dict[str, int] = {
    "15m": 96,
    "1H": 24,
    "4H": 6,
    "1D": 1,
    "1W": 1,
    "1M": 1,
}

# Volume ratio için 20-bar mean — TF-bağımsız sabit
VOLUME_MEAN_BARS = 20

# Price direction tespit eşiği (yüzde)
DIRECTION_THRESHOLD_PCT = 0.5


def _label(score: float) -> ConfluenceLabel:
    if score > 60:
        return "strong_bullish"
    if score > 30:
        return "bullish"
    if score < -60:
        return "strong_bearish"
    if score < -30:
        return "bearish"
    return "neutral"


def _direction(score: float) -> TradeDirection:
    if score > 20:
        return "long"
    if score < -20:
        return "short"
    return "neutral"


def _normalize_weights_without_futures() -> dict[str, float]:
    """Futures yokken kalan 4 ağırlığı 1.0 toplamına normalize et."""
    base = {k: v for k, v in DEFAULT_WEIGHTS.items() if k != "futures"}
    total = sum(base.values())
    return {k: v / total for k, v in base.items()}


def compute_volume_ratio(df: pd.DataFrame, bars: int = VOLUME_MEAN_BARS) -> float:
    """Son bar hacmi / son `bars` mean. >=2 bar olmalı."""
    if len(df) < 2:
        return 1.0
    n = min(bars, len(df) - 1)
    if n < 1:
        return 1.0
    recent_mean = float(df["volume"].iloc[-(n + 1) : -1].mean())
    last = float(df["volume"].iloc[-1])
    if recent_mean <= 0:
        return 1.0
    return last / recent_mean


def compute_price_direction(
    df: pd.DataFrame, bars: int, threshold_pct: float = DIRECTION_THRESHOLD_PCT
) -> Literal["up", "down", "flat"]:
    """Son `bars` bar öncesine göre fiyat yönü."""
    if len(df) < bars + 1:
        return "flat"
    old = float(df["close"].iloc[-bars - 1])
    new = float(df["close"].iloc[-1])
    if old <= 0:
        return "flat"
    pct = ((new - old) / old) * 100
    if pct > threshold_pct:
        return "up"
    if pct < -threshold_pct:
        return "down"
    return "flat"


def compute_local_confluence(
    *,
    symbol: str,
    timeframe: str,
    df: pd.DataFrame,
    trend: TrendIndicators,
    momentum: MomentumIndicators,
    volume: VolumeIndicators,
    volatility: VolatilityIndicators,
    futures: FuturesIndicators | None,
    price: float,
) -> LocalConfluenceResult:
    """Tüm scorer'ları çalıştır + ağırlıklı toplam üret."""
    if timeframe not in TF_TO_INTERVAL:
        raise ValueError(f"Bilinmeyen timeframe: {timeframe}")

    # Aux metrikler
    volume_ratio = compute_volume_ratio(df)
    price_dir_short = compute_price_direction(df, bars=VOLUME_MEAN_BARS)
    bars_24h = BARS_PER_24H.get(timeframe, 6)
    price_dir_24h = compute_price_direction(df, bars=bars_24h)

    # Skorlar
    s_trend = score_trend(trend, timeframe)
    s_momentum = score_momentum(momentum)
    s_volume = score_volume(volume, price, volume_ratio, price_dir_short)
    s_volatility = score_volatility(volatility, price)
    s_futures: float | None = (
        score_futures(futures, price_dir_24h) if futures is not None else None
    )

    # Ağırlıklı toplam
    if futures is None:
        weights = _normalize_weights_without_futures()
        final = (
            s_trend * weights["trend"]
            + s_momentum * weights["momentum"]
            + s_volume * weights["volume"]
            + s_volatility * weights["volatility"]
        )
    else:
        weights = dict(DEFAULT_WEIGHTS)
        final = (
            s_trend * weights["trend"]
            + s_momentum * weights["momentum"]
            + s_volume * weights["volume"]
            + s_volatility * weights["volatility"]
            + (s_futures or 0.0) * weights["futures"]
        )

    final = max(-100.0, min(100.0, final))

    return LocalConfluenceResult(
        symbol=symbol,
        timeframe=timeframe,
        final_score=final,
        label=_label(final),
        direction=_direction(final),
        components=ScoreBreakdown(
            trend=s_trend,
            momentum=s_momentum,
            volume=s_volume,
            volatility=s_volatility,
            futures=s_futures,
        ),
        weights_applied=weights,
        computed_at=datetime.now(UTC),
    )


__all__ = [
    "DEFAULT_WEIGHTS",
    "compute_local_confluence",
    "compute_price_direction",
    "compute_volume_ratio",
]
