"""Ichimoku Cloud."""
from __future__ import annotations

import pytest

from app.services.indicators.base import klines_to_dataframe
from app.services.indicators.trend.ichimoku import compute_ichimoku

from ._synthetic import linear_downtrend, linear_uptrend, sideways


def test_uptrend_price_above_cloud() -> None:
    df = klines_to_dataframe(linear_uptrend(n=200))
    result = compute_ichimoku(df)
    assert result.cloud_state == "above"
    # Tenkan > Kijun (yükselen trend)
    assert result.tenkan > result.kijun


def test_downtrend_price_below_cloud() -> None:
    df = klines_to_dataframe(linear_downtrend(n=200))
    result = compute_ichimoku(df)
    assert result.cloud_state == "below"
    assert result.tenkan < result.kijun


def test_sideways_price_inside_cloud_is_possible() -> None:
    df = klines_to_dataframe(sideways(n=200))
    result = compute_ichimoku(df)
    # Yan piyasada cloud_state belirsiz olabilir; sadece çağrı patlamasın yeter
    assert result.cloud_state in ("above", "below", "inside")


def test_insufficient_data_raises() -> None:
    df = klines_to_dataframe(linear_uptrend(n=40))
    with pytest.raises(ValueError, match="en az 52"):
        compute_ichimoku(df)
