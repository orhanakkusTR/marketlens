"""Counter-trend detector: 6 warning tipi + severity sıralama + neutral."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.schemas.indicators import (
    DivergenceResult,
    FundingAnalysisResult,
    FuturesIndicators,
    LongShortAnomalyResult,
    MACDResult,
    MomentumIndicators,
    OIChangeResult,
    RSIResult,
    StochRSIResult,
)
from app.services.indicators.base import klines_to_dataframe
from app.services.quality.counter_trend import (
    MAX_WARNINGS,
    counter_trend_detector,
)
from tests._synthetic import linear_uptrend


def _momentum(rsi_value: float = 55.0) -> MomentumIndicators:
    return MomentumIndicators(
        rsi=RSIResult(current=rsi_value, history=[rsi_value], state="neutral"),
        macd=MACDResult(macd=0, signal=0, histogram=0, histogram_direction="flat", cross="none"),
        stoch_rsi=StochRSIResult(k=50, d=50, state="neutral", cross="none"),
        divergence_rsi=DivergenceResult(detected=False, type="none"),
        divergence_macd=DivergenceResult(detected=False, type="none"),
    )


def _futures(
    funding_rate: float = 0.0,
    ls_ratio: float = 1.0,
) -> FuturesIndicators:
    return FuturesIndicators(
        funding=FundingAnalysisResult(
            current_rate=funding_rate,
            avg_24h=funding_rate,
            avg_7d=funding_rate,
            extreme=abs(funding_rate) > 0.0008,
            next_funding_time=0,
        ),
        open_interest=OIChangeResult(
            current=1000, change_1h_pct=0, change_4h_pct=0, change_24h_pct=0
        ),
        long_short=LongShortAnomalyResult(
            ratio=ls_ratio,
            long_account=ls_ratio / (1 + ls_ratio),
            short_account=1 / (1 + ls_ratio),
            extreme=ls_ratio > 3.0 or ls_ratio < 0.33,
            period="1h",
        ),
    )


def _flat_df(n: int = 50, price: float = 100.0):
    """N bar, sabit fiyat ve hacim."""
    klines = [
        {
            "open_time": i * 14_400_000,
            "open": price,
            "high": price + 0.1,
            "low": price - 0.1,
            "close": price,
            "volume": 100.0,
            "close_time": (i + 1) * 14_400_000,
            "quote_volume": price * 100,
            "trades": 100,
        }
        for i in range(n)
    ]
    return klines_to_dataframe(klines)


def test_neutral_direction_returns_empty() -> None:
    df = _flat_df()
    warnings = counter_trend_detector.detect(
        df=df,
        momentum=_momentum(),
        futures=_futures(),
        direction="neutral",
        timeframe="4H",
    )
    assert warnings == []


def test_parabolic_move_detected_long() -> None:
    """Son 4H bar'da >%3 hareket → parabolic_move."""
    # 50 bar düz 100, son bar +%5
    klines = []
    for i in range(50):
        klines.append({
            "open_time": i * 14_400_000, "open": 100.0, "high": 100.1, "low": 99.9,
            "close": 100.0, "volume": 100.0, "close_time": (i + 1) * 14_400_000,
            "quote_volume": 10000, "trades": 100,
        })
    klines[-1]["close"] = 105.0  # +%5
    df = klines_to_dataframe(klines)
    warnings = counter_trend_detector.detect(
        df=df, momentum=_momentum(), futures=_futures(),
        direction="long", timeframe="4H",
    )
    types = [w.type for w in warnings]
    assert "parabolic_move" in types
    par = next(w for w in warnings if w.type == "parabolic_move")
    assert par.severity == "high"


def test_extreme_funding_detected() -> None:
    warnings = counter_trend_detector.detect(
        df=_flat_df(),
        momentum=_momentum(),
        futures=_futures(funding_rate=0.0015),  # > 0.08%
        direction="long",
        timeframe="4H",
    )
    types = [w.type for w in warnings]
    assert "extreme_funding" in types


def test_extreme_ls_long_squeeze() -> None:
    warnings = counter_trend_detector.detect(
        df=_flat_df(),
        momentum=_momentum(),
        futures=_futures(ls_ratio=4.0),
        direction="long",
        timeframe="4H",
    )
    types = [w.type for w in warnings]
    assert "extreme_ls_long" in types


def test_extreme_ls_short_squeeze() -> None:
    warnings = counter_trend_detector.detect(
        df=_flat_df(),
        momentum=_momentum(),
        futures=_futures(ls_ratio=0.2),
        direction="short",
        timeframe="4H",
    )
    types = [w.type for w in warnings]
    assert "extreme_ls_short" in types


def test_extreme_ls_does_not_trigger_for_wrong_direction() -> None:
    """L/S 4.0 ile short → trigger olmaz (sadece long için)."""
    warnings = counter_trend_detector.detect(
        df=_flat_df(),
        momentum=_momentum(),
        futures=_futures(ls_ratio=4.0),
        direction="short",
        timeframe="4H",
    )
    types = [w.type for w in warnings]
    assert "extreme_ls_long" not in types
    assert "extreme_ls_short" not in types


def test_volume_exhaustion_long() -> None:
    """Son 3 mum hacim azalıyor + long → volume_exhaustion."""
    klines = []
    for i in range(50):
        klines.append({
            "open_time": i * 14_400_000, "open": 100.0, "high": 100.1, "low": 99.9,
            "close": 100.0, "volume": 100.0 - (i if i >= 47 else 0) * 5,  # son 3 azalıyor
            "close_time": (i + 1) * 14_400_000, "quote_volume": 10000, "trades": 100,
        })
    # Son 4 mum hacim ardışık azalan: 100 → 90 → 80 → 70 → 60
    # (consecutive_volume_decreasing 4 sayar)
    klines[-4]["volume"] = 100.0
    klines[-3]["volume"] = 90.0
    klines[-2]["volume"] = 80.0
    klines[-1]["volume"] = 70.0
    df = klines_to_dataframe(klines)
    warnings = counter_trend_detector.detect(
        df=df, momentum=_momentum(), futures=_futures(),
        direction="long", timeframe="4H",
    )
    types = [w.type for w in warnings]
    assert "volume_exhaustion" in types


def test_rsi_stall_overbought_flat_price() -> None:
    """RSI > 75 + 4H fiyat değişimi |0.5%| < → rsi_stall."""
    df = _flat_df()  # düz 100 fiyat, son 4H bar ~0% değişim
    warnings = counter_trend_detector.detect(
        df=df,
        momentum=_momentum(rsi_value=80),
        futures=_futures(),
        direction="long",
        timeframe="4H",
    )
    types = [w.type for w in warnings]
    assert "rsi_stall" in types


def test_warnings_severity_sorted_high_first() -> None:
    """High severity'ler önce gelmeli."""
    # Birden fazla warning trigger
    df = _flat_df()
    warnings = counter_trend_detector.detect(
        df=df,
        momentum=_momentum(rsi_value=80),  # rsi_stall (medium)
        futures=_futures(funding_rate=0.002, ls_ratio=4.0),  # funding+ls (high)
        direction="long",
        timeframe="4H",
    )
    # En azından 2 high + 1 medium
    severities = [w.severity for w in warnings]
    assert severities[0] == "high"
    # Tüm high'lar mediumlardan önce
    high_indices = [i for i, s in enumerate(severities) if s == "high"]
    medium_indices = [i for i, s in enumerate(severities) if s == "medium"]
    if high_indices and medium_indices:
        assert max(high_indices) < min(medium_indices)


def test_warnings_max_5_limit() -> None:
    """Çok fazla warning olsa max 5 dön."""
    df = _flat_df()
    # Tüm trigger'ları aç
    klines = []
    for i in range(50):
        klines.append({
            "open_time": i * 14_400_000, "open": 100.0, "high": 100.1, "low": 99.9,
            "close": 100.0, "volume": 100.0, "close_time": (i + 1) * 14_400_000,
            "quote_volume": 10000, "trades": 100,
        })
    klines[-1]["close"] = 105.0  # parabolic
    klines[-4]["volume"] = 100; klines[-3]["volume"] = 90
    klines[-2]["volume"] = 80; klines[-1]["volume"] = 70  # vol exh (4 azalan)
    df = klines_to_dataframe(klines)

    warnings = counter_trend_detector.detect(
        df=df,
        momentum=_momentum(rsi_value=80),  # rsi_stall
        futures=_futures(funding_rate=0.002, ls_ratio=4.0),  # funding + ls
        direction="long",
        timeframe="4H",
    )
    assert len(warnings) <= MAX_WARNINGS


def test_no_futures_no_funding_or_ls_warnings() -> None:
    """futures=None → funding/ls warning üretilmez."""
    df = _flat_df()
    warnings = counter_trend_detector.detect(
        df=df, momentum=_momentum(),
        futures=None, direction="long", timeframe="4H",
    )
    types = [w.type for w in warnings]
    assert "extreme_funding" not in types
    assert "extreme_ls_long" not in types
