"""Auto S/R Levels — round numbers + cluster + sources."""
from __future__ import annotations

from app.services.indicators.base import klines_to_dataframe
from app.services.indicators.fibonacci.auto_fib import compute_fibonacci
from app.services.indicators.levels.auto_sr import compute_levels
from app.services.indicators.levels.round_numbers import (
    _round_steps,
    round_levels_around,
)
from app.services.indicators.trend.market_structure import compute_market_structure
from app.services.indicators.volume.volume_profile import compute_volume_profile

from ._synthetic import zigzag_uptrend


# ─── Round numbers ───


def test_round_steps_btc_range() -> None:
    """BTC ~80k → minor=$1k, major=$5k."""
    minor, major = _round_steps(80_000)
    assert minor == 1_000.0
    assert major == 5_000.0


def test_round_steps_eth_range() -> None:
    """ETH ~3500 → minor=$100, major=$500."""
    minor, major = _round_steps(3_500)
    assert minor == 100.0
    assert major == 500.0


def test_round_steps_sol_range() -> None:
    """SOL ~200 → minor=$10, major=$50."""
    minor, major = _round_steps(200)
    assert minor == 10.0
    assert major == 50.0


def test_round_steps_doge_range() -> None:
    """DOGE ~0.5 → minor=$0.01, major=$0.05."""
    minor, major = _round_steps(0.5)
    assert minor == 0.01
    assert major == 0.05


def test_round_steps_pepe_micro() -> None:
    """PEPE 0.00001234 → 5 anlamlı basamak (1e-9 minor, 5e-9 major)."""
    minor, major = _round_steps(0.00001234)
    # log10(0.00001234) ≈ -4.91 → digits=-5, base=10^-9=1e-9
    assert abs(minor - 1e-9) < 1e-15
    assert abs(major - 5e-9) < 1e-15


def test_round_levels_around_btc() -> None:
    """BTC $80,000 etrafında ±5% (76k-84k) round'lar."""
    levels = round_levels_around(80_000, range_pct=5.0)
    prices = {p for p, _ in levels}
    # Major'lar $5k (75k, 80k, 85k → 80k major; 75k ve 85k sınırda olabilir)
    # Minor'lar $1k
    assert 80_000.0 in prices  # major
    assert 81_000.0 in prices or 81_000.0 in {round(p, 2) for p in prices}


def test_round_levels_kind_split() -> None:
    levels = round_levels_around(80_000, range_pct=5.0)
    # 80k = major, 81k/82k/... = minor
    kind_at_80k = next(k for p, k in levels if abs(p - 80_000) < 1e-6)
    assert kind_at_80k == "round_major"


def test_round_levels_zero_price_safe() -> None:
    levels = round_levels_around(0.0, range_pct=5.0)
    assert levels == []


# ─── Auto S/R compute_levels integration ───


def test_compute_levels_returns_supports_and_resistances() -> None:
    klines = zigzag_uptrend(cycles=4, swing_size=20)
    df = klines_to_dataframe(klines)
    ms = compute_market_structure(df)
    fib = compute_fibonacci(df)
    vp = compute_volume_profile(df, "4H")

    result = compute_levels(df, ms, fib, vp, top_n=5)
    assert len(result.supports) <= 5
    assert len(result.resistances) <= 5
    # Tüm supportlar < current_price
    for s in result.supports:
        assert s.price < result.current_price
    # Tüm resistance'lar >= current_price
    for r in result.resistances:
        assert r.price >= result.current_price
    # Her level en az 1 source'a sahip
    for lv in result.supports + result.resistances:
        assert len(lv.sources) >= 1
        assert lv.strength_score > 0


def test_compute_levels_supports_sorted_by_proximity() -> None:
    klines = zigzag_uptrend(cycles=4, swing_size=20)
    df = klines_to_dataframe(klines)
    ms = compute_market_structure(df)
    fib = compute_fibonacci(df)
    vp = compute_volume_profile(df, "4H")
    result = compute_levels(df, ms, fib, vp)
    # Support'lar fiyata yakından uzağa
    if len(result.supports) > 1:
        distances = [result.current_price - s.price for s in result.supports]
        assert distances == sorted(distances)
