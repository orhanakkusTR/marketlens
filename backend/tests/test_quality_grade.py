"""Setup quality grade hesabı ve modifier mantığı."""
from __future__ import annotations

import pytest

from app.services.quality.setup_quality import (
    GRADE_ORDER,
    _apply_modifiers,
    _grade_from_score,
)


# ─── Base grade from score ───


def test_grade_a_from_score_90_plus() -> None:
    assert _grade_from_score(95) == "A"
    assert _grade_from_score(90) == "A"


def test_grade_b_from_score_70_to_89() -> None:
    assert _grade_from_score(70) == "B"
    assert _grade_from_score(89) == "B"


def test_grade_c_from_score_50_to_69() -> None:
    assert _grade_from_score(50) == "C"
    assert _grade_from_score(69) == "C"


def test_grade_d_from_score_below_50() -> None:
    assert _grade_from_score(0) == "D"
    assert _grade_from_score(49) == "D"


def test_grade_order_canonical() -> None:
    assert GRADE_ORDER == ["D", "C", "B", "A"]


# ─── Modifiers ───


def test_modifier_neutral_direction_overrides_to_no_trade() -> None:
    grade, mods = _apply_modifiers(
        "A",
        direction="neutral",
        macro_modifier=10.0,
        counter_trend_high_count=0,
        trade_quality_verdict="EXCELLENT",
        no_trade_blocking=False,
        no_trade_warning_count=0,
    )
    assert grade == "NO_TRADE"


def test_modifier_avoid_overrides_to_no_trade() -> None:
    grade, mods = _apply_modifiers(
        "A",
        direction="long",
        macro_modifier=0.0,
        counter_trend_high_count=0,
        trade_quality_verdict="AVOID",
        no_trade_blocking=False,
        no_trade_warning_count=0,
    )
    assert grade == "NO_TRADE"
    assert mods["trade_quality_avoid"] == -99


def test_modifier_macro_strong_positive_upgrades() -> None:
    grade, mods = _apply_modifiers(
        "B",
        direction="long",
        macro_modifier=20.0,  # > 15
        counter_trend_high_count=0,
        trade_quality_verdict="GOOD",
        no_trade_blocking=False,
        no_trade_warning_count=0,
    )
    assert grade == "A"
    assert mods["macro_strong_positive"] == 1


def test_modifier_macro_strong_negative_downgrades() -> None:
    grade, mods = _apply_modifiers(
        "B",
        direction="long",
        macro_modifier=-20.0,
        counter_trend_high_count=0,
        trade_quality_verdict="GOOD",
        no_trade_blocking=False,
        no_trade_warning_count=0,
    )
    assert grade == "C"
    assert mods["macro_strong_negative"] == -1


def test_modifier_counter_trend_2plus_downgrades() -> None:
    grade, mods = _apply_modifiers(
        "B",
        direction="long",
        macro_modifier=0.0,
        counter_trend_high_count=2,
        trade_quality_verdict="GOOD",
        no_trade_blocking=False,
        no_trade_warning_count=0,
    )
    assert grade == "C"
    assert mods["counter_trend"] == -1


def test_modifier_quality_excellent_upgrades() -> None:
    grade, mods = _apply_modifiers(
        "C",
        direction="long",
        macro_modifier=0.0,
        counter_trend_high_count=0,
        trade_quality_verdict="EXCELLENT",
        no_trade_blocking=False,
        no_trade_warning_count=0,
    )
    assert grade == "B"


def test_modifier_quality_weak_downgrades() -> None:
    grade, mods = _apply_modifiers(
        "B",
        direction="long",
        macro_modifier=0.0,
        counter_trend_high_count=0,
        trade_quality_verdict="WEAK",
        no_trade_blocking=False,
        no_trade_warning_count=0,
    )
    assert grade == "C"


def test_modifier_clamped_at_a_top() -> None:
    """A + macro_pos + quality_excellent → A (clamp, +2 olamaz)."""
    grade, mods = _apply_modifiers(
        "A",
        direction="long",
        macro_modifier=20.0,
        counter_trend_high_count=0,
        trade_quality_verdict="EXCELLENT",
        no_trade_blocking=False,
        no_trade_warning_count=0,
    )
    assert grade == "A"


def test_modifier_clamped_at_d_bottom() -> None:
    """D + macro_neg + counter + weak → D (clamp)."""
    grade, mods = _apply_modifiers(
        "D",
        direction="long",
        macro_modifier=-20.0,
        counter_trend_high_count=2,
        trade_quality_verdict="WEAK",
        no_trade_blocking=False,
        no_trade_warning_count=0,
    )
    assert grade == "D"


def test_modifier_combined_offsetting() -> None:
    """macro +1 + quality_weak -1 = net 0 → B kalır."""
    grade, mods = _apply_modifiers(
        "B",
        direction="long",
        macro_modifier=20.0,
        counter_trend_high_count=0,
        trade_quality_verdict="WEAK",
        no_trade_blocking=False,
        no_trade_warning_count=0,
    )
    assert grade == "B"
    assert mods["macro_strong_positive"] == 1
    assert mods["trade_quality_weak"] == -1


# ─── No-Trade Zone modifiers (Adım 14) ───


def test_modifier_no_trade_blocking_overrides() -> None:
    """≥1 blocking zone → NO_TRADE hard override."""
    grade, mods = _apply_modifiers(
        "A",
        direction="long",
        macro_modifier=20.0,
        counter_trend_high_count=0,
        trade_quality_verdict="EXCELLENT",
        no_trade_blocking=True,
        no_trade_warning_count=0,
    )
    assert grade == "NO_TRADE"
    assert mods["no_trade_zone_blocking"] == -99


def test_modifier_no_trade_warning_downgrades_one() -> None:
    """≥1 warning zone → grade -1."""
    grade, mods = _apply_modifiers(
        "B",
        direction="long",
        macro_modifier=0.0,
        counter_trend_high_count=0,
        trade_quality_verdict="GOOD",
        no_trade_blocking=False,
        no_trade_warning_count=1,
    )
    assert grade == "C"
    assert mods["no_trade_zone_warning"] == -1


def test_modifier_no_trade_blocking_takes_precedence_over_avoid() -> None:
    """Hard override hierarchy: AVOID önce sıraya gelir; ama ikisi de NO_TRADE üretir."""
    grade, mods = _apply_modifiers(
        "A",
        direction="long",
        macro_modifier=0.0,
        counter_trend_high_count=0,
        trade_quality_verdict="AVOID",
        no_trade_blocking=True,
        no_trade_warning_count=0,
    )
    assert grade == "NO_TRADE"


def test_modifier_no_trade_warning_combines_with_others() -> None:
    """Macro +1 + no_trade warning -1 = net 0 → A kalır (clamp final)."""
    grade, mods = _apply_modifiers(
        "A",
        direction="long",
        macro_modifier=20.0,
        counter_trend_high_count=0,
        trade_quality_verdict="GOOD",
        no_trade_blocking=False,
        no_trade_warning_count=2,
    )
    # idx: A=3 → +1 (macro) =4 → -1 (no_trade) =3 → clamp 3 → A
    assert grade == "A"
    assert mods["no_trade_zone_warning"] == -1
    assert mods["macro_strong_positive"] == 1
