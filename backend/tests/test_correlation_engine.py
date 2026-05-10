"""Korelasyon engine: categorize + log returns + helpers."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from app.data.symbols_meta import ALL_SYMBOLS, SECTORS, sector_of
from app.services.correlation.engine import (
    _build_returns_dataframe,
    _categorize,
    _compute_log_returns,
    _series_to_aligned_close_dict,
)


# ─── categorize ───


def test_categorize_strong_positive() -> None:
    cat, sign = _categorize(0.85)
    assert cat == "strong"
    assert sign == "positive"


def test_categorize_strong_negative() -> None:
    cat, sign = _categorize(-0.85)
    assert cat == "strong"
    assert sign == "negative"


def test_categorize_moderate_boundary_07() -> None:
    """abs(r) > 0.7 → strong; abs(r) == 0.7 → moderate (sınır içe)."""
    assert _categorize(0.7)[0] == "moderate"
    assert _categorize(0.71)[0] == "strong"
    assert _categorize(-0.7)[0] == "moderate"


def test_categorize_moderate_range() -> None:
    assert _categorize(0.5)[0] == "moderate"
    assert _categorize(0.4)[0] == "moderate"


def test_categorize_weak_range() -> None:
    assert _categorize(0.3)[0] == "weak"
    assert _categorize(0.2)[0] == "weak"


def test_categorize_decoupled() -> None:
    assert _categorize(0.15)[0] == "decoupled"
    assert _categorize(-0.1)[0] == "decoupled"
    assert _categorize(0.0)[0] == "decoupled"


def test_categorize_sign_zero_is_positive() -> None:
    """r = 0 → positive (>= 0 mantığı)."""
    _, sign = _categorize(0.0)
    assert sign == "positive"


# ─── log returns ───


def test_log_returns_basic() -> None:
    closes = [100.0, 105.0, 102.0]
    returns = _compute_log_returns(closes)
    assert len(returns) == 2
    assert returns[0] == pytest.approx(math.log(105 / 100))
    assert returns[1] == pytest.approx(math.log(102 / 105))


def test_log_returns_handle_zero() -> None:
    closes = [100.0, 0.0, 105.0]
    returns = _compute_log_returns(closes)
    # 0 → NaN
    assert np.isnan(returns[0])
    # 0 → 105 ise yine NaN (önceki 0)
    assert np.isnan(returns[1])


def test_log_returns_short_series() -> None:
    assert _compute_log_returns([100.0]) == []
    assert _compute_log_returns([]) == []


# ─── alignment + DataFrame ───


def test_aligned_takes_last_n_days() -> None:
    series = {
        "BTC": [(i, 100.0 + i) for i in range(40)],
        "ETH": [(i, 50.0 + i * 0.5) for i in range(35)],
    }
    aligned = _series_to_aligned_close_dict(series, days=30)
    assert "BTC" in aligned
    assert "ETH" in aligned
    assert len(aligned["BTC"]) == 30
    assert len(aligned["ETH"]) == 30


def test_aligned_drops_too_short_series() -> None:
    series = {
        "BTC": [(i, 100.0 + i) for i in range(40)],
        "BAD": [(0, 100.0)],  # 1 bar — atlanır
    }
    aligned = _series_to_aligned_close_dict(series, days=30)
    assert "BTC" in aligned
    assert "BAD" not in aligned


def test_returns_dataframe_perfectly_correlated() -> None:
    """İki birebir aynı seri → corr = 1.0."""
    aligned = {
        "A": [100.0 + i for i in range(31)],
        "B": [100.0 + i for i in range(31)],
    }
    df = _build_returns_dataframe(aligned)
    corr = df.corr()
    assert corr.loc["A", "B"] == pytest.approx(1.0)


def test_returns_dataframe_inverse_correlated() -> None:
    """A random walk, B = -A → returns ters → corr ≈ -1."""
    rng = np.random.default_rng(0)
    base = 100.0 + rng.normal(0, 2, 31).cumsum()
    aligned = {
        "A": base.tolist(),
        # B'nin günlük return'leri A'nın tam tersi olacak şekilde inşa
        "B": (100.0 - (base - 100.0)).tolist(),
    }
    df = _build_returns_dataframe(aligned)
    corr = df.corr()
    # Mükemmel -1 değil çünkü log nonlinear; ama belirgin negatif (<-0.8) olmalı
    assert corr.loc["A", "B"] < -0.8


def test_returns_dataframe_uncorrelated_random() -> None:
    """Random iki seri → corr |r| < 0.5 (yüksek ihtimal)."""
    rng = np.random.default_rng(42)
    aligned = {
        "A": (100 + rng.normal(0, 1, 31).cumsum()).tolist(),
        "B": (100 + rng.normal(0, 1, 31).cumsum()).tolist(),
    }
    df = _build_returns_dataframe(aligned)
    corr = df.corr()
    assert abs(corr.loc["A", "B"]) < 0.5


# ─── Sectors ───


def test_all_27_symbols_have_sector() -> None:
    assert len(ALL_SYMBOLS) == 27
    for sym in ALL_SYMBOLS:
        assert sym in SECTORS
        assert sector_of(sym) is not None


def test_sector_groups_canonical() -> None:
    """CLAUDE.md mapping doğru — L1 11 sembol, L2 3, vb."""
    from collections import Counter

    counts = Counter(SECTORS.values())
    # L1: 11 (BTC, ETH, SOL, BNB, AVAX, ADA, DOT, NEAR, APT, SUI, SEI)
    assert counts["L1"] == 11
    # L2: 3 (ARB, OP, POL)
    assert counts["L2"] == 3
    # DeFi: 4 (UNI, AAVE, LDO, INJ)
    assert counts["DeFi"] == 4
    # Meme: 5 (DOGE, SHIB, PEPE, WIF, BONK)
    assert counts["Meme"] == 5
    # Other: 3 (XRP, LINK, ATOM)
    assert counts["Other"] == 3
    # Commodity: 1 (GOLD)
    assert counts["Commodity"] == 1


def test_sector_of_unknown_returns_none() -> None:
    assert sector_of("FOOUSDT") is None
