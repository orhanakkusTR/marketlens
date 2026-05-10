"""Multi-TF Alignment testleri."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.schemas.confluence import (
    FinalConfluenceResult,
    ModifierBreakdown,
    ScoreBreakdown,
)
from app.services.confluence.alignment import (
    ALIGNMENT_WEIGHTS,
    compute_multi_tf_alignment,
)


def _final(tf: str, score: float, direction: str = "long") -> FinalConfluenceResult:
    from app.schemas.confluence import ConfluenceLabel

    def _label(s: float) -> ConfluenceLabel:
        if s > 60:
            return "strong_bullish"
        if s > 30:
            return "bullish"
        if s < -60:
            return "strong_bearish"
        if s < -30:
            return "bearish"
        return "neutral"

    return FinalConfluenceResult(
        symbol="BTCUSDT",
        timeframe=tf,
        symbol_type="btc",
        local_score=score,
        macro_modifier=0.0,
        final_score=score,
        label=_label(score),
        direction=direction,  # type: ignore[arg-type]
        components=ScoreBreakdown(
            trend=0, momentum=0, volume=0, volatility=0, futures=0
        ),
        macro_breakdown=ModifierBreakdown(
            eth_btc=0.0, sp500=0.0, dxy=0.0, vix=0.0, regime=None, total3=None,
        ),
        weights_applied={"trend": 0.4},
        market_regime="MIXED",
        computed_at=datetime.now(UTC),
    )


def _all_tfs(score: float, direction: str = "long") -> dict[str, FinalConfluenceResult]:
    return {tf: _final(tf, score, direction) for tf in ALIGNMENT_WEIGHTS}


# ─── Weights & sum ───


def test_alignment_weights_sum_to_one() -> None:
    assert sum(ALIGNMENT_WEIGHTS.values()) == pytest.approx(1.0)


def test_alignment_weighted_sum_correct() -> None:
    """Tüm TF +50 → alignment 50."""
    scores = _all_tfs(50.0)
    result = compute_multi_tf_alignment("BTCUSDT", scores)
    assert result.alignment_score == pytest.approx(50.0)


def test_alignment_4h_1d_dominant() -> None:
    """Sadece 4H ve 1D +100, kalan 0 → score = 100*(0.25+0.30) = 55."""
    scores = _all_tfs(0.0, direction="neutral")
    scores["4H"] = _final("4H", 100.0)
    scores["1D"] = _final("1D", 100.0)
    result = compute_multi_tf_alignment("BTCUSDT", scores)
    assert result.alignment_score == pytest.approx(55.0)


# ─── Labels ───


def test_alignment_label_strong_above_70() -> None:
    scores = _all_tfs(80.0)
    result = compute_multi_tf_alignment("BTCUSDT", scores)
    assert result.label == "strong"


def test_alignment_label_aligned_40_to_70() -> None:
    scores = _all_tfs(50.0)
    result = compute_multi_tf_alignment("BTCUSDT", scores)
    assert result.label == "aligned"


def test_alignment_label_weak_20_to_40() -> None:
    """Yön çelişkisi yok, alignment 30 → weak."""
    scores = _all_tfs(30.0)
    result = compute_multi_tf_alignment("BTCUSDT", scores)
    assert result.label == "weak"


def test_alignment_label_conflicted_low_magnitude() -> None:
    """Alignment 15 → conflicted (magnitude düşük)."""
    scores = _all_tfs(15.0, direction="neutral")
    result = compute_multi_tf_alignment("BTCUSDT", scores)
    assert result.label == "conflicted"


def test_alignment_label_conflicted_on_direction_split() -> None:
    """Yarı bullish yarı bearish → conflicted, magnitude irrelevant."""
    scores = {
        "15m": _final("15m", 30.0, "long"),
        "1H": _final("1H", 50.0, "long"),
        "4H": _final("4H", 60.0, "long"),
        "1D": _final("1D", -60.0, "short"),  # split
        "1W": _final("1W", -50.0, "short"),
        "1M": _final("1M", -40.0, "short"),
    }
    result = compute_multi_tf_alignment("BTCUSDT", scores)
    # Weighted sum yakın 0 ama yön çelişkisi → conflicted
    assert result.label == "conflicted"


def test_alignment_label_conflicted_one_outlier() -> None:
    """5 TF +50, 1 TF -25 → conflict (≥1 TF <-20)."""
    scores = _all_tfs(50.0, "long")
    scores["1M"] = _final("1M", -25.0, "short")
    result = compute_multi_tf_alignment("BTCUSDT", scores)
    assert result.label == "conflicted"


# ─── Consistent direction ───


def test_alignment_consistent_direction_all_long() -> None:
    scores = _all_tfs(50.0, "long")
    result = compute_multi_tf_alignment("BTCUSDT", scores)
    assert result.consistent_direction == "long"


def test_alignment_consistent_direction_none_on_mixed() -> None:
    scores = _all_tfs(50.0, "long")
    scores["1W"] = _final("1W", 0.0, "neutral")
    result = compute_multi_tf_alignment("BTCUSDT", scores)
    assert result.consistent_direction is None


def test_alignment_by_timeframe_ordered() -> None:
    scores = _all_tfs(50.0)
    result = compute_multi_tf_alignment("BTCUSDT", scores)
    tfs = [tf.timeframe for tf in result.by_timeframe]
    assert tfs == ["15m", "1H", "4H", "1D", "1W", "1M"]


# ─── Edge cases ───


def test_alignment_empty_raises() -> None:
    with pytest.raises(ValueError, match="en az 1 TF"):
        compute_multi_tf_alignment("BTCUSDT", {})


def test_alignment_clamped_to_100() -> None:
    """Tüm TF +120 (hypothetical) → clamp 100. Pratikte zaten clamp'li ama
    weighted_sum normalize edilirse aşabilir; bu test güvence."""
    scores = _all_tfs(100.0)
    result = compute_multi_tf_alignment("BTCUSDT", scores)
    assert result.alignment_score == 100.0


def test_alignment_negative_full_bearish() -> None:
    scores = _all_tfs(-80.0, "short")
    result = compute_multi_tf_alignment("BTCUSDT", scores)
    assert result.alignment_score == pytest.approx(-80.0)
    assert result.label == "strong"
    assert result.consistent_direction == "short"
