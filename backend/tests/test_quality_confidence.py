"""Confidence Engine: 5 level threshold + signature builder + neutral handling."""
from __future__ import annotations

import pytest

from app.services.quality.confidence_engine import (
    LOOKBACK_DAYS,
    _category_to_sql_filter,
    _classify_level,
    build_signature,
    confidence_engine,
)


def test_classify_very_low_under_5() -> None:
    level, label, advice = _classify_level(0)
    assert level == "VERY_LOW"
    assert "Kanıt yok" in label

    level, _, _ = _classify_level(4)
    assert level == "VERY_LOW"


def test_classify_low_5_to_14() -> None:
    assert _classify_level(5)[0] == "LOW"
    assert _classify_level(14)[0] == "LOW"


def test_classify_medium_15_to_29() -> None:
    assert _classify_level(15)[0] == "MEDIUM"
    assert _classify_level(29)[0] == "MEDIUM"


def test_classify_high_30_to_59() -> None:
    assert _classify_level(30)[0] == "HIGH"
    assert _classify_level(59)[0] == "HIGH"


def test_classify_very_high_60_plus() -> None:
    assert _classify_level(60)[0] == "VERY_HIGH"
    assert _classify_level(1000)[0] == "VERY_HIGH"


def test_lookback_180_days() -> None:
    assert LOOKBACK_DAYS == 180


def test_build_signature_format() -> None:
    sig = build_signature("alt", "MIXED", "B", "long")
    assert sig == "alt:MIXED:B:long"


def test_build_signature_btc_category() -> None:
    sig = build_signature("btc", "ALT_BULL", "A", "short")
    assert sig == "btc:ALT_BULL:A:short"


def test_category_filter_btc_only() -> None:
    codes = _category_to_sql_filter("btc")
    assert codes == ["BTCUSDT"]


def test_category_filter_commodity_only() -> None:
    codes = _category_to_sql_filter("commodity")
    assert codes == ["GOLD"]


def test_category_filter_alt_excludes_btc_and_gold() -> None:
    codes = _category_to_sql_filter("alt")
    assert "BTCUSDT" not in codes
    assert "GOLD" not in codes
    assert "ETHUSDT" in codes
    assert "SOLUSDT" in codes
    # 26 USDT - 1 BTC = 25 sembol
    assert len(codes) == 25


async def test_confidence_neutral_direction_returns_very_low_n0() -> None:
    """Neutral direction → DB query yapılmaz, n=0 VERY_LOW dön."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await confidence_engine.compute(
            session,
            symbol_category="btc",
            regime="MIXED",
            base_grade="B",
            direction="neutral",
            user_id=None,
        )
    assert result.level == "VERY_LOW"
    assert result.trade_count == 0
    assert result.actual_win_rate is None
    assert result.setup_signature.endswith(":neutral")


async def test_confidence_empty_db_returns_very_low() -> None:
    """Trade tablosu boş (henüz yok) → VERY_LOW dön."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await confidence_engine.compute(
            session,
            symbol_category="alt",
            regime="MIXED",
            base_grade="B",
            direction="long",
            user_id=None,
        )
    assert result.level == "VERY_LOW"
    assert result.trade_count == 0
    assert result.actual_win_rate is None
