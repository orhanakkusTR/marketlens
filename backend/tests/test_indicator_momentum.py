"""RSI + MACD + StochRSI momentum testleri."""
from __future__ import annotations

import pytest

from app.services.indicators.base import klines_to_dataframe
from app.services.indicators.momentum.macd import compute_macd
from app.services.indicators.momentum.rsi import compute_rsi
from app.services.indicators.momentum.stoch_rsi import compute_stoch_rsi

from ._synthetic import (
    accelerating_uptrend,
    decelerating_downtrend,
    linear_downtrend,
    linear_uptrend,
    sideways,
)

# ─── RSI ───


def test_rsi_uptrend_overbought() -> None:
    df = klines_to_dataframe(linear_uptrend(n=200))
    result = compute_rsi(df, period=14)
    # Düz uptrend → RSI 100'e yakın (sürekli yeşil mum)
    assert result.current > 70
    assert result.state == "overbought"
    assert 0 < result.current <= 100
    assert len(result.history) > 0


def test_rsi_downtrend_oversold() -> None:
    df = klines_to_dataframe(linear_downtrend(n=200))
    result = compute_rsi(df, period=14)
    assert result.current < 30
    assert result.state == "oversold"


def test_rsi_sideways_neutral() -> None:
    df = klines_to_dataframe(sideways(n=200))
    result = compute_rsi(df, period=14)
    assert 30 < result.current < 70
    assert result.state == "neutral"


def test_rsi_insufficient_data_raises() -> None:
    df = klines_to_dataframe(linear_uptrend(n=10))
    with pytest.raises(ValueError, match="hesaplanamadı"):
        compute_rsi(df, period=14)


# ─── MACD ───


def test_macd_uptrend_bullish() -> None:
    """Hızlanan uptrend → MACD > Signal, histogram pozitif (steady state'e oturmaz)."""
    df = klines_to_dataframe(accelerating_uptrend(n=200))
    result = compute_macd(df)
    assert result.macd > result.signal
    assert result.histogram > 0


def test_macd_downtrend_bearish() -> None:
    df = klines_to_dataframe(decelerating_downtrend(n=200))
    result = compute_macd(df)
    assert result.macd < result.signal
    assert result.histogram < 0


# ─── Stoch RSI ───


def test_stoch_rsi_uptrend() -> None:
    df = klines_to_dataframe(linear_uptrend(n=200))
    result = compute_stoch_rsi(df)
    # Üstte saturate olur
    assert 0 <= result.k <= 100
    assert 0 <= result.d <= 100


def test_stoch_rsi_state_classification() -> None:
    df = klines_to_dataframe(sideways(n=200))
    result = compute_stoch_rsi(df)
    assert result.state in ("overbought", "oversold", "neutral")
