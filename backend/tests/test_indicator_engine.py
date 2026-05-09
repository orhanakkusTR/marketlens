"""Engine smoke test — synthetic data ile compute_trend/momentum/all akışı."""
from __future__ import annotations

import pytest

from app.services.indicators.engine import indicator_engine

from ._synthetic import accelerating_uptrend, linear_uptrend


async def test_compute_trend_with_external_klines() -> None:
    klines = linear_uptrend(n=300)
    result = await indicator_engine.compute_trend("BTCUSDT", "4H", klines=klines)

    assert result.moving_averages.alignment == "bullish_stack"
    assert result.ichimoku.cloud_state == "above"
    assert result.market_structure.structure in ("uptrend", "ranging")


async def test_compute_momentum_with_external_klines() -> None:
    """Hızlanan uptrend → RSI overbought, MACD histogram pozitif."""
    klines = accelerating_uptrend(n=300)
    result = await indicator_engine.compute_momentum("BTCUSDT", "4H", klines=klines)

    assert result.rsi.state == "overbought"
    assert result.macd.histogram > 0


async def test_invalid_timeframe_raises() -> None:
    with pytest.raises(ValueError, match="Bilinmeyen timeframe"):
        await indicator_engine.compute_trend("BTCUSDT", "BAD", klines=linear_uptrend(n=300))


async def test_compute_volatility_with_external_klines() -> None:
    klines = linear_uptrend(n=300)
    result = await indicator_engine.compute_volatility("BTCUSDT", "4H", klines=klines)
    assert result.atr.value_usdt > 0
    assert result.atr.value_pct > 0
    assert result.bollinger.upper > result.bollinger.lower


async def test_compute_volume_with_external_klines() -> None:
    klines = linear_uptrend(n=300)
    result = await indicator_engine.compute_volume("BTCUSDT", "4H", klines=klines)
    assert result.obv.slope == "rising"
    assert result.vwap is None  # 4H intraday değil
    assert result.volume_profile.poc > 0


async def test_compute_fibonacci_returns_or_none() -> None:
    from ._synthetic import zigzag_uptrend

    klines = zigzag_uptrend(cycles=4, swing_size=20)
    result = await indicator_engine.compute_fibonacci("BTCUSDT", "4H", klines=klines)
    if result is not None:
        assert result.swing_high.price > result.swing_low.price
        assert len(result.levels) > 0


async def test_compute_levels_with_external_klines() -> None:
    from ._synthetic import zigzag_uptrend

    klines = zigzag_uptrend(cycles=4, swing_size=20)
    result = await indicator_engine.compute_levels("BTCUSDT", "4H", klines=klines)
    assert len(result.supports) <= 5
    assert len(result.resistances) <= 5
