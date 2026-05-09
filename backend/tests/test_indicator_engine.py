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
