"""Setup Quality R/R factor — Adım 16 sonrası scenario.rr_weighted üzerinden.

Adım 15'te _estimate_rr placeholder yerine kullanılıyordu; Adım 16'da bunu
deprecate ettik ve scenario.rr_weighted tek source of truth oldu.

Bu modül `_compute_base_factors`'ın R/R faktörünü scenario ile doğru hesaplayıp
hesaplamadığını test eder.
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.schemas.confluence import (
    AlignmentResult,
    FinalConfluenceResult,
    ScoreBreakdown,
    TimeframeScore,
    ModifierBreakdown,
)
from app.schemas.indicators import (
    ATRResult,
    BollingerResult,
    IndicatorBundle,
    LevelEntry,
    LevelsResult,
    VolatilityIndicators,
)
from app.schemas.scenario import (
    EntryBand,
    ScenarioResult,
    StopLevel,
    TPLevel,
)
from app.services.quality.setup_quality import (
    RR_FULL_THRESHOLD,
    RR_PARTIAL_THRESHOLD,
    _compute_base_factors,
)


def _bundle(
    *,
    current_price: float = 80500.0,
    atr_usdt: float = 500.0,
    atr_pct: float = 0.62,
    resistances: list[float] | None = None,
    supports: list[float] | None = None,
) -> IndicatorBundle:
    levels = LevelsResult(
        current_price=current_price,
        supports=[
            LevelEntry(
                price=p, kind="support", sources=["pivot_low"],
                confluence_count=1, strength_score=1.0,
            ) for p in (supports or [78000.0])
        ],
        resistances=[
            LevelEntry(
                price=p, kind="resistance", sources=["pivot_high"],
                confluence_count=1, strength_score=1.0,
            ) for p in (resistances or [83500.0])
        ],
    )
    volatility = VolatilityIndicators(
        atr=ATRResult(value_usdt=atr_usdt, value_pct=atr_pct, period=14),
        bollinger=BollingerResult(
            upper=current_price * 1.02, middle=current_price,
            lower=current_price * 0.98, width_pct=4.0, squeeze=False,
        ),
    )
    return IndicatorBundle(
        symbol="BTCUSDT",
        timeframe="4H",
        computed_at=datetime.now(UTC),
        kline_count=200,
        volatility=volatility,
        levels=levels,
    )


def _final(direction: str = "long", score: float = 60.0) -> FinalConfluenceResult:
    return FinalConfluenceResult(
        symbol="BTCUSDT",
        timeframe="4H",
        symbol_type="btc",
        local_score=score,
        components=ScoreBreakdown(
            trend=score, momentum=score, volume=score,
            volatility=score, futures=score,
        ),
        weights_applied={
            "trend": 0.40, "momentum": 0.20, "volume": 0.15,
            "volatility": 0.10, "futures": 0.15,
        },
        macro_modifier=0.0,
        macro_breakdown=ModifierBreakdown(dxy=0.0, vix=15.0),
        final_score=score,
        label="bullish" if score > 30 else "neutral",
        direction=direction,  # type: ignore[arg-type]
        market_regime="MIXED",
        computed_at=datetime.now(UTC),
    )


def _alignment_empty() -> AlignmentResult:
    return AlignmentResult(
        symbol="BTCUSDT",
        alignment_score=0.0,
        label="weak",
        consistent_direction=None,
        by_timeframe=[],
        weights={},
        computed_at=datetime.now(UTC),
    )


def _scenario_with_rr(rr_weighted: float, direction: str = "long") -> ScenarioResult:
    """Sentetik scenario — sadece rr_weighted manters."""
    return ScenarioResult(
        symbol="BTCUSDT",
        timeframe="4H",
        direction=direction,  # type: ignore[arg-type]
        entry=EntryBand(low=80350, mid=80500, high=80650, width_atr=0.6),
        stop=StopLevel(
            price=79750, source="support", distance_atr=1.5,
            distance_pct=0.93, reasoning="test stop",
        ),
        targets=[
            TPLevel(
                price=80500 + 1000, source="test", distance_atr=2.0,
                distance_pct=1.24, rr=rr_weighted, reasoning="test tp",
            )
        ],
        rr_weighted=rr_weighted,
        final_confluence=60.0,
        reasoning="test",
        computed_at=datetime.now(UTC),
    )


# ─── R/R factor scoring ───


def test_rr_above_3_full_credit() -> None:
    """rr_weighted ≥ 3 → +10 puan."""
    score, factors = _compute_base_factors(
        _final("long"), _alignment_empty(), _bundle(),
        _scenario_with_rr(3.5),
    )
    rr_factor = next(f for f in factors if f.name == "R:R ≥ 3")
    assert rr_factor.passed is True
    assert rr_factor.points == 10


def test_rr_partial_credit() -> None:
    """1.5 ≤ rr_weighted < 3 → +5 puan."""
    score, factors = _compute_base_factors(
        _final("long"), _alignment_empty(), _bundle(),
        _scenario_with_rr(2.0),
    )
    rr_factor = next(f for f in factors if f.name == "R:R ≥ 3")
    assert rr_factor.passed is True
    assert rr_factor.points == 5


def test_rr_below_partial_zero_credit() -> None:
    """rr_weighted < 1.5 → 0 puan."""
    score, factors = _compute_base_factors(
        _final("long"), _alignment_empty(), _bundle(),
        _scenario_with_rr(0.8),
    )
    rr_factor = next(f for f in factors if f.name == "R:R ≥ 3")
    assert rr_factor.passed is False
    assert rr_factor.points == 0


def test_rr_neutral_direction_no_scenario() -> None:
    """Direction neutral → scenario=None → 0 puan + 'Neutral' note."""
    score, factors = _compute_base_factors(
        _final("neutral"), _alignment_empty(), _bundle(),
        None,  # scenario None
    )
    rr_factor = next(f for f in factors if f.name == "R:R ≥ 3")
    assert rr_factor.passed is False
    assert rr_factor.points == 0
    assert "Neutral" in rr_factor.note


def test_rr_scenario_none_other_reasons() -> None:
    """Scenario None ama direction long (veriler yetersiz) → 0 puan + 'üretilemedi' note."""
    score, factors = _compute_base_factors(
        _final("long"), _alignment_empty(), _bundle(),
        None,
    )
    rr_factor = next(f for f in factors if f.name == "R:R ≥ 3")
    assert rr_factor.passed is False
    assert rr_factor.points == 0
    assert "üretilemedi" in rr_factor.note


def test_rr_constants() -> None:
    assert RR_FULL_THRESHOLD == 3.0
    assert RR_PARTIAL_THRESHOLD == 1.5
