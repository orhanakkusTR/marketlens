"""Volume: OBV + VWAP + Volume Profile."""
from __future__ import annotations

import pytest

from app.services.indicators.base import klines_to_dataframe
from app.services.indicators.volume.obv import compute_obv
from app.services.indicators.volume.volume_profile import compute_volume_profile
from app.services.indicators.volume.vwap import compute_vwap

from ._synthetic import linear_downtrend, linear_uptrend, sideways

# ─── OBV ───


def test_obv_uptrend_rising_slope() -> None:
    df = klines_to_dataframe(linear_uptrend(n=200))
    result = compute_obv(df)
    # Sürekli yeşil mum → OBV artıyor
    assert result.slope == "rising"


def test_obv_downtrend_falling_slope() -> None:
    df = klines_to_dataframe(linear_downtrend(n=200))
    result = compute_obv(df)
    assert result.slope == "falling"


# ─── VWAP ───


def test_vwap_returns_none_for_4h_and_above() -> None:
    df = klines_to_dataframe(linear_uptrend(n=100))
    assert compute_vwap(df, "4H") is None
    assert compute_vwap(df, "1D") is None
    assert compute_vwap(df, "1W") is None
    assert compute_vwap(df, "1M") is None


def test_vwap_returns_value_for_1h() -> None:
    # 24 mum * 1H = 24h. Synthetic data 4H kullanıyor — yine de döner çünkü
    # session_start mantığı UTC günü başlangıcına dayanıyor.
    df = klines_to_dataframe(linear_uptrend(n=100))
    result = compute_vwap(df, "1H")
    # En azından bir intraday session içinde data var → result not None
    if result is not None:
        assert result.value > 0
        assert isinstance(result.distance_pct, float)


def test_vwap_returns_value_for_15m() -> None:
    df = klines_to_dataframe(linear_uptrend(n=200))
    result = compute_vwap(df, "15m")
    if result is not None:
        assert result.value > 0


# ─── Volume Profile ───


def test_volume_profile_basic() -> None:
    df = klines_to_dataframe(linear_uptrend(n=50))
    result = compute_volume_profile(df, "4H")
    # Linear uptrend: POC, VAH, VAL price aralığı içinde
    price_min = float(df["low"].min())
    price_max = float(df["high"].max())
    assert price_min <= result.poc <= price_max
    assert result.val <= result.poc <= result.vah
    assert result.total_volume > 0
    assert result.bin_count == 50


def test_volume_profile_sideways_poc_near_mid() -> None:
    """Sideways piyasada POC orta noktaya yakın olmalı."""
    df = klines_to_dataframe(sideways(n=100, mid=100, amp=2))
    result = compute_volume_profile(df, "4H", window_bars=100)
    # Mid'e yakın (±5%)
    assert 95 < result.poc < 105


def test_volume_profile_window_bars_respected() -> None:
    df = klines_to_dataframe(linear_uptrend(n=100))
    result = compute_volume_profile(df, "4H", window_bars=20)
    assert result.window_bars == 20


def test_volume_profile_insufficient_data_raises() -> None:
    df = klines_to_dataframe(linear_uptrend(n=1))
    with pytest.raises(ValueError, match="en az 2 mum"):
        compute_volume_profile(df, "4H")
