"""Final confluence — local + macro modifier compose.

final_score = clamp(local_score + macro_modifier, -100, +100)
label: 5 seviye (Adım 9'la aynı thresholds)
direction: long/short/neutral (Adım 9'la aynı thresholds)
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.schemas.confluence import (
    ConfluenceLabel,
    FinalConfluenceResult,
    LocalConfluenceResult,
    TradeDirection,
)
from app.schemas.macro import MacroSnapshot
from app.services.confluence.macro_modifier import (
    compute_macro_modifier,
    symbol_type,
)


def _label(score: float) -> ConfluenceLabel:
    if score > 60:
        return "strong_bullish"
    if score > 30:
        return "bullish"
    if score < -60:
        return "strong_bearish"
    if score < -30:
        return "bearish"
    return "neutral"


def _direction(score: float) -> TradeDirection:
    if score > 20:
        return "long"
    if score < -20:
        return "short"
    return "neutral"


def compute_final_confluence(
    local: LocalConfluenceResult,
    macro: MacroSnapshot,
) -> FinalConfluenceResult:
    modifier, breakdown = compute_macro_modifier(local.symbol, macro)
    final_score = max(-100.0, min(100.0, local.final_score + modifier))

    return FinalConfluenceResult(
        symbol=local.symbol,
        timeframe=local.timeframe,
        symbol_type=symbol_type(local.symbol),
        local_score=local.final_score,
        macro_modifier=modifier,
        final_score=final_score,
        label=_label(final_score),
        direction=_direction(final_score),
        components=local.components,
        macro_breakdown=breakdown,
        weights_applied=local.weights_applied,
        market_regime=macro.market_regime.regime,
        computed_at=datetime.now(UTC),
    )
