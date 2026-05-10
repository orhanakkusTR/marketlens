"""Trade Quality Filter — 5 faktör, vasat setup ayıklama.

Confluence yüksek olsa bile bazı setup'lar edge sunmaz. Bu filtre 5 faktör
üzerinden EXCELLENT/GOOD/WEAK/AVOID kararı verir.

Faktörler (Türkçe label):
- "ATR makul"        ATR % > 0.8 (yeterli volatilite)
- "ADX güçlü"        ADX > 20 (trend piyasası, range değil)
- "Macro net"        DXY/SP500 ters yönde (kripto için bullish veya bearish net)
- "Hacim artıyor"    Son 4 mum monotonik artan
- "Yol açık"         En yakın major S/R > 2 ATR uzakta

Verdict & modifier:
  4-5 puan → EXCELLENT  (+1)
  3 puan   → GOOD       (0)
  2 puan   → WEAK       (-1)
  0-1 puan → AVOID      (-2, NO_TRADE override)
"""
from __future__ import annotations

import pandas as pd
import pandas_ta as ta

from app.schemas.indicators import LevelsResult, VolatilityIndicators
from app.schemas.macro import MacroSnapshot
from app.schemas.setup_quality import (
    TradeQualityFactor,
    TradeQualityResult,
    TradeQualityVerdict,
)

ATR_MIN_PCT = 0.8
ADX_MIN = 20.0
VOLUME_GROWTH_BARS = 4
SR_DISTANCE_ATR_MIN = 2.0


def _compute_adx(df: pd.DataFrame, period: int = 14) -> float | None:
    """pandas-ta ADX — inline (schema'ya eklemeden)."""
    if len(df) < period + 1:
        return None
    result = ta.adx(df["high"], df["low"], df["close"], length=period)
    if result is None or result.empty:
        return None
    # Kolon: ADX_14
    col = f"ADX_{period}"
    if col not in result.columns:
        return None
    valid = result[col].dropna()
    if valid.empty:
        return None
    return float(valid.iloc[-1])


def _volume_increasing_n(df: pd.DataFrame, n: int = VOLUME_GROWTH_BARS) -> bool:
    """Son n mum hacim monotonik artıyor mu."""
    if len(df) < n:
        return False
    vols = df["volume"].iloc[-n:].values
    for i in range(1, len(vols)):
        if vols[i] <= vols[i - 1]:
            return False
    return True


def _is_macro_aligned(macro: MacroSnapshot) -> bool:
    """DXY ↓ + SP500 ↑ (kripto bullish) OR DXY ↑ + SP500 ↓ (kripto bearish)."""
    dxy = macro.dxy.change_24h_pct
    spx = macro.sp500.change_24h_pct
    if dxy is None or spx is None:
        return False
    return (dxy < 0 and spx > 0) or (dxy > 0 and spx < 0)


def _nearest_sr_distance_atr(
    levels: LevelsResult, atr_value: float
) -> float | None:
    """En yakın support veya resistance'a ATR cinsinden mesafe."""
    if atr_value <= 0:
        return None
    price = levels.current_price
    candidates: list[float] = []
    for s in levels.supports:
        candidates.append(abs(price - s.price))
    for r in levels.resistances:
        candidates.append(abs(price - r.price))
    if not candidates:
        return None
    return min(candidates) / atr_value


def _verdict_from_score(score: int) -> tuple[TradeQualityVerdict, int]:
    """(verdict, quality_modifier)."""
    if score >= 4:
        return ("EXCELLENT", 1)
    if score >= 3:
        return ("GOOD", 0)
    if score >= 2:
        return ("WEAK", -1)
    return ("AVOID", -2)


class TradeQualityFilter:
    def evaluate(
        self,
        df: pd.DataFrame,
        volatility: VolatilityIndicators,
        levels: LevelsResult,
        macro: MacroSnapshot,
    ) -> TradeQualityResult:
        factors: list[TradeQualityFactor] = []
        score = 0

        # 1. ATR makul
        atr_pct = volatility.atr.value_pct
        atr_passed = atr_pct > ATR_MIN_PCT
        if atr_passed:
            score += 1
        factors.append(
            TradeQualityFactor(
                name="ATR makul",
                passed=atr_passed,
                value=f"ATR %{atr_pct:.2f}",
                note=(
                    "Volatilite yeterli, hareket alanı var"
                    if atr_passed
                    else "Düşük volatilite, hareket yavaş — funding kâr yer"
                ),
            )
        )

        # 2. ADX güçlü
        adx = _compute_adx(df)
        adx_passed = adx is not None and adx > ADX_MIN
        if adx_passed:
            score += 1
        adx_value = f"ADX {adx:.0f}" if adx is not None else "ADX hesaplanamadı"
        factors.append(
            TradeQualityFactor(
                name="ADX güçlü",
                passed=adx_passed,
                value=adx_value,
                note=(
                    "Trend piyasası — trend pozisyonu uygun"
                    if adx_passed
                    else "Range piyasası — trend pozisyonu zayıf, scalping/range stratejisi düşün"
                ),
            )
        )

        # 3. Macro net
        macro_passed = _is_macro_aligned(macro)
        if macro_passed:
            score += 1
        factors.append(
            TradeQualityFactor(
                name="Macro net",
                passed=macro_passed,
                value=None,
                note=(
                    "DXY/SP500 ters yönde — kripto için net sinyal"
                    if macro_passed
                    else "Macro karışık (DXY/SP500 aynı yön) — bağımsızlık yok"
                ),
            )
        )

        # 4. Hacim artıyor
        vol_passed = _volume_increasing_n(df)
        if vol_passed:
            score += 1
        factors.append(
            TradeQualityFactor(
                name="Hacim artıyor",
                passed=vol_passed,
                value=None,
                note=(
                    "Son 4 mum hacim monotonik artıyor — momentum teyitli"
                    if vol_passed
                    else "Hacim yatay/azalıyor — momentum zayıf"
                ),
            )
        )

        # 5. Yol açık
        sr_dist = _nearest_sr_distance_atr(levels, volatility.atr.value_usdt)
        sr_passed = sr_dist is not None and sr_dist > SR_DISTANCE_ATR_MIN
        if sr_passed:
            score += 1
        sr_value = f"{sr_dist:.1f} ATR" if sr_dist is not None else "hesaplanamadı"
        factors.append(
            TradeQualityFactor(
                name="Yol açık",
                passed=sr_passed,
                value=sr_value,
                note=(
                    "En yakın S/R > 2 ATR — hareket alanı temiz"
                    if sr_passed
                    else "Yakın S/R var (<2 ATR) — sıkışık, çıkış zor"
                ),
            )
        )

        verdict, modifier = _verdict_from_score(score)
        return TradeQualityResult(
            score=score,
            verdict=verdict,
            quality_modifier=modifier,
            factors=factors,
        )


trade_quality_filter = TradeQualityFilter()
