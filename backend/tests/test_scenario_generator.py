"""Scenario Generator unit testleri.

Stop/TP selection, cluster prevention, fallback, R/R weighted.
"""
from __future__ import annotations

from math import isclose

import pytest

from app.schemas.indicators import LevelEntry, LevelsResult
from app.services.analysis.scenario_generator import (
    ENTRY_BAND_HALF_ATR,
    STOP_BUFFER_ATR,
    STOP_FALLBACK_ATR_MULTIPLIER,
    STOP_LEVEL_MAX_DISTANCE_ATR,
    STOP_LEVEL_MIN_DISTANCE_ATR,
    TP_CLUSTER_MIN_GAP_ATR,
    TP_FALLBACK_ATR_MULTIPLIERS,
    TP_RR_MIN,
    TP_WEIGHTS,
    generate_scenario,
)


def _levels(
    *,
    current_price: float = 80500.0,
    supports: list[float] | None = None,
    resistances: list[float] | None = None,
) -> LevelsResult:
    return LevelsResult(
        current_price=current_price,
        supports=[
            LevelEntry(
                price=p, kind="support", sources=["pivot_low"],
                confluence_count=1, strength_score=1.0,
            ) for p in (supports or [])
        ],
        resistances=[
            LevelEntry(
                price=p, kind="resistance", sources=["pivot_high"],
                confluence_count=1, strength_score=1.0,
            ) for p in (resistances or [])
        ],
    )


# ─── Direction ───


def test_neutral_returns_none() -> None:
    result = generate_scenario(
        symbol="BTCUSDT", timeframe="4H", direction="neutral",
        current_price=80500, atr=500,
        levels=_levels(supports=[79500], resistances=[81500]),
        final_confluence=20.0,
    )
    assert result is None


def test_zero_atr_returns_none() -> None:
    result = generate_scenario(
        symbol="BTCUSDT", timeframe="4H", direction="long",
        current_price=80500, atr=0,
        levels=_levels(supports=[79500], resistances=[81500]),
        final_confluence=50.0,
    )
    assert result is None


# ─── Long scenario ───


def test_long_entry_band() -> None:
    """Entry band = current_price ± 0.3 ATR."""
    result = generate_scenario(
        symbol="BTCUSDT", timeframe="4H", direction="long",
        current_price=80500, atr=500,
        levels=_levels(supports=[79500], resistances=[83500]),
        final_confluence=50.0,
    )
    assert result is not None
    assert result.entry.mid == 80500
    assert isclose(result.entry.low, 80500 - 0.3 * 500, rel_tol=1e-6)
    assert isclose(result.entry.high, 80500 + 0.3 * 500, rel_tol=1e-6)


def test_long_stop_from_support_with_buffer() -> None:
    """Long stop = support - 0.5 ATR buffer; level distance 0.5-3 ATR aralığında."""
    # support 79500, ATR 500 → distance = 1000/500 = 2 ATR (aralık içinde)
    result = generate_scenario(
        symbol="BTCUSDT", timeframe="4H", direction="long",
        current_price=80500, atr=500,
        levels=_levels(supports=[79500], resistances=[83500]),
        final_confluence=50.0,
    )
    assert result is not None
    # stop = 79500 - 0.5*500 = 79250
    assert isclose(result.stop.price, 79250, rel_tol=1e-6)
    assert "support" in result.stop.source.lower()


def test_long_stop_skips_too_close_level() -> None:
    """Level < 0.5 ATR → atla, bir sonrakini al."""
    # supports: 80400 (0.2 ATR, çok yakın), 79500 (2 ATR, uygun)
    result = generate_scenario(
        symbol="BTCUSDT", timeframe="4H", direction="long",
        current_price=80500, atr=500,
        levels=_levels(supports=[80400, 79500], resistances=[83500]),
        final_confluence=50.0,
    )
    assert result is not None
    # 79500 - 0.5*500 = 79250 (80400 atlandı)
    assert isclose(result.stop.price, 79250, rel_tol=1e-6)


def test_long_stop_fallback_when_level_too_far() -> None:
    """Tüm levels > 3 ATR → ATR×1.5 fallback."""
    # support 78000, distance = 2500/500 = 5 ATR (uzak)
    result = generate_scenario(
        symbol="BTCUSDT", timeframe="4H", direction="long",
        current_price=80500, atr=500,
        levels=_levels(supports=[78000], resistances=[83500]),
        final_confluence=50.0,
    )
    assert result is not None
    # fallback = 80500 - 1.5*500 = 79750
    assert isclose(result.stop.price, 79750, rel_tol=1e-6)
    assert "fallback" in result.stop.source.lower()


def test_long_stop_fallback_when_no_supports() -> None:
    """Hiç support yok → fallback."""
    result = generate_scenario(
        symbol="BTCUSDT", timeframe="4H", direction="long",
        current_price=80500, atr=500,
        levels=_levels(supports=[], resistances=[83500]),
        final_confluence=50.0,
    )
    assert result is not None
    assert "fallback" in result.stop.source.lower()


def test_long_targets_from_resistances() -> None:
    """Long TP'ler resistance'lardan."""
    # support 79500 (stop 79250); resistances 81500, 83500, 86500
    result = generate_scenario(
        symbol="BTCUSDT", timeframe="4H", direction="long",
        current_price=80500, atr=500,
        levels=_levels(
            supports=[79500],
            resistances=[81500, 83500, 86500],
        ),
        final_confluence=50.0,
    )
    assert result is not None
    assert len(result.targets) == 3
    # Hepsi current price üstünde
    assert all(t.price > 80500 for t in result.targets)
    # Sıralı artarak
    assert result.targets[0].price < result.targets[1].price < result.targets[2].price


def test_long_target_cluster_prevention() -> None:
    """3 yakın resistance → sadece 1'i seçilir, kalanı fallback."""
    # ATR 500 → cluster gap 250. Resistance'lar 81000, 81100, 81200 (cluster)
    result = generate_scenario(
        symbol="BTCUSDT", timeframe="4H", direction="long",
        current_price=80500, atr=500,
        levels=_levels(
            supports=[79500],
            resistances=[81000, 81100, 81200],
        ),
        final_confluence=50.0,
    )
    assert result is not None
    # En az 1 fallback olmalı (cluster'dan 2 atılır)
    fallback_count = sum(1 for t in result.targets if "fallback" in t.source.lower())
    assert fallback_count >= 1


def test_long_targets_fallback_when_no_resistances() -> None:
    """Hiç resistance yok → 3 ATR fallback."""
    result = generate_scenario(
        symbol="BTCUSDT", timeframe="4H", direction="long",
        current_price=80500, atr=500,
        levels=_levels(supports=[79500], resistances=[]),
        final_confluence=50.0,
    )
    assert result is not None
    assert len(result.targets) == 3
    # Fallback: ATR×2/4/6 → +1000, +2000, +3000
    assert all("fallback" in t.source.lower() for t in result.targets)


def test_long_targets_filter_rr_below_1() -> None:
    """R/R < 1.0 → skip."""
    # stop 79250 (risk 1250). Resistance 80700 (reward 200) → R/R 0.16, skip
    # Resistance 83000 (reward 2500) → R/R 2.0, OK
    result = generate_scenario(
        symbol="BTCUSDT", timeframe="4H", direction="long",
        current_price=80500, atr=500,
        levels=_levels(
            supports=[79500],
            resistances=[80700, 83000],
        ),
        final_confluence=50.0,
    )
    assert result is not None
    # 80700 atılmış olmalı
    selected_prices = [t.price for t in result.targets]
    assert 80700 not in selected_prices


# ─── Short scenario ───


def test_short_stop_from_resistance_with_buffer() -> None:
    # resistance 81500, ATR 500 → distance 1000/500=2 ATR
    result = generate_scenario(
        symbol="BTCUSDT", timeframe="4H", direction="short",
        current_price=80500, atr=500,
        levels=_levels(supports=[79500], resistances=[81500]),
        final_confluence=-50.0,
    )
    assert result is not None
    # stop = 81500 + 0.5*500 = 81750
    assert isclose(result.stop.price, 81750, rel_tol=1e-6)
    assert "resistance" in result.stop.source.lower()


def test_short_targets_from_supports() -> None:
    result = generate_scenario(
        symbol="BTCUSDT", timeframe="4H", direction="short",
        current_price=80500, atr=500,
        levels=_levels(
            supports=[79500, 77500, 75500],
            resistances=[81500],
        ),
        final_confluence=-50.0,
    )
    assert result is not None
    assert len(result.targets) == 3
    assert all(t.price < 80500 for t in result.targets)
    # TP1 en yakın, TP3 en uzak
    assert result.targets[0].price > result.targets[1].price > result.targets[2].price


# ─── R/R weighted ───


def test_rr_weighted_3_targets() -> None:
    """3 TP: weighted = 0.40*tp1 + 0.35*tp2 + 0.25*tp3."""
    # stop 79250 (risk 1250)
    # tp1 82750 (reward 2250 → R/R 1.8)
    # tp2 84000 (reward 3500 → R/R 2.8)
    # tp3 85250 (reward 4750 → R/R 3.8)
    result = generate_scenario(
        symbol="BTCUSDT", timeframe="4H", direction="long",
        current_price=80500, atr=500,
        levels=_levels(
            supports=[79500],
            resistances=[82750, 84000, 85250],
        ),
        final_confluence=50.0,
    )
    assert result is not None
    assert result.rr_weighted is not None
    rrs = [t.rr for t in result.targets]
    expected = sum(rr * w for rr, w in zip(rrs, TP_WEIGHTS))
    assert isclose(result.rr_weighted, expected, rel_tol=1e-6)


def test_rr_weighted_with_fallback() -> None:
    """Hiç level yok → tüm TP'ler fallback ama weighted yine de hesaplanır."""
    result = generate_scenario(
        symbol="BTCUSDT", timeframe="4H", direction="long",
        current_price=80500, atr=500,
        levels=_levels(supports=[], resistances=[]),
        final_confluence=50.0,
    )
    assert result is not None
    assert result.rr_weighted is not None
    assert result.rr_weighted > 0


# ─── Reasoning ───


def test_reasoning_includes_direction_and_levels() -> None:
    result = generate_scenario(
        symbol="BTCUSDT", timeframe="4H", direction="long",
        current_price=80500, atr=500,
        levels=_levels(supports=[79500], resistances=[83500]),
        final_confluence=50.0,
    )
    assert result is not None
    assert "Long" in result.reasoning
    assert "TP1" in result.reasoning
    assert "Entry" in result.reasoning


# ─── Constants sanity ───


def test_constants() -> None:
    assert ENTRY_BAND_HALF_ATR == 0.3
    assert STOP_BUFFER_ATR == 0.5
    assert STOP_LEVEL_MIN_DISTANCE_ATR == 0.5
    assert STOP_LEVEL_MAX_DISTANCE_ATR == 3.0
    assert STOP_FALLBACK_ATR_MULTIPLIER == 1.5
    assert TP_CLUSTER_MIN_GAP_ATR == 0.5
    assert TP_RR_MIN == 1.0
    assert TP_FALLBACK_ATR_MULTIPLIERS == (2, 4, 6)
    assert TP_WEIGHTS == (0.40, 0.35, 0.25)
    assert sum(TP_WEIGHTS) == 1.0
