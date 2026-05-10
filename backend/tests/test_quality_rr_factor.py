"""Setup Quality R/R factor — Adım 15 ile gerçek hesap.

Önce placeholder'dı, şimdi auto entry/stop/TP üzerinden hesaplanıyor.
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.schemas.indicators import (
    ATRResult,
    BollingerResult,
    IndicatorBundle,
    LevelEntry,
    LevelsResult,
    VolatilityIndicators,
)
from app.services.quality.setup_quality import (
    RR_FULL_THRESHOLD,
    RR_PARTIAL_THRESHOLD,
    _estimate_rr,
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


# ─── Direction handling ───


def test_rr_neutral_returns_none() -> None:
    rr, note = _estimate_rr("neutral", _bundle())
    assert rr is None
    assert "Neutral" in note


def test_rr_long_with_nearby_resistance() -> None:
    """Entry 80500, stop = 80500 - 1.5*500 = 79750 (risk 750).
    TP = en yakın resistance 83500 (reward 3000). R/R = 4.0.
    """
    rr, note = _estimate_rr("long", _bundle(resistances=[83500.0]))
    assert rr is not None
    assert abs(rr - 4.0) < 1e-3
    assert "resistance" in note


def test_rr_short_with_nearby_support() -> None:
    """Short: entry 80500, stop = 80500 + 1.5*500 = 81250 (risk 750).
    TP = en yakın support 78000 (reward 2500). R/R = 3.333.
    """
    rr, note = _estimate_rr(
        "short", _bundle(supports=[78000.0]),
    )
    assert rr is not None
    assert abs(rr - (2500 / 750)) < 1e-3
    assert "support" in note


def test_rr_fallback_when_no_resistances() -> None:
    """Resistances list empty → fallback current_price + 3*ATR.
    Entry 80500, stop 79750 (risk 750), tp 80500 + 1500 = 82000 (reward 1500). R/R = 2.0.
    """
    bundle = _bundle()
    bundle.levels.resistances.clear()
    rr, note = _estimate_rr("long", bundle)
    assert rr is not None
    assert abs(rr - 2.0) < 1e-3
    assert "fallback" in note


def test_rr_no_volatility_returns_none() -> None:
    bundle = _bundle()
    bundle.volatility = None
    rr, note = _estimate_rr("long", bundle)
    assert rr is None


def test_rr_above_3_full_credit() -> None:
    """R/R 4.0 ≥ 3.0 → full credit."""
    rr, _ = _estimate_rr("long", _bundle(resistances=[83500.0]))
    assert rr is not None
    assert rr >= RR_FULL_THRESHOLD


def test_rr_between_partial_threshold() -> None:
    """Resistance 82000 → reward 1500, risk 750 → R/R 2.0 (partial)."""
    rr, _ = _estimate_rr("long", _bundle(resistances=[82000.0]))
    assert rr is not None
    assert RR_PARTIAL_THRESHOLD <= rr < RR_FULL_THRESHOLD


def test_rr_below_partial_threshold() -> None:
    """Resistance 81000 → reward 500, risk 750 → R/R 0.67 (zero credit)."""
    rr, _ = _estimate_rr("long", _bundle(resistances=[81000.0]))
    assert rr is not None
    assert rr < RR_PARTIAL_THRESHOLD


def test_rr_constants() -> None:
    assert RR_FULL_THRESHOLD == 3.0
    assert RR_PARTIAL_THRESHOLD == 1.5
