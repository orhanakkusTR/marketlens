"""Final confluence (local + macro modifier) testleri."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.schemas.confluence import LocalConfluenceResult, ScoreBreakdown
from app.services.confluence.final import compute_final_confluence
from tests.test_confluence_macro_modifier import _snapshot


def _local(symbol: str = "BTCUSDT", score: float = 50.0) -> LocalConfluenceResult:
    return LocalConfluenceResult(
        symbol=symbol,
        timeframe="4H",
        final_score=score,
        label="bullish",
        direction="long",
        components=ScoreBreakdown(
            trend=80.0, momentum=30.0, volume=10.0, volatility=20.0, futures=0.0,
        ),
        weights_applied={"trend": 0.4, "momentum": 0.2, "volume": 0.15, "volatility": 0.1, "futures": 0.15},
        computed_at=datetime.now(UTC),
    )


def test_final_composition_btc_with_positive_modifier() -> None:
    """Local +50 + macro +10 = final 60 (bullish, long)."""
    local = _local("BTCUSDT", score=50)
    snap = _snapshot(eth_btc_7d=-5.0)  # +10 for BTC
    result = compute_final_confluence(local, snap)

    assert result.local_score == 50
    assert result.macro_modifier == pytest.approx(10.0)
    assert result.final_score == pytest.approx(60.0)
    assert result.label == "bullish"
    assert result.direction == "long"
    assert result.symbol_type == "btc"
    assert result.market_regime == "MIXED"


def test_final_label_strong_bullish_above_60() -> None:
    local = _local("BTCUSDT", score=65)
    snap = _snapshot(eth_btc_7d=-5.0, sp500_7d=4.0)  # ~+16 modifier
    result = compute_final_confluence(local, snap)
    assert result.final_score > 60
    assert result.label == "strong_bullish"


def test_final_clamped_to_100() -> None:
    """Local +95 + macro +25 = clamp +100."""
    local = _local("BTCUSDT", score=95)
    snap = _snapshot(eth_btc_7d=-10.0, sp500_7d=10.0, dxy_7d=-10.0, vix_level=10.0)
    result = compute_final_confluence(local, snap)
    assert result.final_score == 100.0


def test_final_alt_with_regime_modifier() -> None:
    """ALT için ALT_BULL rejim ek +5."""
    local = _local("ETHUSDT", score=40)
    snap = _snapshot(eth_btc_7d=4.0, regime="ALT_BULL")
    result = compute_final_confluence(local, snap)
    assert result.symbol_type == "alt"
    assert result.macro_breakdown.regime == 5.0
    # local 40 + eth_btc 8 + regime 5 = 53
    assert result.final_score > 50


def test_final_gold_only_dxy_vix() -> None:
    local = _local("GOLD", score=30)
    snap = _snapshot(dxy_7d=-3.0, vix_level=22.0)
    result = compute_final_confluence(local, snap)
    assert result.symbol_type == "commodity"
    assert result.macro_breakdown.eth_btc is None
    assert result.macro_breakdown.sp500 is None
    assert result.macro_breakdown.regime is None
    assert result.macro_breakdown.dxy == pytest.approx(9.0)  # -dxy_7d * 3.0 = 9


def test_final_mixed_regime_small_modifier() -> None:
    """MIXED rejim + nötr metrikler → modifier -5 .. +10 aralığı."""
    local = _local("BTCUSDT", score=50)
    snap = _snapshot(
        eth_btc_7d=-2.0,  # +4
        sp500_7d=1.0,     # +1.5
        dxy_7d=-1.0,      # +2
        vix_level=18.0,   # 0
        regime="MIXED",
    )
    result = compute_final_confluence(local, snap)
    # 4 + 1.5 + 2 + 0 = 7.5
    assert -5 < result.macro_modifier < 10


def test_final_direction_changes_with_modifier() -> None:
    """Local +15 (neutral direction) + macro +10 = final 25 → direction long."""
    local = _local("BTCUSDT", score=15)
    snap = _snapshot(eth_btc_7d=-5.0)  # +10
    result = compute_final_confluence(local, snap)
    assert result.final_score == pytest.approx(25.0)
    assert result.direction == "long"
