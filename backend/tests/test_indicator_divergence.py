"""Divergence detection — synthetic regular bullish + regular bearish."""
from __future__ import annotations

import pandas as pd

from app.services.indicators.base import klines_to_dataframe
from app.services.indicators.momentum.divergence import detect_divergence

from ._synthetic import zigzag_for_divergence


def test_regular_bullish_detected() -> None:
    klines, ind_values = zigzag_for_divergence("regular_bullish")
    df = klines_to_dataframe(klines)
    indicator_series = pd.Series(ind_values, index=df.index)

    result = detect_divergence(df, indicator_series, lookback_bars=120)
    assert result.detected, "Regular bullish divergence tespit edilmedi"
    assert result.type == "regular_bullish"
    assert len(result.price_swings) == 2
    # Price LL: ikinci swing fiyatı birinciden düşük
    assert result.price_swings[1].price < result.price_swings[0].price
    # Indicator HL: ikinci swing değeri birinciden yüksek
    assert result.indicator_swings[1].value > result.indicator_swings[0].value


def test_regular_bearish_detected() -> None:
    klines, ind_values = zigzag_for_divergence("regular_bearish")
    df = klines_to_dataframe(klines)
    indicator_series = pd.Series(ind_values, index=df.index)

    result = detect_divergence(df, indicator_series, lookback_bars=120)
    assert result.detected, "Regular bearish divergence tespit edilmedi"
    assert result.type == "regular_bearish"
    # Price HH: ikinci tepe birinciden yüksek
    assert result.price_swings[1].price > result.price_swings[0].price
    # Indicator LH: ikinci tepe değeri birinciden düşük
    assert result.indicator_swings[1].value < result.indicator_swings[0].value


def test_no_divergence_in_aligned_uptrend() -> None:
    """Tutarlı uptrend → divergence yok (price HH + indicator HH)."""
    from ._synthetic import linear_uptrend

    klines = linear_uptrend(n=200)
    df = klines_to_dataframe(klines)
    # İndikatör de fiyatla aynı yönlü (yapay)
    indicator_series = df["close"] * 0.5
    result = detect_divergence(df, indicator_series, lookback_bars=120)
    # Tutarlı seri pivot bulamayabilir veya bulsa da divergence sınıflanmaz
    if result.detected:
        assert result.type not in ("regular_bullish", "regular_bearish")


def test_min_swings_parameter() -> None:
    """min_swings=2 default — fonksiyon kabul ediyor."""
    klines, ind_values = zigzag_for_divergence("regular_bullish")
    df = klines_to_dataframe(klines)
    indicator_series = pd.Series(ind_values, index=df.index)

    # Default 2 ile çalışıyor mu
    result = detect_divergence(df, indicator_series, lookback_bars=120, min_swings=2)
    assert result.detected
