"""Moving averages: TF-aware EMA/SMA + alignment."""
from __future__ import annotations

import pytest

from app.services.indicators.base import klines_to_dataframe
from app.services.indicators.trend.moving_averages import compute_moving_averages

from ._synthetic import linear_downtrend, linear_uptrend, sideways


def test_uptrend_4h_uses_only_ema_and_is_bullish_stack() -> None:
    df = klines_to_dataframe(linear_uptrend(n=300))
    result = compute_moving_averages(df, "4H")

    assert len(result.moving_averages) == 3
    types = {ma.type for ma in result.moving_averages}
    assert types == {"EMA"}
    assert result.alignment == "bullish_stack"
    # Fiyat tüm MA'ların üstünde
    assert all(ma.distance_pct > 0 for ma in result.moving_averages)


def test_downtrend_1d_uses_ema_and_sma_and_is_bearish_stack() -> None:
    df = klines_to_dataframe(linear_downtrend(n=300))
    result = compute_moving_averages(df, "1D")

    types = {ma.type for ma in result.moving_averages}
    # 1D → EMA 50/100 + SMA 200
    assert types == {"EMA", "SMA"}
    assert result.alignment == "bearish_stack"
    assert all(ma.distance_pct < 0 for ma in result.moving_averages)


def test_weekly_uses_only_sma() -> None:
    df = klines_to_dataframe(linear_uptrend(n=300))
    result = compute_moving_averages(df, "1W")
    types = {ma.type for ma in result.moving_averages}
    assert types == {"SMA"}


def test_sideways_not_clean_stack() -> None:
    """Sin oscillation MA'ları orta noktaya yaklaştırır — stack çoğu zaman mixed."""
    df = klines_to_dataframe(sideways(n=300, mid=100, amp=5))
    result = compute_moving_averages(df, "4H")
    # Net bullish/bearish stack olmamalı (sin yönünde anlık dalga olabilir)
    # Ama daimi stack tutarsız — sonuç deterministik değil; en azından MA'lar
    # birbirine çok yakın
    spreads = [abs(ma.distance_pct) for ma in result.moving_averages]
    assert max(spreads) < 10.0  # %10'dan az sapma — yan piyasa


def test_unknown_timeframe_raises() -> None:
    df = klines_to_dataframe(linear_uptrend(n=300))
    with pytest.raises(ValueError, match="Bilinmeyen timeframe"):
        compute_moving_averages(df, "2H")
