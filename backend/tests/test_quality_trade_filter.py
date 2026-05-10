"""Trade Quality Filter: 5 faktör + ADX inline + verdict mapping."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.schemas.indicators import (
    ATRResult,
    BollingerResult,
    LevelEntry,
    LevelsResult,
    VolatilityIndicators,
)
from app.schemas.macro import (
    CryptoCapsSnapshot,
    FearGreedSnapshot,
    MacroSnapshot,
    MetricTrend,
    RegimeResult,
)
from app.services.indicators.base import klines_to_dataframe
from app.services.quality.trade_quality_filter import (
    _is_macro_aligned,
    _verdict_from_score,
    _volume_increasing_n,
    trade_quality_filter,
)
from tests._synthetic import accelerating_uptrend, linear_uptrend


def _volatility(atr_usdt: float = 1.5, atr_pct: float = 1.5) -> VolatilityIndicators:
    return VolatilityIndicators(
        atr=ATRResult(value_usdt=atr_usdt, value_pct=atr_pct, period=14),
        bollinger=BollingerResult(
            upper=105, middle=100, lower=95, width_pct=10.0, squeeze=False
        ),
    )


def _levels(current: float = 100.0, supports: list[float] = None, resistances: list[float] = None) -> LevelsResult:
    supports = supports or [95.0]
    resistances = resistances or [105.0]
    return LevelsResult(
        current_price=current,
        supports=[
            LevelEntry(
                price=p, kind="support", sources=["pivot_low"], confluence_count=1, strength_score=1.0
            ) for p in supports
        ],
        resistances=[
            LevelEntry(
                price=p, kind="resistance", sources=["pivot_high"], confluence_count=1, strength_score=1.0
            ) for p in resistances
        ],
    )


def _metric(change_24h: float = 0.0) -> MetricTrend:
    return MetricTrend(
        current=100.0,
        change_24h_pct=change_24h,
        change_7d_pct=0.0,
        change_30d_pct=0.0,
        direction_24h="flat",
        direction_7d="flat",
        direction_30d="flat",
    )


def _macro(dxy_24h: float = 0.0, spx_24h: float = 0.0) -> MacroSnapshot:
    return MacroSnapshot(
        crypto_caps=CryptoCapsSnapshot(
            total=2.5e12, total2=1e12, total3=0.7e12,
            btc_dominance=55, eth_dominance=15,
        ),
        btc_market_cap=_metric(),
        eth_btc_ratio=_metric(),
        dxy=_metric(dxy_24h),
        sp500=_metric(spx_24h),
        nasdaq=_metric(),
        vix=_metric(),
        us10y=_metric(),
        gold=_metric(),
        fear_greed=FearGreedSnapshot(value=50, classification="Neutral", timestamp="0"),
        market_regime=RegimeResult(regime="MIXED", label="Kararsız", triggers={}),
        computed_at=datetime.now(UTC),
    )


# ─── Helper unit tests ───


def test_macro_aligned_bullish_crypto() -> None:
    """DXY ↓ + SP500 ↑ → bullish kripto, aligned."""
    macro = _macro(dxy_24h=-0.5, spx_24h=+1.0)
    assert _is_macro_aligned(macro) is True


def test_macro_aligned_bearish_crypto() -> None:
    """DXY ↑ + SP500 ↓ → bearish kripto, aligned."""
    macro = _macro(dxy_24h=+0.5, spx_24h=-1.0)
    assert _is_macro_aligned(macro) is True


def test_macro_not_aligned_same_direction() -> None:
    """DXY ↑ + SP500 ↑ → karışık, not aligned."""
    macro = _macro(dxy_24h=+0.5, spx_24h=+1.0)
    assert _is_macro_aligned(macro) is False


def test_macro_not_aligned_none_data() -> None:
    macro = _macro()
    # change_24h_pct=0 → not strict ↑↓; iki tarafta da sıfır → not aligned
    # Implementation: (dxy<0 and spx>0) or (dxy>0 and spx<0); 0 ne <0 ne >0 → False
    assert _is_macro_aligned(macro) is False


def test_volume_increasing_4_bars() -> None:
    klines = []
    for i in range(50):
        v = 100.0 if i < 46 else 100.0 + (i - 45) * 10  # son 4 artıyor
        klines.append({
            "open_time": i * 14_400_000, "open": 100, "high": 100.1, "low": 99.9,
            "close": 100, "volume": v, "close_time": (i + 1) * 14_400_000,
            "quote_volume": 1000, "trades": 10,
        })
    df = klines_to_dataframe(klines)
    assert _volume_increasing_n(df, n=4) is True


def test_volume_not_increasing_flat() -> None:
    df = klines_to_dataframe([
        {
            "open_time": i * 14_400_000, "open": 100, "high": 100.1, "low": 99.9,
            "close": 100, "volume": 100, "close_time": (i + 1) * 14_400_000,
            "quote_volume": 1000, "trades": 10,
        }
        for i in range(50)
    ])
    assert _volume_increasing_n(df, n=4) is False


def test_verdict_excellent_score_4_or_5() -> None:
    assert _verdict_from_score(5) == ("EXCELLENT", 1)
    assert _verdict_from_score(4) == ("EXCELLENT", 1)


def test_verdict_good_score_3() -> None:
    assert _verdict_from_score(3) == ("GOOD", 0)


def test_verdict_weak_score_2() -> None:
    assert _verdict_from_score(2) == ("WEAK", -1)


def test_verdict_avoid_score_0_or_1() -> None:
    assert _verdict_from_score(1) == ("AVOID", -2)
    assert _verdict_from_score(0) == ("AVOID", -2)


# ─── Full evaluate ───


def test_evaluate_returns_5_factors() -> None:
    df = klines_to_dataframe(linear_uptrend(n=100))
    result = trade_quality_filter.evaluate(
        df=df,
        volatility=_volatility(),
        levels=_levels(),
        macro=_macro(),
    )
    assert len(result.factors) == 5


def test_evaluate_turkish_labels() -> None:
    """5 faktörün adı türkçe olmalı."""
    df = klines_to_dataframe(linear_uptrend(n=100))
    result = trade_quality_filter.evaluate(
        df=df, volatility=_volatility(), levels=_levels(), macro=_macro(),
    )
    expected_names = {"ATR makul", "ADX güçlü", "Macro net", "Hacim artıyor", "Yol açık"}
    actual_names = {f.name for f in result.factors}
    assert actual_names == expected_names


def test_evaluate_atr_low_fails_volatility() -> None:
    df = klines_to_dataframe(linear_uptrend(n=100))
    result = trade_quality_filter.evaluate(
        df=df, volatility=_volatility(atr_pct=0.5),  # < 0.8
        levels=_levels(), macro=_macro(),
    )
    atr_factor = next(f for f in result.factors if f.name == "ATR makul")
    assert atr_factor.passed is False


def test_evaluate_macro_aligned_passes() -> None:
    df = klines_to_dataframe(linear_uptrend(n=100))
    result = trade_quality_filter.evaluate(
        df=df, volatility=_volatility(),
        levels=_levels(),
        macro=_macro(dxy_24h=-1.0, spx_24h=+1.0),
    )
    macro_factor = next(f for f in result.factors if f.name == "Macro net")
    assert macro_factor.passed is True


def test_evaluate_clear_path_far_sr_passes() -> None:
    """SR uzakta (>2 ATR) → yol açık passed."""
    df = klines_to_dataframe(linear_uptrend(n=100))
    last_price = float(df["close"].iloc[-1])
    # SR çok uzakta (10 ATR)
    result = trade_quality_filter.evaluate(
        df=df,
        volatility=_volatility(atr_usdt=1.0),  # ATR = 1 birim
        levels=_levels(
            current=last_price,
            supports=[last_price - 20],  # 20 birim aşağı = 20 ATR
            resistances=[last_price + 20],
        ),
        macro=_macro(),
    )
    cp = next(f for f in result.factors if f.name == "Yol açık")
    assert cp.passed is True


def test_evaluate_clear_path_close_sr_fails() -> None:
    df = klines_to_dataframe(linear_uptrend(n=100))
    last_price = float(df["close"].iloc[-1])
    result = trade_quality_filter.evaluate(
        df=df,
        volatility=_volatility(atr_usdt=10.0),  # ATR büyük
        levels=_levels(
            current=last_price,
            supports=[last_price - 5],  # 0.5 ATR uzakta
            resistances=[last_price + 5],
        ),
        macro=_macro(),
    )
    cp = next(f for f in result.factors if f.name == "Yol açık")
    assert cp.passed is False
