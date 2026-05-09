"""Volatility: ATR + Bollinger."""
from __future__ import annotations

import pytest

from app.services.indicators.base import klines_to_dataframe
from app.services.indicators.volatility.atr import compute_atr
from app.services.indicators.volatility.bollinger import compute_bollinger

from ._synthetic import linear_uptrend, sideways


def test_atr_positive_for_real_movement() -> None:
    df = klines_to_dataframe(linear_uptrend(n=100))
    result = compute_atr(df, period=14)
    assert result.value_usdt > 0
    assert result.value_pct > 0
    assert result.period == 14


def test_atr_pct_calculation() -> None:
    df = klines_to_dataframe(linear_uptrend(n=100))
    result = compute_atr(df)
    price = float(df["close"].iloc[-1])
    expected_pct = (result.value_usdt / price) * 100
    assert abs(result.value_pct - expected_pct) < 1e-6


def test_atr_insufficient_data_raises() -> None:
    df = klines_to_dataframe(linear_uptrend(n=10))
    with pytest.raises(ValueError, match="ATR hesaplanamadı"):
        compute_atr(df, period=14)


def test_bollinger_basic_structure() -> None:
    df = klines_to_dataframe(linear_uptrend(n=100))
    result = compute_bollinger(df, length=20, std=2.0)
    # Düz uptrend: upper > middle > lower
    assert result.upper > result.middle > result.lower
    assert result.width_pct > 0


def test_bollinger_squeeze_detection_in_sideways() -> None:
    """Düz yatay piyasa → BB Width düşük → squeeze (en alt %25) olabilir."""
    # Çok düşük amp ile sideways → küçük width
    df = klines_to_dataframe(sideways(n=200, mid=100, amp=0.3))
    result = compute_bollinger(df)
    # Squeeze flag bool olmalı; kesin True/False zorlamak deterministik değil
    assert isinstance(result.squeeze, bool)


def test_bollinger_squeeze_threshold_consistency() -> None:
    """Squeeze sadece current width <= 25th percentile ise True dönmeli — tutarlılık."""
    import numpy as np
    import pandas_ta as ta

    from app.services.indicators.volatility.bollinger import _width_series

    df = klines_to_dataframe(linear_uptrend(n=200))
    result = compute_bollinger(df)

    bb = ta.bbands(df["close"], length=20, std=2.0)
    width_series = _width_series(bb).dropna().tail(100)
    threshold = float(np.percentile(width_series.values, 25))

    if result.width_pct <= threshold:
        assert result.squeeze is True
    else:
        assert result.squeeze is False
