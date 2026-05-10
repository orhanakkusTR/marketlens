"""Local orchestrator: label/direction thresholds + weight redistribution."""
from __future__ import annotations

import pandas as pd
import pytest

from app.services.confluence.local import (
    DEFAULT_WEIGHTS,
    _direction,
    _label,
    _normalize_weights_without_futures,
    compute_local_confluence,
    compute_price_direction,
    compute_volume_ratio,
)
from tests.test_confluence_scorers import (
    _make_futures,
    _make_momentum,
    _make_trend,
    _make_volatility,
    _make_volume,
)
from tests._synthetic import linear_uptrend
from app.services.indicators.base import klines_to_dataframe


# ─── Label thresholds (5 seviye) ───


def test_label_strong_bullish_above_60() -> None:
    assert _label(75) == "strong_bullish"
    assert _label(60.001) == "strong_bullish"


def test_label_bullish_30_to_60() -> None:
    assert _label(45) == "bullish"
    assert _label(30.001) == "bullish"
    assert _label(60) == "bullish"  # eşik içinde (= 60 değil > 60 strong)


def test_label_neutral_minus30_to_30() -> None:
    assert _label(0) == "neutral"
    assert _label(20) == "neutral"
    assert _label(30) == "neutral"
    assert _label(-30) == "neutral"


def test_label_bearish_minus60_to_minus30() -> None:
    assert _label(-45) == "bearish"
    assert _label(-31) == "bearish"


def test_label_strong_bearish_below_minus60() -> None:
    assert _label(-75) == "strong_bearish"
    assert _label(-60.001) == "strong_bearish"


# ─── Direction thresholds (long/short/neutral) ───


def test_direction_long_above_20() -> None:
    assert _direction(25) == "long"
    assert _direction(21) == "long"


def test_direction_short_below_minus20() -> None:
    assert _direction(-25) == "short"


def test_direction_neutral_in_band() -> None:
    assert _direction(0) == "neutral"
    assert _direction(15) == "neutral"
    assert _direction(-20) == "neutral"
    assert _direction(20) == "neutral"


# ─── Weight redistribution (GOLD case) ───


def test_default_weights_sum_to_1() -> None:
    total = sum(DEFAULT_WEIGHTS.values())
    assert total == pytest.approx(1.0)


def test_normalized_weights_sum_to_1() -> None:
    norm = _normalize_weights_without_futures()
    assert sum(norm.values()) == pytest.approx(1.0)
    assert "futures" not in norm


def test_normalized_weights_match_user_spec() -> None:
    norm = _normalize_weights_without_futures()
    # Kullanıcı spec'i: trend 0.471, momentum 0.235, volume 0.176, volatility 0.118
    assert norm["trend"] == pytest.approx(0.40 / 0.85, abs=0.001)
    assert norm["momentum"] == pytest.approx(0.20 / 0.85, abs=0.001)
    assert norm["volume"] == pytest.approx(0.15 / 0.85, abs=0.001)
    assert norm["volatility"] == pytest.approx(0.10 / 0.85, abs=0.001)


# ─── Aux helpers ───


def test_compute_volume_ratio_uses_last_20_mean() -> None:
    df = klines_to_dataframe(linear_uptrend(n=30))
    # Synthetic uptrend uniform volume (100) → ratio ~= 1.0
    ratio = compute_volume_ratio(df, bars=20)
    assert ratio == pytest.approx(1.0)


def test_compute_volume_ratio_short_history() -> None:
    df = klines_to_dataframe(linear_uptrend(n=2))
    # 2 bar — fallback ratio
    ratio = compute_volume_ratio(df, bars=20)
    assert ratio > 0


def test_compute_price_direction_up() -> None:
    df = klines_to_dataframe(linear_uptrend(n=30))
    direction = compute_price_direction(df, bars=20, threshold_pct=0.5)
    assert direction == "up"


def test_compute_price_direction_flat_short_history() -> None:
    df = klines_to_dataframe(linear_uptrend(n=5))
    direction = compute_price_direction(df, bars=20)
    assert direction == "flat"


# ─── compute_local_confluence end-to-end (synthetic) ───


def test_compute_local_confluence_strong_bullish_btc() -> None:
    """Tüm modüller bullish + futures → strong_bullish + long."""
    df = klines_to_dataframe(linear_uptrend(n=100))
    trend = _make_trend()  # full bullish
    momentum = _make_momentum(
        rsi_value=65, macd_hist=1.0, macd_dir="rising", stoch_k=60, stoch_d=50,
        div_rsi_type="regular_bullish",
    )
    volume = _make_volume(obv_slope="rising")
    volatility = _make_volatility(squeeze=True, middle=100.0, atr_pct=1.5)
    futures = _make_futures(funding_rate=-0.001, oi_change_24h=2.0, ls_ratio=0.2)

    result = compute_local_confluence(
        symbol="BTCUSDT",
        timeframe="4H",
        df=df,
        trend=trend,
        momentum=momentum,
        volume=volume,
        volatility=volatility,
        futures=futures,
        price=105.0,  # > VAH
    )
    assert result.final_score > 60
    assert result.label == "strong_bullish"
    assert result.direction == "long"
    assert result.components.futures is not None


def test_compute_local_confluence_no_futures_renormalize() -> None:
    """futures=None → weights renormalize, components.futures = None.

    Ocak 2026 sonrası: XAUUSDT artık futures destekli, ama futures verisi
    çekilemediği durumlar için renormalize davranışı korunur (synthetic test).
    """
    df = klines_to_dataframe(linear_uptrend(n=100))
    result = compute_local_confluence(
        symbol="XAUUSDT",
        timeframe="4H",
        df=df,
        trend=_make_trend(),
        momentum=_make_momentum(rsi_value=65, macd_hist=1.0, macd_dir="rising"),
        volume=_make_volume(obv_slope="rising"),
        volatility=_make_volatility(squeeze=False, atr_pct=1.5),
        futures=None,
        price=105.0,
    )
    assert result.components.futures is None
    assert "futures" not in result.weights_applied
    # Renormalized weights toplamı 1
    assert sum(result.weights_applied.values()) == pytest.approx(1.0)
    # Yine bullish (futures yok ama trend/momentum/volume güçlü)
    assert result.final_score > 30


def test_compute_local_confluence_invalid_timeframe_raises() -> None:
    df = klines_to_dataframe(linear_uptrend(n=50))
    with pytest.raises(ValueError, match="Bilinmeyen timeframe"):
        compute_local_confluence(
            symbol="BTCUSDT",
            timeframe="BAD",
            df=df,
            trend=_make_trend(),
            momentum=_make_momentum(),
            volume=_make_volume(),
            volatility=_make_volatility(),
            futures=None,
            price=100.0,
        )


def test_compute_local_confluence_score_clamped_to_100() -> None:
    df = klines_to_dataframe(linear_uptrend(n=100))
    result = compute_local_confluence(
        symbol="BTCUSDT",
        timeframe="4H",
        df=df,
        trend=_make_trend(),
        momentum=_make_momentum(rsi_value=65, macd_hist=1.0, macd_dir="rising",
                                 stoch_k=60, stoch_d=50, div_rsi_type="regular_bullish"),
        volume=_make_volume(obv_slope="rising"),
        volatility=_make_volatility(squeeze=True),
        futures=_make_futures(funding_rate=-0.001, oi_change_24h=2.0, ls_ratio=0.2),
        price=105.0,
    )
    assert -100 <= result.final_score <= 100
