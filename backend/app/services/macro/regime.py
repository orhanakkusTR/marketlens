"""Market regime detection (5 sınıf, türkçe label).

Tetikleyici eşikler (architecture.md tablosu + makul threshold'lar):
    BTC strong  : 7d > +5%
    BTC down    : 7d < -5%
    ETH/BTC up  : 7d > +3%
    ETH/BTC strong: 7d > +5%
    ETH/BTC down: 7d < 0%
    VIX spike   : 7d > +10%
    F&G greed   : > 65

Triggers dict frontend tooltip'inde "neden bu rejim?" gösterimi için.
"""
from __future__ import annotations

from app.schemas.macro import (
    FearGreedSnapshot,
    MarketRegime,
    MetricTrend,
    RegimeResult,
)

REGIME_LABELS: dict[MarketRegime, str] = {
    "ALT_BULL": "Altcoin boğa rejimi",
    "BTC_BULL": "BTC boğa, altlar geride",
    "RISK_OFF": "Risk-off, altlar zayıf",
    "ALT_SEASON_EARLY": "Erken alt sezonu işareti",
    "MIXED": "Kararsız ortam",
}


def _safe(pct: float | None) -> float:
    return 0.0 if pct is None else pct


def detect_market_regime(
    btc_market_cap: MetricTrend,
    eth_btc_ratio: MetricTrend,
    vix: MetricTrend,
    fear_greed: FearGreedSnapshot,
) -> RegimeResult:
    btc_7d = _safe(btc_market_cap.change_7d_pct)
    ethbtc_7d = _safe(eth_btc_ratio.change_7d_pct)
    vix_7d = _safe(vix.change_7d_pct)
    fng = fear_greed.value

    triggers: dict[str, bool] = {
        "btc_up_7d": btc_7d > 0,
        "btc_strong_7d": btc_7d > 5,
        "btc_down_7d": btc_7d < -5,
        "ethbtc_up_7d": ethbtc_7d > 3,
        "ethbtc_strong_7d": ethbtc_7d > 5,
        "ethbtc_down_7d": ethbtc_7d < 0,
        "vix_spike_7d": vix_7d > 10,
        "fng_greed": fng > 65,
    }

    regime: MarketRegime
    # Sıra önemli — en spesifik önce
    if triggers["vix_spike_7d"] and triggers["btc_down_7d"]:
        regime = "RISK_OFF"
    elif triggers["ethbtc_strong_7d"] and triggers["fng_greed"]:
        regime = "ALT_SEASON_EARLY"
    elif triggers["ethbtc_up_7d"] and triggers["btc_up_7d"]:
        regime = "ALT_BULL"
    elif triggers["btc_strong_7d"] and triggers["ethbtc_down_7d"]:
        regime = "BTC_BULL"
    else:
        regime = "MIXED"

    return RegimeResult(
        regime=regime,
        label=REGIME_LABELS[regime],
        triggers=triggers,
    )
