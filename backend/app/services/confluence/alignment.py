"""Multi-TF Alignment — 6 TF için weighted final score.

Ağırlıklar (CLAUDE.md):
    15m  0.05   mikro timing
    1H   0.10
    4H   0.25   ana karar TF
    1D   0.30   makro yön (en yüksek)
    1W   0.20
    1M   0.10

Label thresholds:
    Strong:     |score| > 70
    Aligned:    |score| > 40
    Weak:       20 < |score| ≤ 40
    Conflicted: |score| ≤ 20  VEYA  yön çelişkisi (≥1 TF >+20 AND ≥1 TF <-20)
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.schemas.confluence import (
    AlignmentLabel,
    AlignmentResult,
    FinalConfluenceResult,
    TimeframeScore,
    TradeDirection,
)

ALIGNMENT_WEIGHTS: dict[str, float] = {
    "15m": 0.05,
    "1H": 0.10,
    "4H": 0.25,
    "1D": 0.30,
    "1W": 0.20,
    "1M": 0.10,
}

CONFLICT_DIRECTION_THRESHOLD = 20.0  # ±20 üstü = belirgin yön
STRONG_THRESHOLD = 70.0
ALIGNED_THRESHOLD = 40.0
WEAK_THRESHOLD = 20.0


def _detect_conflict(scores_by_tf: dict[str, FinalConfluenceResult]) -> bool:
    """≥1 TF >+20 AND ≥1 TF <-20 → conflicted (yön çelişkisi)."""
    has_long = any(s.final_score > CONFLICT_DIRECTION_THRESHOLD for s in scores_by_tf.values())
    has_short = any(s.final_score < -CONFLICT_DIRECTION_THRESHOLD for s in scores_by_tf.values())
    return has_long and has_short


def _label(weighted_score: float, is_conflicted: bool) -> AlignmentLabel:
    if is_conflicted:
        return "conflicted"
    abs_score = abs(weighted_score)
    if abs_score > STRONG_THRESHOLD:
        return "strong"
    if abs_score > ALIGNED_THRESHOLD:
        return "aligned"
    if abs_score > WEAK_THRESHOLD:
        return "weak"
    return "conflicted"


def _consistent_direction(
    scores_by_tf: dict[str, FinalConfluenceResult],
) -> TradeDirection | None:
    """Tüm TF'ler aynı yönlüyse o yönü dön; çelişki varsa None."""
    directions = {s.direction for s in scores_by_tf.values()}
    if len(directions) == 1:
        return next(iter(directions))
    return None


def compute_multi_tf_alignment(
    symbol: str,
    scores_by_tf: dict[str, FinalConfluenceResult],
) -> AlignmentResult:
    if not scores_by_tf:
        raise ValueError("Alignment hesabı için en az 1 TF gerekli")

    # Ağırlıklı toplam — sadece bilinen TF'leri kullan
    used_weight = 0.0
    weighted_sum = 0.0
    for tf, score_obj in scores_by_tf.items():
        if tf not in ALIGNMENT_WEIGHTS:
            continue
        w = ALIGNMENT_WEIGHTS[tf]
        weighted_sum += score_obj.final_score * w
        used_weight += w

    # Eksik TF varsa kalan ağırlığı normalize et
    if used_weight > 0 and used_weight < 1.0:
        weighted_sum = weighted_sum / used_weight
    weighted_sum = max(-100.0, min(100.0, weighted_sum))

    is_conflicted = _detect_conflict(scores_by_tf)
    label = _label(weighted_sum, is_conflicted)
    consistent = _consistent_direction(scores_by_tf)

    by_tf = [
        TimeframeScore(
            timeframe=tf,
            final_score=score_obj.final_score,
            label=score_obj.label,
            direction=score_obj.direction,
        )
        for tf, score_obj in scores_by_tf.items()
    ]
    # 15m → 1M sırasında dön
    order = {tf: i for i, tf in enumerate(ALIGNMENT_WEIGHTS.keys())}
    by_tf.sort(key=lambda x: order.get(x.timeframe, 99))

    return AlignmentResult(
        symbol=symbol,
        alignment_score=weighted_sum,
        label=label,
        consistent_direction=consistent,
        by_timeframe=by_tf,
        weights=dict(ALIGNMENT_WEIGHTS),
        computed_at=datetime.now(UTC),
    )
