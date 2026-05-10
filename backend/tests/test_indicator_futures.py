"""Futures: funding_analysis + oi_change + ls_anomaly + has_futures flag."""
from __future__ import annotations

import pytest

from app.data.symbols_meta import has_futures
from app.services.indicators.futures.funding_analysis import (
    EXTREME_THRESHOLD,
    compute_funding_analysis,
)
from app.services.indicators.futures.long_short_anomaly import (
    EXTREME_HIGH,
    EXTREME_LOW,
    compute_ls_anomaly,
)
from app.services.indicators.futures.oi_change import (
    BARS_1H,
    BARS_4H,
    BARS_24H,
    compute_oi_change,
)


# ─── has_futures ───


def test_has_futures_btc() -> None:
    assert has_futures("BTCUSDT") is True


def test_has_futures_xauusdt_present() -> None:
    """Ocak 2026 sonrası: XAUUSDT artık Binance TradFi Perpetual'da → True."""
    assert has_futures("XAUUSDT") is True


def test_has_futures_legacy_gold_codes() -> None:
    """Eski code'lar (GOLD/XAUUSD) artık tanımlı değil."""
    assert has_futures("GOLD") is False
    assert has_futures("XAUUSD") is False


def test_has_futures_case_insensitive() -> None:
    assert has_futures("btcusdt") is True


# ─── Funding analysis ───


def test_funding_extreme_above_threshold() -> None:
    rate = EXTREME_THRESHOLD * 1.5
    result = compute_funding_analysis(history=[], current_rate=rate, next_funding_time=0)
    assert result.extreme is True
    assert result.current_rate == rate


def test_funding_not_extreme_below_threshold() -> None:
    rate = EXTREME_THRESHOLD * 0.5
    result = compute_funding_analysis(history=[], current_rate=rate, next_funding_time=0)
    assert result.extreme is False


def test_funding_avg_24h_uses_last_3_payments() -> None:
    history = [
        {"funding_rate": 0.0001, "funding_time": 1},
        {"funding_rate": 0.0002, "funding_time": 2},
        {"funding_rate": 0.0003, "funding_time": 3},  # avg_24h = (1+2+3)/3 = 0.0002
        {"funding_rate": 0.0004, "funding_time": 4},
        {"funding_rate": 0.0005, "funding_time": 5},  # last 3: 3+4+5 = 0.0004
    ]
    result = compute_funding_analysis(history, current_rate=0.0005, next_funding_time=0)
    assert result.avg_24h == pytest.approx(0.0004)


def test_funding_avg_7d_uses_last_21_payments() -> None:
    history = [{"funding_rate": 0.0001, "funding_time": i} for i in range(25)]
    result = compute_funding_analysis(history, current_rate=0.0001, next_funding_time=0)
    # Tüm rate'ler 0.0001 → avg = 0.0001
    assert result.avg_7d == pytest.approx(0.0001)


def test_funding_empty_history_uses_current_rate() -> None:
    result = compute_funding_analysis([], current_rate=0.001, next_funding_time=0)
    assert result.avg_24h == 0.001
    assert result.avg_7d == 0.001


# ─── OI change ───


def test_oi_change_calculates_correct_pct() -> None:
    # 5m bar bazında 300 bar; OI sürekli +1 birim büyüyor
    history = [{"open_interest": 1000.0 + i} for i in range(BARS_24H + 5)]
    result = compute_oi_change(history)
    # Current = 1000 + 292 = 1292; 1h önce = 1000 + 280; 4h önce = 1000 + 244;
    # 24h önce = 1000 + 4 (history index = -288-1 = -289 → ~en başa yakın)
    # Tüm değişimler pozitif olmalı
    assert result.change_1h_pct > 0
    assert result.change_4h_pct > 0
    assert result.change_24h_pct > result.change_1h_pct  # 24h daha büyük değişim


def test_oi_change_negative_for_decrease() -> None:
    history = [{"open_interest": 1000.0 - i * 0.5} for i in range(BARS_24H + 5)]
    result = compute_oi_change(history)
    assert result.change_1h_pct < 0
    assert result.change_4h_pct < 0
    assert result.change_24h_pct < 0


def test_oi_change_short_history_uses_oldest() -> None:
    history = [{"open_interest": 100.0}, {"open_interest": 110.0}]
    result = compute_oi_change(history)
    # 2 bar = yeterli yok, en eski referans
    expected = ((110 - 100) / 100) * 100
    assert result.change_1h_pct == pytest.approx(expected)
    assert result.change_4h_pct == pytest.approx(expected)
    assert result.change_24h_pct == pytest.approx(expected)


def test_oi_change_empty_raises() -> None:
    with pytest.raises(ValueError, match="OI history boş"):
        compute_oi_change([])


def test_oi_change_constants_match_5m_granularity() -> None:
    """1h=12, 4h=48, 24h=288 (5dk bar)."""
    assert BARS_1H == 12
    assert BARS_4H == 48
    assert BARS_24H == 288


# ─── L/S anomaly ───


def test_ls_extreme_high() -> None:
    data = [{"long_short_ratio": 3.5, "long_account": 0.78, "short_account": 0.22}]
    result = compute_ls_anomaly(data)
    assert result.extreme is True
    assert result.ratio == 3.5


def test_ls_extreme_low() -> None:
    data = [{"long_short_ratio": 0.25, "long_account": 0.20, "short_account": 0.80}]
    result = compute_ls_anomaly(data)
    assert result.extreme is True


def test_ls_normal_range() -> None:
    data = [{"long_short_ratio": 1.5, "long_account": 0.60, "short_account": 0.40}]
    result = compute_ls_anomaly(data)
    assert result.extreme is False


def test_ls_uses_latest_record() -> None:
    data = [
        {"long_short_ratio": 1.0, "long_account": 0.5, "short_account": 0.5},
        {"long_short_ratio": 4.0, "long_account": 0.8, "short_account": 0.2},  # latest
    ]
    result = compute_ls_anomaly(data)
    assert result.ratio == 4.0
    assert result.extreme is True


def test_ls_empty_raises() -> None:
    with pytest.raises(ValueError, match="boş"):
        compute_ls_anomaly([])


def test_ls_thresholds() -> None:
    assert EXTREME_HIGH == 3.0
    assert EXTREME_LOW == pytest.approx(0.33, abs=1e-9)
