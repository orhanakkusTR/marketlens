"""Setup Quality Engine — Adım 13 ana orchestrator.

Base Score (0-90 MVP, 100 hedef):
  Multi-TF alignment Strong          +20
  4H + 1D aynı yönde                 +20
  Market structure temiz             +10
  R:R ≥ 3                            +10  (Adım 16'da gerçek hesap; MVP'de 0)
  ATR normal (0.5-5%)                +10
  Funding ekstrem değil              +5
  Yakın major event yok              +5   (calendar future; MVP default +5)
  Macro modifier > 0                 +10
  Korelasyon riski düşük             +5   (open positions future; MVP +5)
  Time-of-day uygun                  +5   (Adım 14 future; MVP +5)

Base grade: A 90+, B 70+, C 50+, D <50.

Modifier'lar (final grade):
  direction == "neutral"             → NO_TRADE (erken çıkış)
  trade_quality.verdict == "AVOID"   → NO_TRADE (hard override)
  macro_modifier > +15               → grade +1
  macro_modifier < -15               → grade -1
  ≥2 high-severity counter-trend     → grade -1
  trade_quality EXCELLENT            → grade +1
  trade_quality WEAK                 → grade -1
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cached_call
from app.core.logging import get_logger
from app.data.binance_spot import TF_TO_INTERVAL, TF_TTL
from app.db.session import AsyncSessionLocal
from app.schemas.confluence import AlignmentResult, FinalConfluenceResult
from app.schemas.indicators import IndicatorBundle
from app.schemas.macro import MacroSnapshot
from app.schemas.setup_quality import (
    SetupFactor,
    SetupGrade,
    SetupQualityResult,
)
from app.services.indicators.base import klines_to_dataframe
from app.services.indicators.engine import indicator_engine
from app.services.macro.context import macro_service
from app.services.quality.confidence_engine import confidence_engine
from app.services.quality.counter_trend import counter_trend_detector
from app.services.quality.trade_quality_filter import trade_quality_filter

logger = get_logger(__name__)

CACHE_TTL = 300  # 5dk

GRADE_ORDER: list[SetupGrade] = ["D", "C", "B", "A"]


def _compute_base_factors(
    final: FinalConfluenceResult,
    alignment: AlignmentResult,
    bundle: IndicatorBundle,
) -> tuple[int, list[SetupFactor]]:
    """10 faktör üzerinden 0-100 puan + faktör listesi."""
    factors: list[SetupFactor] = []
    score = 0

    # 1. Multi-TF alignment Strong (+20)
    align_strong = alignment.label == "strong"
    if align_strong:
        score += 20
    factors.append(
        SetupFactor(
            name="Multi-TF alignment strong",
            passed=align_strong,
            points=20 if align_strong else 0,
            note=f"Alignment: {alignment.label} ({alignment.alignment_score:+.1f})",
        )
    )

    # 2. 4H + 1D aynı yönde (+20)
    h4 = next((t for t in alignment.by_timeframe if t.timeframe == "4H"), None)
    d1 = next((t for t in alignment.by_timeframe if t.timeframe == "1D"), None)
    same_dir = (
        h4 is not None and d1 is not None and h4.direction == d1.direction
        and h4.direction != "neutral"
    )
    if same_dir:
        score += 20
    factors.append(
        SetupFactor(
            name="4H + 1D aynı yönde",
            passed=same_dir,
            points=20 if same_dir else 0,
            note=(
                f"4H {h4.direction if h4 else '?'} / 1D {d1.direction if d1 else '?'}"
            ),
        )
    )

    # 3. Market structure temiz (+10)
    if bundle.trend is not None:
        struct = bundle.trend.market_structure.structure
        struct_clean = struct in ("uptrend", "downtrend")
    else:
        struct = "ranging"
        struct_clean = False
    if struct_clean:
        score += 10
    factors.append(
        SetupFactor(
            name="Market structure temiz",
            passed=struct_clean,
            points=10 if struct_clean else 0,
            note=f"Structure: {struct}",
        )
    )

    # 4. R:R ≥ 3 (+10) — Adım 16'da gerçek hesap
    rr_passed = False  # MVP: scenario yok, 0 puan
    factors.append(
        SetupFactor(
            name="R:R ≥ 3",
            passed=rr_passed,
            points=0,
            note="Future adımda gerçek hesap (R:R: Adım 16, scenario engine)",
        )
    )

    # 5. ATR normal (+10): 0.5% < ATR < 5%
    if bundle.volatility is not None:
        atr_pct = bundle.volatility.atr.value_pct
        atr_passed = 0.5 < atr_pct < 5.0
    else:
        atr_pct = 0.0
        atr_passed = False
    if atr_passed:
        score += 10
    factors.append(
        SetupFactor(
            name="ATR normal",
            passed=atr_passed,
            points=10 if atr_passed else 0,
            note=f"ATR %{atr_pct:.2f} (aralık: 0.5-5%)",
        )
    )

    # 6. Funding ekstrem değil (+5)
    if bundle.futures is not None:
        funding_extreme = bundle.futures.funding.extreme
        funding_ok = not funding_extreme
    else:
        funding_ok = True  # GOLD vs.
    if funding_ok:
        score += 5
    factors.append(
        SetupFactor(
            name="Funding ekstrem değil",
            passed=funding_ok,
            points=5 if funding_ok else 0,
            note=(
                "GOLD/no futures" if bundle.futures is None
                else f"Funding {bundle.futures.funding.current_rate * 100:+.4f}%"
            ),
        )
    )

    # 7. Yakın major event yok (+5) — calendar future
    event_ok = True  # MVP default
    score += 5
    factors.append(
        SetupFactor(
            name="Yakın major event yok",
            passed=event_ok,
            points=5,
            note="Future adımda gerçek hesap (ekonomik takvim entegrasyonu future)",
        )
    )

    # 8. Macro modifier > 0 (+10)
    macro_pos = final.macro_modifier > 0
    if macro_pos:
        score += 10
    factors.append(
        SetupFactor(
            name="Macro modifier pozitif",
            passed=macro_pos,
            points=10 if macro_pos else 0,
            note=f"Macro modifier: {final.macro_modifier:+.1f}",
        )
    )

    # 9. Korelasyon riski düşük (+5) — open positions future
    correlation_ok = True  # MVP default
    score += 5
    factors.append(
        SetupFactor(
            name="Korelasyon riski düşük",
            passed=correlation_ok,
            points=5,
            note="Future adımda gerçek hesap (Adım 12 var, open positions Adım 15+)",
        )
    )

    # 10. Time-of-day uygun (+5) — Adım 14 future
    time_ok = True  # MVP default
    score += 5
    factors.append(
        SetupFactor(
            name="Time-of-day uygun",
            passed=time_ok,
            points=5,
            note="Future adımda gerçek hesap (Adım 14: No-Trade Zone)",
        )
    )

    return score, factors


def _grade_from_score(score: int) -> SetupGrade:
    if score >= 90:
        return "A"
    if score >= 70:
        return "B"
    if score >= 50:
        return "C"
    return "D"


def _apply_modifiers(
    base_grade: SetupGrade,
    *,
    direction: str,
    macro_modifier: float,
    counter_trend_high_count: int,
    trade_quality_verdict: str,
) -> tuple[SetupGrade, dict[str, int]]:
    """Final grade + uygulanan modifier'lar."""
    # Hard overrides
    if direction == "neutral":
        return "NO_TRADE", {"neutral_direction": 0}
    if trade_quality_verdict == "AVOID":
        return "NO_TRADE", {"trade_quality_avoid": -99}

    modifiers: dict[str, int] = {}

    idx = GRADE_ORDER.index(base_grade) if base_grade in GRADE_ORDER else 0

    if macro_modifier > 15:
        idx += 1
        modifiers["macro_strong_positive"] = 1
    elif macro_modifier < -15:
        idx -= 1
        modifiers["macro_strong_negative"] = -1

    if counter_trend_high_count >= 2:
        idx -= 1
        modifiers["counter_trend"] = -1

    if trade_quality_verdict == "EXCELLENT":
        idx += 1
        modifiers["trade_quality_excellent"] = 1
    elif trade_quality_verdict == "WEAK":
        idx -= 1
        modifiers["trade_quality_weak"] = -1

    idx = max(0, min(len(GRADE_ORDER) - 1, idx))
    return GRADE_ORDER[idx], modifiers


class SetupQualityEngine:
    """Public facade — 4 modülü compose eder."""

    async def evaluate(
        self,
        symbol: str,
        timeframe: str,
        *,
        session: AsyncSession | None = None,
        user_id: uuid.UUID | None = None,
    ) -> SetupQualityResult:
        if timeframe not in TF_TO_INTERVAL:
            raise ValueError(f"Bilinmeyen timeframe: {timeframe}")

        async def fetch() -> dict[str, Any]:
            # Paralel-friendly fetch
            final = await indicator_engine.compute_final_confluence(symbol, timeframe)
            alignment = await indicator_engine.compute_multi_tf_alignment(symbol)
            bundle = await indicator_engine.compute_all(symbol, timeframe)
            macro = await macro_service.get_snapshot()
            klines = await indicator_engine._get_klines(symbol, timeframe)
            df = klines_to_dataframe(klines)

            # Base score + factors
            base_score, base_factors = _compute_base_factors(final, alignment, bundle)
            base_grade = _grade_from_score(base_score)

            # Counter-trend (direction kullanır)
            counter_warnings = counter_trend_detector.detect(
                df=df,
                momentum=bundle.momentum,
                futures=bundle.futures,
                direction=final.direction,
                timeframe=timeframe,
            )
            high_severity_count = sum(1 for w in counter_warnings if w.severity == "high")

            # Trade quality filter
            quality_result = trade_quality_filter.evaluate(
                df=df,
                volatility=bundle.volatility,
                levels=bundle.levels,
                macro=macro,
            )

            # Confidence (DB session gerekli)
            local_session = session
            owned_session = False
            if local_session is None:
                local_session = AsyncSessionLocal()
                owned_session = True
            try:
                confidence = await confidence_engine.compute(
                    local_session,
                    symbol_category=final.symbol_type,
                    regime=final.market_regime,
                    base_grade=base_grade,
                    direction=final.direction,
                    user_id=user_id,
                )
            finally:
                if owned_session:
                    await local_session.close()

            # Final grade + modifiers
            final_grade, modifiers_applied = _apply_modifiers(
                base_grade,
                direction=final.direction,
                macro_modifier=final.macro_modifier,
                counter_trend_high_count=high_severity_count,
                trade_quality_verdict=quality_result.verdict,
            )

            result = SetupQualityResult(
                symbol=symbol,
                timeframe=timeframe,
                direction=final.direction,
                final_score=final.final_score,
                raw_score=base_score,
                base_grade=base_grade,
                grade=final_grade,
                factors=base_factors,
                grade_modifiers=modifiers_applied,
                confidence=confidence,
                counter_trend_warnings=counter_warnings,
                trade_quality=quality_result,
                computed_at=datetime.now(UTC),
            )
            return result.model_dump(mode="json")

        raw = await cached_call(
            key=f"setup_quality:{symbol}:{timeframe}",
            ttl=min(CACHE_TTL, TF_TTL[timeframe]),
            fetch_fn=fetch,
        )
        return SetupQualityResult.model_validate(raw)


setup_quality_engine = SetupQualityEngine()
