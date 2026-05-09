"""Confluence scorer'ların golden testleri.

Her scorer pure function — minimal Pydantic instance'larıyla doğrudan çağrılır.
"""
from __future__ import annotations

import pytest

from app.schemas.indicators import (
    ATRResult,
    BollingerResult,
    DivergenceResult,
    FibSwing,
    FundingAnalysisResult,
    FuturesIndicators,
    IchimokuResult,
    LongShortAnomalyResult,
    MACDResult,
    MarketStructureResult,
    MomentumIndicators,
    MovingAverage,
    MovingAveragesResult,
    OBVResult,
    OIChangeResult,
    RSIResult,
    StochRSIResult,
    TrendIndicators,
    VolatilityIndicators,
    VolumeIndicators,
    VolumeProfileResult,
    VWAPResult,
)
from app.services.confluence.futures_scorer import score_futures
from app.services.confluence.momentum_scorer import score_momentum
from app.services.confluence.trend_scorer import score_trend
from app.services.confluence.volatility_scorer import score_volatility
from app.services.confluence.volume_scorer import score_volume


# ─── Trend ───


def _make_trend(
    *,
    alignment: str = "bullish_stack",
    ma200_distance: float = 5.0,
    ma200_type: str = "EMA",
    cloud_state: str = "above",
    tk_cross: str = "none",
    structure: str = "uptrend",
) -> TrendIndicators:
    return TrendIndicators(
        moving_averages=MovingAveragesResult(
            timeframe="4H",
            price=100.0,
            moving_averages=[
                MovingAverage(period=50, type="EMA", value=95.0, distance_pct=5.0),
                MovingAverage(period=100, type="EMA", value=92.0, distance_pct=8.0),
                MovingAverage(
                    period=200,
                    type=ma200_type,  # type: ignore[arg-type]
                    value=90.0,
                    distance_pct=ma200_distance,
                ),
            ],
            alignment=alignment,  # type: ignore[arg-type]
        ),
        ichimoku=IchimokuResult(
            tenkan=98.0,
            kijun=95.0,
            senkou_a=94.0,
            senkou_b=92.0,
            chikou=99.0,
            cloud_state=cloud_state,  # type: ignore[arg-type]
            tk_cross=tk_cross,  # type: ignore[arg-type]
        ),
        market_structure=MarketStructureResult(
            structure=structure,  # type: ignore[arg-type]
            recent_swings=[],
            last_swing_high=None,
            last_swing_low=None,
        ),
    )


def test_trend_full_bullish() -> None:
    """bullish_stack + price>MA200 + cloud above + uptrend → +100."""
    score = score_trend(_make_trend(), "4H")
    assert score == 100.0


def test_trend_full_bearish() -> None:
    score = score_trend(
        _make_trend(
            alignment="bearish_stack",
            ma200_distance=-5.0,
            cloud_state="below",
            structure="downtrend",
        ),
        "4H",
    )
    assert score == -100.0


def test_trend_neutral_mixed_ranging() -> None:
    score = score_trend(
        _make_trend(
            alignment="mixed",
            ma200_distance=0.0,
            cloud_state="inside",
            structure="ranging",
        ),
        "4H",
    )
    assert score == 0.0


def test_trend_tk_cross_bonus_clamped_to_20() -> None:
    """Cloud above (+20) + bullish TK cross (+5) → clamp 20."""
    score = score_trend(
        _make_trend(
            alignment="mixed",
            ma200_distance=0.0,
            cloud_state="above",
            tk_cross="bullish",
            structure="ranging",
        ),
        "4H",
    )
    # ichimoku component clamped to 20 (cloud above 20 + bullish cross +5 → still 20)
    assert score == 20.0


def test_trend_1d_bonus_above_5pct() -> None:
    """1D + SMA200 distance > 5% → +10 bonus."""
    score = score_trend(
        _make_trend(ma200_distance=8.0, ma200_type="SMA"),
        "1D",
    )
    # 30 + 20 + 20 + 30 + 10 = 110 → clamp 100
    assert score == 100.0


def test_trend_1d_bonus_not_applied_on_4h() -> None:
    """4H'da 1D bonus tetiklenmez (clamp etkisi yok)."""
    base = score_trend(_make_trend(ma200_distance=8.0), "4H")
    # 30 + 20 + 20 + 30 = 100 (zaten clamp), bonus eklenmez
    assert base == 100.0


# ─── Momentum ───


def _make_momentum(
    *,
    rsi_value: float = 55.0,
    rsi_state: str = "neutral",
    macd_hist: float = 1.0,
    macd_dir: str = "rising",
    stoch_k: float = 60.0,
    stoch_d: float = 50.0,
    stoch_cross: str = "bullish",
    div_rsi_type: str = "none",
    div_macd_type: str = "none",
) -> MomentumIndicators:
    return MomentumIndicators(
        rsi=RSIResult(current=rsi_value, history=[rsi_value], state=rsi_state),  # type: ignore[arg-type]
        macd=MACDResult(
            macd=1.0,
            signal=0.5,
            histogram=macd_hist,
            histogram_direction=macd_dir,  # type: ignore[arg-type]
            cross="none",
        ),
        stoch_rsi=StochRSIResult(
            k=stoch_k,
            d=stoch_d,
            state="neutral",
            cross=stoch_cross,  # type: ignore[arg-type]
        ),
        divergence_rsi=DivergenceResult(detected=False, type=div_rsi_type),  # type: ignore[arg-type]
        divergence_macd=DivergenceResult(detected=False, type=div_macd_type),  # type: ignore[arg-type]
    )


def test_momentum_strong_bullish() -> None:
    """RSI 65 + MACD pozitif rising + Stoch k>d 50-80 + regular bullish div → ~+100."""
    score = score_momentum(
        _make_momentum(
            rsi_value=65.0,
            macd_hist=1.0,
            macd_dir="rising",
            stoch_k=60.0,
            stoch_d=50.0,
            div_rsi_type="regular_bullish",
        )
    )
    # RSI 25 + MACD 30 + Stoch 25 + Div 20 = 100
    assert score == 100.0


def test_momentum_strong_bearish() -> None:
    score = score_momentum(
        _make_momentum(
            rsi_value=35.0,
            rsi_state="neutral",
            macd_hist=-1.0,
            macd_dir="falling",
            stoch_k=40.0,
            stoch_d=50.0,
            stoch_cross="bearish",
            div_rsi_type="regular_bearish",
        )
    )
    # RSI -25 + MACD -30 + Stoch -25 + Div -20 = -100
    assert score == -100.0


def test_momentum_overbought_rsi_only_mild_bonus() -> None:
    """RSI >=70 → sadece +10 (exhaustion riski)."""
    score = score_momentum(
        _make_momentum(rsi_value=75.0, macd_hist=0.0, macd_dir="flat", stoch_k=50.0, stoch_d=50.0)
    )
    # RSI 10 + MACD 0 + Stoch 0 + Div 0 = 10
    assert score == 10.0


def test_momentum_divergence_picks_strongest() -> None:
    """RSI hidden_bullish (+10) ve MACD regular_bullish (+20) → +20."""
    score = score_momentum(
        _make_momentum(
            rsi_value=50.0,
            macd_hist=0.0,
            macd_dir="flat",
            stoch_k=50.0,
            stoch_d=50.0,
            div_rsi_type="hidden_bullish",
            div_macd_type="regular_bullish",
        )
    )
    # RSI 15 + MACD 0 + Stoch 0 + Div 20 = 35
    assert score == 35.0


# ─── Volume ───


def _make_volume(
    *,
    obv_slope: str = "rising",
    poc: float = 95.0,
    val: float = 90.0,
    vah: float = 100.0,
    vwap_distance: float | None = 1.5,
) -> VolumeIndicators:
    vwap = None
    if vwap_distance is not None:
        vwap = VWAPResult(
            value=98.0, distance_pct=vwap_distance, session_start_ms=0
        )
    return VolumeIndicators(
        obv=OBVResult(current=1000.0, slope=obv_slope),  # type: ignore[arg-type]
        vwap=vwap,
        volume_profile=VolumeProfileResult(
            poc=poc,
            vah=vah,
            val=val,
            total_volume=1000.0,
            bin_count=50,
            window_bars=30,
        ),
    )


def test_volume_strong_bullish_with_vwap() -> None:
    """OBV rising + high vol + price > VAH + price >> VWAP → +100."""
    score = score_volume(
        _make_volume(),
        price=105.0,  # > VAH 100
        volume_ratio=2.0,  # > 1.5
        price_direction="up",
    )
    # OBV 25 + vol_ratio 25 + POC 20 (above VAH) + VWAP 30 (>1%) = 100
    assert score == 100.0


def test_volume_strong_bearish_no_vwap() -> None:
    """4H+ TF (vwap=None) — VWAP skoru 0."""
    score = score_volume(
        _make_volume(obv_slope="falling", vwap_distance=None),
        price=85.0,  # < VAL 90
        volume_ratio=2.0,
        price_direction="down",
    )
    # OBV -25 + vol_ratio -25 + POC -20 + VWAP 0 = -70
    assert score == -70.0


def test_volume_low_volume_warning() -> None:
    """volume_ratio < 0.7 + price up → -10 (zayıf rally)."""
    score = score_volume(
        _make_volume(obv_slope="flat", vwap_distance=None),
        price=95.0,  # POC seviyesinde
        volume_ratio=0.5,
        price_direction="up",
    )
    # OBV 0 + vol_ratio -10 + POC 0 + VWAP 0 = -10
    assert score == -10.0


def test_volume_inside_value_area_above_poc() -> None:
    score = score_volume(
        _make_volume(obv_slope="flat", vwap_distance=None),
        price=97.0,  # poc 95, vah 100
        volume_ratio=1.0,
        price_direction="flat",
    )
    # OBV 0 + vol_ratio 0 + POC +5 + VWAP 0 = 5
    assert score == 5.0


# ─── Volatility ───


def _make_volatility(
    *,
    squeeze: bool = True,
    middle: float = 100.0,
    atr_pct: float = 1.5,
) -> VolatilityIndicators:
    return VolatilityIndicators(
        atr=ATRResult(value_usdt=1.5, value_pct=atr_pct, period=14),
        bollinger=BollingerResult(
            upper=middle + 5,
            middle=middle,
            lower=middle - 5,
            width_pct=10.0,
            squeeze=squeeze,
        ),
    )


def test_volatility_squeeze_bullish_breakout() -> None:
    """Squeeze + price > middle → +30 (max)."""
    score = score_volatility(_make_volatility(), price=105.0)
    assert score == 30.0


def test_volatility_squeeze_bearish_breakout() -> None:
    """Squeeze + price < middle → -30."""
    score = score_volatility(_make_volatility(), price=95.0)
    assert score == -30.0


def test_volatility_extreme_atr_penalty() -> None:
    """ATR > 5% → -20, no squeeze → 0; net -20."""
    score = score_volatility(
        _make_volatility(squeeze=False, atr_pct=6.0), price=100.0
    )
    assert score == -20.0


def test_volatility_squeeze_bearish_plus_atr_extreme_clamps_to_minus_50() -> None:
    """-30 (squeeze bearish) + -20 (ATR extreme) = -50 (lo bound)."""
    score = score_volatility(
        _make_volatility(squeeze=True, atr_pct=6.0), price=95.0
    )
    assert score == -50.0


def test_volatility_normal_no_squeeze_zero() -> None:
    score = score_volatility(
        _make_volatility(squeeze=False, atr_pct=1.5), price=100.0
    )
    assert score == 0.0


# ─── Futures ───


def _make_futures(
    *,
    funding_rate: float = 0.0,
    oi_change_24h: float = 0.0,
    ls_ratio: float = 1.0,
) -> FuturesIndicators:
    return FuturesIndicators(
        funding=FundingAnalysisResult(
            current_rate=funding_rate,
            avg_24h=funding_rate,
            avg_7d=funding_rate,
            extreme=abs(funding_rate) > 0.0008,
            next_funding_time=0,
        ),
        open_interest=OIChangeResult(
            current=1000.0,
            change_1h_pct=0.0,
            change_4h_pct=0.0,
            change_24h_pct=oi_change_24h,
        ),
        long_short=LongShortAnomalyResult(
            ratio=ls_ratio,
            long_account=ls_ratio / (1 + ls_ratio),
            short_account=1 / (1 + ls_ratio),
            extreme=ls_ratio > 3.0 or ls_ratio < 0.33,
            period="1h",
        ),
    )


def test_futures_extreme_long_squeeze_setup() -> None:
    """Funding çok yüksek + L/S aşırı long → -45 (-30 - 15)."""
    score = score_futures(
        _make_futures(funding_rate=0.001, ls_ratio=4.0),
        price_dir_24h="flat",
    )
    assert score == -45.0


def test_futures_short_squeeze_opportunity() -> None:
    """Funding çok düşük + L/S aşırı short → +45."""
    score = score_futures(
        _make_futures(funding_rate=-0.001, ls_ratio=0.2),
        price_dir_24h="flat",
    )
    assert score == 45.0


def test_futures_oi_price_real_buying() -> None:
    """OI artıyor + price up → +30 (gerçek alım)."""
    score = score_futures(
        _make_futures(oi_change_24h=2.0),
        price_dir_24h="up",
    )
    assert score == 30.0


def test_futures_oi_falling_price_up_short_covering() -> None:
    score = score_futures(
        _make_futures(oi_change_24h=-2.0),
        price_dir_24h="up",
    )
    assert score == 10.0


def test_futures_normal_zero() -> None:
    score = score_futures(_make_futures(), price_dir_24h="flat")
    assert score == 0.0


def test_futures_full_bearish_alignment() -> None:
    """Funding extreme high + OI up + price down + LS extreme high → -75 (-30-30-15)."""
    score = score_futures(
        _make_futures(funding_rate=0.001, oi_change_24h=2.0, ls_ratio=4.0),
        price_dir_24h="down",
    )
    assert score == -75.0
