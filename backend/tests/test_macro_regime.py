"""Market regime detector — 5 rejim için trigger senaryoları."""
from __future__ import annotations

from app.schemas.macro import FearGreedSnapshot, MetricTrend
from app.services.macro.regime import REGIME_LABELS, detect_market_regime


def _trend(change_7d: float | None) -> MetricTrend:
    return MetricTrend(
        current=100.0,
        change_24h_pct=0.0,
        change_7d_pct=change_7d,
        change_30d_pct=0.0,
        direction_24h="flat",
        direction_7d="up" if (change_7d or 0) > 0.5 else ("down" if (change_7d or 0) < -0.5 else "flat"),
        direction_30d="flat",
    )


def _fng(value: int) -> FearGreedSnapshot:
    return FearGreedSnapshot(
        value=value,
        classification="Greed" if value > 65 else "Neutral",
        timestamp="0",
    )


def test_risk_off_when_vix_spike_and_btc_down() -> None:
    result = detect_market_regime(
        btc_market_cap=_trend(-7.0),  # btc_down_7d
        eth_btc_ratio=_trend(0.0),
        vix=_trend(15.0),  # vix_spike
        fear_greed=_fng(40),
    )
    assert result.regime == "RISK_OFF"
    assert result.label == "Risk-off, altlar zayıf"
    assert result.triggers["vix_spike_7d"] is True
    assert result.triggers["btc_down_7d"] is True


def test_alt_season_early_when_ethbtc_strong_and_greed() -> None:
    result = detect_market_regime(
        btc_market_cap=_trend(2.0),
        eth_btc_ratio=_trend(7.0),  # strong
        vix=_trend(0.0),
        fear_greed=_fng(75),  # greed
    )
    assert result.regime == "ALT_SEASON_EARLY"
    assert result.label == "Erken alt sezonu işareti"


def test_alt_bull_when_ethbtc_up_and_btc_up() -> None:
    result = detect_market_regime(
        btc_market_cap=_trend(3.0),  # btc_up
        eth_btc_ratio=_trend(4.0),  # ethbtc_up (>3)
        vix=_trend(0.0),
        fear_greed=_fng(55),
    )
    assert result.regime == "ALT_BULL"
    assert result.label == "Altcoin boğa rejimi"


def test_btc_bull_when_btc_strong_and_ethbtc_down() -> None:
    result = detect_market_regime(
        btc_market_cap=_trend(7.0),  # btc_strong
        eth_btc_ratio=_trend(-2.0),  # ethbtc_down
        vix=_trend(0.0),
        fear_greed=_fng(50),
    )
    assert result.regime == "BTC_BULL"
    assert result.label == "BTC boğa, altlar geride"


def test_mixed_when_no_specific_pattern() -> None:
    result = detect_market_regime(
        btc_market_cap=_trend(1.0),  # weak up
        eth_btc_ratio=_trend(1.0),  # not enough for ethbtc_up (>3)
        vix=_trend(2.0),
        fear_greed=_fng(50),
    )
    assert result.regime == "MIXED"
    assert result.label == "Kararsız ortam"


def test_risk_off_priority_over_other_signals() -> None:
    """RISK_OFF en spesifik — diğer trigger'lar olsa bile o seçilmeli."""
    result = detect_market_regime(
        btc_market_cap=_trend(-7.0),  # btc_down (RISK_OFF)
        eth_btc_ratio=_trend(7.0),  # ethbtc_strong (would be ALT_SEASON_EARLY)
        vix=_trend(15.0),  # vix_spike
        fear_greed=_fng(75),  # greed
    )
    assert result.regime == "RISK_OFF"


def test_triggers_dict_complete() -> None:
    """Triggers dict 8 anahtar içermeli (frontend tooltip için)."""
    result = detect_market_regime(
        btc_market_cap=_trend(0.0),
        eth_btc_ratio=_trend(0.0),
        vix=_trend(0.0),
        fear_greed=_fng(50),
    )
    expected_keys = {
        "btc_up_7d", "btc_strong_7d", "btc_down_7d",
        "ethbtc_up_7d", "ethbtc_strong_7d", "ethbtc_down_7d",
        "vix_spike_7d", "fng_greed",
    }
    assert set(result.triggers.keys()) == expected_keys


def test_all_regime_labels_in_turkish() -> None:
    """5 rejim için türkçe label tanımlı."""
    expected = {"ALT_BULL", "BTC_BULL", "RISK_OFF", "ALT_SEASON_EARLY", "MIXED"}
    assert set(REGIME_LABELS.keys()) == expected
    for label in REGIME_LABELS.values():
        assert isinstance(label, str)
        assert len(label) > 0


def test_safe_handles_none_change() -> None:
    """change_7d_pct None olsa bile çalışmalı."""
    result = detect_market_regime(
        btc_market_cap=_trend(None),
        eth_btc_ratio=_trend(None),
        vix=_trend(None),
        fear_greed=_fng(50),
    )
    assert result.regime == "MIXED"
