"""Position Sizer unit testleri — volatility factor, position, R/R, liq, funding."""
from __future__ import annotations

from math import isclose

import pytest

from app.services.risk.position_sizer import (
    BTC_VOLATILITY_HIGH,
    BTC_VOLATILITY_MED,
    FUNDING_PERIODS_24H,
    FUNDING_PERIODS_72H,
    FUNDING_PERIODS_1W,
    TP_WEIGHTS,
    compute_position,
    compute_volatility_factor,
)


# ─── Volatility factor ───


def test_volatility_factor_normal() -> None:
    adj = compute_volatility_factor(0.6, None)
    assert adj.factor == 1.0
    assert "Normal" in adj.reason


def test_volatility_factor_btc_high() -> None:
    adj = compute_volatility_factor(-9.5, None)
    assert adj.factor == 0.5
    assert "8" in adj.reason


def test_volatility_factor_btc_medium() -> None:
    adj = compute_volatility_factor(6.0, None)
    assert adj.factor == 0.7
    assert "5" in adj.reason


def test_volatility_factor_atr_zscore() -> None:
    adj = compute_volatility_factor(0.6, 2.5)
    assert adj.factor == 0.7
    assert "z-score" in adj.reason


def test_volatility_factor_btc_high_overrides_atr() -> None:
    """BTC > 8% ilk kontrol kazanır."""
    adj = compute_volatility_factor(-10.0, 3.0)
    assert adj.factor == 0.5


def test_volatility_factor_no_data() -> None:
    adj = compute_volatility_factor(None, None)
    assert adj.factor == 1.0


# ─── Position size: BTC 80500/79500/3000USDT/2% ───


def test_position_btc_long_2pct_3000usdt() -> None:
    """Entry 80500, stop 79500, 3000 USDT, 2% → 60 USDT risk, ~4830 USDT pozisyon."""
    result = compute_position(
        symbol="BTCUSDT",
        direction="long",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=79500.0,
        targets=[83500.0],
        max_leverage=10,
        funding_rate=0.0,
        btc_24h_change_pct=0.6,  # normal
        atr_zscore=None,
    )
    # stop_distance_pct = 1000/80500 * 100 ≈ 1.2422%
    assert isclose(result.stop_distance_pct, 1000 / 80500 * 100, rel_tol=1e-4)
    # risk_amount = 60
    assert isclose(result.risk_amount_usd, 60.0, rel_tol=1e-6)
    # position_size = 60 / 0.012422 ≈ 4830
    assert isclose(result.position_size_usd, 60 / (1000 / 80500), rel_tol=1e-4)
    # leverage_required = ceil(4830 / 3000) = 2
    assert result.leverage_required == 2
    assert result.leverage_actual == 2
    # margin_used ≈ position/2 ≈ 2415
    assert isclose(result.margin_used, result.position_size_usd / 2, rel_tol=1e-6)
    # Direction kontrolü
    assert result.direction == "long"
    # adjusted = base (factor 1)
    assert result.adjusted_risk_pct == 2.0


def test_position_volatility_reduces_risk() -> None:
    """BTC %10 değişim → factor 0.5 → risk yarıya."""
    result = compute_position(
        symbol="BTCUSDT",
        direction="long",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=79500.0,
        targets=[83500.0],
        max_leverage=10,
        funding_rate=0.0,
        btc_24h_change_pct=10.0,
        atr_zscore=None,
    )
    assert result.adjusted_risk_pct == 1.0
    assert result.risk_amount_usd == 30.0
    assert any(w.code == "volatility_reduced" for w in result.warnings)


def test_position_leverage_capped() -> None:
    """Çok dar stop → required lev > max → cap + warning."""
    # Entry 80500, stop 80450 → 0.062% mesafe, position çok büyük olur
    result = compute_position(
        symbol="BTCUSDT",
        direction="long",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=80250.0,  # 0.31% — eşik üstünde (0.3 değil, çok azıcık üstünde)
        targets=[83500.0],
        max_leverage=10,
        funding_rate=0.0,
        btc_24h_change_pct=0.6,
        atr_zscore=None,
    )
    # stop_distance = 250/80500*100 ≈ 0.31%
    # position = 60 / 0.0031 ≈ 19320 → req lev = ceil(19320/3000) = 7
    # max=10 → actual=7, no cap
    assert result.leverage_required <= result.leverage_actual or result.leverage_actual == 10

    # Daha dar bir senaryo (eşiğin biraz üstü) ile 10x cap test edelim
    result2 = compute_position(
        symbol="BTCUSDT",
        direction="long",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=80250.0,
        targets=[83500.0],
        max_leverage=3,  # düşük max → cap zorla
        funding_rate=0.0,
        btc_24h_change_pct=0.6,
        atr_zscore=None,
    )
    assert result2.leverage_actual == 3
    assert any(w.code == "leverage_capped" for w in result2.warnings)


def test_position_stop_too_tight_blocking() -> None:
    """Stop mesafesi < 0.3% → blocking warning."""
    result = compute_position(
        symbol="BTCUSDT",
        direction="long",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=80450.0,  # 0.062% — eşik altı
        targets=[],
        max_leverage=10,
    )
    assert any(
        w.code == "stop_too_tight" and w.severity == "blocking"
        for w in result.warnings
    )
    # Korumalı: position_size 0 dönmeli (aşırı şişmesin)
    assert result.position_size_usd == 0.0


def test_position_stop_wrong_side_long() -> None:
    """Long pozisyonda stop entry'nin üstünde → blocking."""
    result = compute_position(
        symbol="BTCUSDT",
        direction="long",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=81000.0,
        targets=[83000.0],
        max_leverage=10,
    )
    assert any(
        w.code == "stop_wrong_side" and w.severity == "blocking"
        for w in result.warnings
    )


def test_position_stop_wrong_side_short() -> None:
    """Short pozisyonda stop entry'nin altında → blocking."""
    result = compute_position(
        symbol="BTCUSDT",
        direction="short",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=80000.0,
        targets=[78000.0],
        max_leverage=10,
    )
    assert any(w.code == "stop_wrong_side" for w in result.warnings)


# ─── R/R ───


def test_rr_three_targets_weighted() -> None:
    """TP1=1:3, TP2=1:5, TP3=1:8 → weighted = 0.40*3 + 0.35*5 + 0.25*8 = 4.95."""
    result = compute_position(
        symbol="BTCUSDT",
        direction="long",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=79500.0,
        targets=[83500.0, 85500.0, 88500.0],  # +3000, +5000, +8000 (risk 1000)
        max_leverage=10,
    )
    assert isclose(result.rr.tp1 or 0, 3.0, rel_tol=1e-6)
    assert isclose(result.rr.tp2 or 0, 5.0, rel_tol=1e-6)
    assert isclose(result.rr.tp3 or 0, 8.0, rel_tol=1e-6)
    expected = 0.40 * 3 + 0.35 * 5 + 0.25 * 8
    assert isclose(result.rr.weighted or 0, expected, rel_tol=1e-6)


def test_rr_short_direction() -> None:
    """Short: TP entry'nin altında. Entry 80500, stop 81500, TP 77500 → R/R 3."""
    result = compute_position(
        symbol="BTCUSDT",
        direction="short",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=81500.0,
        targets=[77500.0],
        max_leverage=10,
    )
    assert isclose(result.rr.tp1 or 0, 3.0, rel_tol=1e-6)
    assert isclose(result.rr.weighted or 0, 3.0, rel_tol=1e-6)


def test_rr_wrong_side_target_skipped() -> None:
    """Long pozisyonda TP entry'nin altında → None (R/R'a katkı yok)."""
    result = compute_position(
        symbol="BTCUSDT",
        direction="long",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=79500.0,
        targets=[78000.0],  # yanlış taraf
        max_leverage=10,
    )
    assert result.rr.tp1 is None
    assert result.rr.weighted is None


def test_rr_no_targets_warning() -> None:
    result = compute_position(
        symbol="BTCUSDT",
        direction="long",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=79500.0,
        targets=[],
        max_leverage=10,
    )
    assert any(w.code == "no_targets" for w in result.warnings)
    assert result.rr.weighted is None


def test_rr_partial_renormalize_weights() -> None:
    """Sadece TP1+TP2 → weighted weights renormalize."""
    result = compute_position(
        symbol="BTCUSDT",
        direction="long",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=79500.0,
        targets=[83500.0, 85500.0],  # R/R 3 ve 5
        max_leverage=10,
    )
    # 0.40 + 0.35 = 0.75 toplam; weighted = (0.40*3 + 0.35*5) / 0.75
    expected = (0.40 * 3 + 0.35 * 5) / 0.75
    assert isclose(result.rr.weighted or 0, expected, rel_tol=1e-6)


def test_rr_below_1_warning() -> None:
    """Weighted R/R < 1 → warning."""
    result = compute_position(
        symbol="BTCUSDT",
        direction="long",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=79500.0,
        targets=[80800.0],  # +300 / 1000 = 0.3
        max_leverage=10,
    )
    assert any(w.code == "rr_below_1" for w in result.warnings)


# ─── Liquidation ───


def test_liquidation_long_simple_formula() -> None:
    result = compute_position(
        symbol="BTCUSDT",
        direction="long",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=79500.0,
        targets=[83500.0],
        max_leverage=10,
    )
    # at_5x: 80500 * (1 - 1/5) = 64400
    # at_10x: 80500 * 0.9 = 72450
    assert isclose(result.liquidation.at_5x, 80500 * (1 - 1 / 5), rel_tol=1e-6)
    assert isclose(result.liquidation.at_10x, 80500 * (1 - 1 / 10), rel_tol=1e-6)


def test_liquidation_short_simple_formula() -> None:
    result = compute_position(
        symbol="BTCUSDT",
        direction="short",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=81500.0,
        targets=[77500.0],
        max_leverage=10,
    )
    assert isclose(result.liquidation.at_5x, 80500 * (1 + 1 / 5), rel_tol=1e-6)
    assert isclose(result.liquidation.at_10x, 80500 * (1 + 1 / 10), rel_tol=1e-6)


# ─── Funding ───


def test_funding_long_positive_rate_is_expense() -> None:
    """Long + funding > 0 → kullanıcı öder → signed pozitif."""
    result = compute_position(
        symbol="BTCUSDT",
        direction="long",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=79500.0,
        targets=[83500.0],
        max_leverage=10,
        funding_rate=0.0001,  # 0.01% per 8h
    )
    # Sign = +1 (long), rate > 0 → h24 > 0
    assert result.funding_costs.funding_rate == 0.0001
    assert result.funding_costs.h24 > 0
    # h24 = position * 0.0001 * 3
    expected = result.position_size_usd * 0.0001 * FUNDING_PERIODS_24H
    assert isclose(result.funding_costs.h24, expected, rel_tol=1e-6)


def test_funding_short_positive_rate_is_income() -> None:
    """Short + funding > 0 → kullanıcı kazanır → signed negatif."""
    result = compute_position(
        symbol="BTCUSDT",
        direction="short",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=81500.0,
        targets=[77500.0],
        max_leverage=10,
        funding_rate=0.0001,
    )
    assert result.funding_costs.h24 < 0
    assert result.funding_costs.h72 < 0
    assert result.funding_costs.w1 < 0


def test_funding_periods_consistency() -> None:
    """h72 = 3 * h24, w1 = 7 * h24."""
    result = compute_position(
        symbol="BTCUSDT",
        direction="long",
        balance=3000.0,
        base_risk_pct=2.0,
        entry=80500.0,
        stop=79500.0,
        targets=[83500.0],
        max_leverage=10,
        funding_rate=0.0001,
    )
    assert isclose(
        result.funding_costs.h72,
        result.funding_costs.h24 * (FUNDING_PERIODS_72H / FUNDING_PERIODS_24H),
        rel_tol=1e-6,
    )
    assert isclose(
        result.funding_costs.w1,
        result.funding_costs.h24 * (FUNDING_PERIODS_1W / FUNDING_PERIODS_24H),
        rel_tol=1e-6,
    )


# ─── Constants sanity ───


def test_constants() -> None:
    assert BTC_VOLATILITY_HIGH == 8.0
    assert BTC_VOLATILITY_MED == 5.0
    assert TP_WEIGHTS == (0.40, 0.35, 0.25)
    assert sum(TP_WEIGHTS) == 1.0
