"""Macro modifier — BTC/ALT/GOLD için golden testler."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.schemas.macro import (
    CryptoCapsSnapshot,
    FearGreedSnapshot,
    MacroSnapshot,
    MetricTrend,
    RegimeResult,
)
from app.services.confluence.macro_modifier import (
    MODIFIER_MAX,
    MODIFIER_MIN,
    REGIME_MODIFIER,
    compute_macro_modifier,
    symbol_type,
)


def _metric(
    *,
    current: float = 100.0,
    change_7d: float | None = 0.0,
) -> MetricTrend:
    return MetricTrend(
        current=current,
        change_24h_pct=0.0,
        change_7d_pct=change_7d,
        change_30d_pct=0.0,
        direction_24h="flat",
        direction_7d="flat",
        direction_30d="flat",
    )


def _snapshot(
    *,
    eth_btc_7d: float | None = 0.0,
    sp500_7d: float | None = 0.0,
    dxy_7d: float | None = 0.0,
    vix_level: float = 18.0,
    regime: str = "MIXED",
    fng_value: int = 50,
) -> MacroSnapshot:
    return MacroSnapshot(
        crypto_caps=CryptoCapsSnapshot(
            total=2.5e12, total2=1e12, total3=0.7e12,
            btc_dominance=55.0, eth_dominance=15.0,
        ),
        btc_market_cap=_metric(current=1.5e12, change_7d=0.0),
        eth_btc_ratio=_metric(current=0.029, change_7d=eth_btc_7d),
        dxy=_metric(current=98.0, change_7d=dxy_7d),
        sp500=_metric(current=7400.0, change_7d=sp500_7d),
        nasdaq=_metric(current=26000.0, change_7d=0.0),
        vix=_metric(current=vix_level, change_7d=0.0),
        us10y=_metric(current=4.3, change_7d=0.0),
        gold=_metric(current=4700.0, change_7d=0.0),
        fear_greed=FearGreedSnapshot(
            value=fng_value,
            classification="Neutral",
            timestamp="0",
        ),
        market_regime=RegimeResult(
            regime=regime,  # type: ignore[arg-type]
            label="test",
            triggers={},
        ),
        computed_at=datetime.now(UTC),
    )


# ─── symbol_type ───


def test_symbol_type_btc() -> None:
    assert symbol_type("BTCUSDT") == "btc"
    assert symbol_type("btcusdt") == "btc"


def test_symbol_type_gold() -> None:
    assert symbol_type("GOLD") == "commodity"


def test_symbol_type_altcoins() -> None:
    for s in ("ETHUSDT", "SOLUSDT", "DOGEUSDT", "PEPEUSDT", "LINKUSDT"):
        assert symbol_type(s) == "alt"


# ─── BTC modifier ───


def test_btc_modifier_ethbtc_inverse() -> None:
    """ETH/BTC -5% → BTC için +10."""
    snap = _snapshot(eth_btc_7d=-5.0)
    total, br = compute_macro_modifier("BTCUSDT", snap)
    assert br.eth_btc == pytest.approx(10.0)
    assert total == pytest.approx(10.0)


def test_btc_modifier_ethbtc_positive_negative_for_btc() -> None:
    """ETH/BTC +5% → BTC için -10."""
    snap = _snapshot(eth_btc_7d=5.0)
    total, br = compute_macro_modifier("BTCUSDT", snap)
    assert br.eth_btc == pytest.approx(-10.0)


def test_btc_modifier_dxy_negative_correlation() -> None:
    """DXY +3% → -6."""
    snap = _snapshot(dxy_7d=3.0)
    _, br = compute_macro_modifier("BTCUSDT", snap)
    assert br.dxy == pytest.approx(-6.0)


def test_btc_modifier_sp500_positive() -> None:
    snap = _snapshot(sp500_7d=4.0)
    _, br = compute_macro_modifier("BTCUSDT", snap)
    assert br.sp500 == pytest.approx(6.0)


def test_btc_modifier_vix_levels() -> None:
    # <15 → +5
    snap = _snapshot(vix_level=12.0)
    _, br = compute_macro_modifier("BTCUSDT", snap)
    assert br.vix == 5.0
    # 15-25 → 0
    snap = _snapshot(vix_level=20.0)
    _, br = compute_macro_modifier("BTCUSDT", snap)
    assert br.vix == 0.0
    # 25-30 → -5
    snap = _snapshot(vix_level=28.0)
    _, br = compute_macro_modifier("BTCUSDT", snap)
    assert br.vix == -5.0
    # >30 → -10
    snap = _snapshot(vix_level=35.0)
    _, br = compute_macro_modifier("BTCUSDT", snap)
    assert br.vix == -10.0


def test_btc_modifier_regime_field_is_none() -> None:
    snap = _snapshot(regime="ALT_BULL")
    _, br = compute_macro_modifier("BTCUSDT", snap)
    assert br.regime is None  # BTC için regime modifier yok


def test_btc_modifier_clamped_to_plus25() -> None:
    """Aşırı bullish kombinasyonu clamp ±25."""
    snap = _snapshot(eth_btc_7d=-10.0, sp500_7d=10.0, dxy_7d=-10.0, vix_level=10.0)
    total, _ = compute_macro_modifier("BTCUSDT", snap)
    assert total == MODIFIER_MAX  # +10 +10 +10 +5 = 35 → clamp 25


# ─── ALT modifier ───


def test_alt_modifier_ethbtc_direct() -> None:
    """ETH/BTC +5% → ALT için +10."""
    snap = _snapshot(eth_btc_7d=5.0)
    _, br = compute_macro_modifier("ETHUSDT", snap)
    assert br.eth_btc == pytest.approx(10.0)


def test_alt_modifier_dxy_dampened_07x() -> None:
    """DXY +3% → ALT için -6 * 0.7 = -4.2."""
    snap = _snapshot(dxy_7d=3.0)
    _, br = compute_macro_modifier("ETHUSDT", snap)
    assert br.dxy == pytest.approx(-4.2)


def test_alt_modifier_regime_alt_bull() -> None:
    snap = _snapshot(regime="ALT_BULL")
    _, br = compute_macro_modifier("ETHUSDT", snap)
    assert br.regime == 5.0


def test_alt_modifier_regime_alt_season_early() -> None:
    snap = _snapshot(regime="ALT_SEASON_EARLY")
    _, br = compute_macro_modifier("SOLUSDT", snap)
    assert br.regime == 10.0


def test_alt_modifier_regime_risk_off() -> None:
    snap = _snapshot(regime="RISK_OFF")
    _, br = compute_macro_modifier("LINKUSDT", snap)
    assert br.regime == -10.0


def test_alt_modifier_regime_btc_bull_negative_for_alt() -> None:
    snap = _snapshot(regime="BTC_BULL")
    _, br = compute_macro_modifier("ETHUSDT", snap)
    assert br.regime == -5.0


def test_alt_modifier_regime_mixed_zero() -> None:
    snap = _snapshot(regime="MIXED")
    _, br = compute_macro_modifier("ETHUSDT", snap)
    assert br.regime == 0.0


def test_alt_modifier_total3_is_none() -> None:
    snap = _snapshot()
    _, br = compute_macro_modifier("ETHUSDT", snap)
    assert br.total3 is None  # history yok


# ─── GOLD modifier ───


def test_gold_modifier_dxy_strong_negative() -> None:
    """DXY -3% → GOLD için +9 (3.0 çarpan)."""
    snap = _snapshot(dxy_7d=-3.0)
    total, br = compute_macro_modifier("GOLD", snap)
    assert br.dxy == pytest.approx(9.0)
    assert br.eth_btc is None
    assert br.sp500 is None
    assert br.regime is None


def test_gold_modifier_vix_safe_haven() -> None:
    """VIX >30 → GOLD için +10 (safe haven demand)."""
    snap = _snapshot(vix_level=35.0)
    _, br = compute_macro_modifier("GOLD", snap)
    assert br.vix == 10.0


def test_gold_modifier_low_vix_risk_on_negative() -> None:
    """VIX <15 → GOLD için -5 (kimse safe haven istemiyor)."""
    snap = _snapshot(vix_level=10.0)
    _, br = compute_macro_modifier("GOLD", snap)
    assert br.vix == -5.0


def test_gold_modifier_vix_mid_range() -> None:
    snap = _snapshot(vix_level=20.0)
    _, br = compute_macro_modifier("GOLD", snap)
    assert br.vix == 0.0


def test_gold_modifier_no_crypto_signals() -> None:
    """GOLD'un modifier'ı sadece DXY + VIX'e duyarlı."""
    snap = _snapshot(eth_btc_7d=10.0, sp500_7d=10.0, regime="ALT_BULL")
    total, br = compute_macro_modifier("GOLD", snap)
    # Sadece dxy=0 + vix=0 katkı → total = 0
    assert br.eth_btc is None
    assert br.sp500 is None
    assert br.regime is None
    assert total == 0.0


# ─── Clamp & general ───


def test_modifier_clamped_extremes() -> None:
    """Aşırı bearish ALT senaryosu — clamp -25."""
    snap = _snapshot(
        eth_btc_7d=-10.0, sp500_7d=-10.0, dxy_7d=10.0, vix_level=35.0, regime="RISK_OFF"
    )
    total, _ = compute_macro_modifier("ETHUSDT", snap)
    assert total == MODIFIER_MIN


def test_regime_modifier_table_has_all_5() -> None:
    assert set(REGIME_MODIFIER.keys()) == {
        "ALT_BULL", "BTC_BULL", "RISK_OFF", "ALT_SEASON_EARLY", "MIXED"
    }


def test_mixed_regime_modifier_small() -> None:
    """MIXED rejimde + nötr metrikler → modifier küçük (-5 .. +5)."""
    snap = _snapshot(eth_btc_7d=0.5, sp500_7d=0.5, dxy_7d=-0.5, vix_level=18.0, regime="MIXED")
    total, _ = compute_macro_modifier("BTCUSDT", snap)
    assert -5 <= total <= 5
