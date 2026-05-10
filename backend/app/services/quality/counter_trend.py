"""Counter-Trend Detector — sistem kendi sinyalini sorgular.

"Kusursuz" görünen setup'lar tuzak olabilir. 6 warning tipi:
- parabolic_move    (high)   |price 2h change| > 3%
- extreme_funding   (high)   |funding| > 0.08%
- extreme_ls_long   (high)   direction=long ve L/S > 3.0
- extreme_ls_short  (high)   direction=short ve L/S < 0.33
- volume_exhaustion (medium) direction=long ve son 3 mum hacim azalıyor
- rsi_stall         (medium) RSI > 75 ve |price 4h change| < 0.5%

Output: severity desc sıralı, max 5 warning.
"""
from __future__ import annotations

import pandas as pd

from app.schemas.confluence import TradeDirection
from app.schemas.indicators import FuturesIndicators, MomentumIndicators
from app.schemas.setup_quality import CounterTrendSeverity, CounterTrendWarning

MAX_WARNINGS = 5
PARABOLIC_THRESHOLD_PCT = 3.0
FUNDING_EXTREME = 0.0008
LS_EXTREME_HIGH = 3.0
LS_EXTREME_LOW = 0.33
VOLUME_EXHAUSTION_BARS = 3
RSI_STALL_LEVEL = 75.0
RSI_STALL_PRICE_THRESHOLD = 0.5

SEVERITY_ORDER: dict[CounterTrendSeverity, int] = {"high": 0, "medium": 1, "low": 2}


def _price_change_pct(df: pd.DataFrame, bars_back: int) -> float | None:
    if len(df) <= bars_back:
        return None
    old = float(df["close"].iloc[-1 - bars_back])
    new = float(df["close"].iloc[-1])
    if old <= 0:
        return None
    return ((new - old) / old) * 100


def _consecutive_volume_decreasing(df: pd.DataFrame) -> int:
    """Son bar'dan geriye doğru ardışık azalan kaç hacim bar'ı var?"""
    if len(df) < 2:
        return 0
    vols = df["volume"].values
    count = 0
    for i in range(len(vols) - 1, 0, -1):
        if vols[i] < vols[i - 1]:
            count += 1
        else:
            break
    return count


def _bars_per_2h(timeframe: str) -> int:
    """TF'ye göre 2h kaç bar'a tekabül eder."""
    return {
        "15m": 8,
        "1H": 2,
        "4H": 1,  # 4H bar zaten 4 saat; tek bar = 4h → 2h için "son tam bar değişimi" yaklaşımı
        "1D": 1,
        "1W": 1,
        "1M": 1,
    }.get(timeframe, 1)


def _bars_per_4h(timeframe: str) -> int:
    return {
        "15m": 16,
        "1H": 4,
        "4H": 1,
        "1D": 1,
        "1W": 1,
        "1M": 1,
    }.get(timeframe, 1)


class CounterTrendDetector:
    def detect(
        self,
        df: pd.DataFrame,
        momentum: MomentumIndicators,
        futures: FuturesIndicators | None,
        direction: TradeDirection,
        timeframe: str,
    ) -> list[CounterTrendWarning]:
        # Neutral direction → sorgu yok
        if direction == "neutral":
            return []

        warnings: list[CounterTrendWarning] = []

        # 1. Parabolik hareket
        price_2h = _price_change_pct(df, _bars_per_2h(timeframe))
        if price_2h is not None and abs(price_2h) > PARABOLIC_THRESHOLD_PCT:
            warnings.append(
                CounterTrendWarning(
                    type="parabolic_move",
                    severity="high",
                    message=f"Son 2 saatte %{price_2h:+.1f} hareket — exhaustion riski",
                    advice="Pullback bekle, FOMO'ya kapılma",
                )
            )

        # 2. Funding ekstrem
        if futures is not None:
            rate = futures.funding.current_rate
            if abs(rate) > FUNDING_EXTREME:
                warnings.append(
                    CounterTrendWarning(
                        type="extreme_funding",
                        severity="high",
                        message=f"Funding {rate * 100:+.3f}% — aşırı kalabalık",
                        advice="Squeeze riski yüksek; counter-trend setup olabilir",
                    )
                )

            # 3 & 4. L/S aşırı (direction'a göre)
            ratio = futures.long_short.ratio
            if direction == "long" and ratio > LS_EXTREME_HIGH:
                warnings.append(
                    CounterTrendWarning(
                        type="extreme_ls_long",
                        severity="high",
                        message=f"L/S {ratio:.2f} — long tarafı sıkışmış",
                        advice="Long açma, contrarian fırsat olabilir",
                    )
                )
            if direction == "short" and ratio < LS_EXTREME_LOW:
                warnings.append(
                    CounterTrendWarning(
                        type="extreme_ls_short",
                        severity="high",
                        message=f"L/S {ratio:.2f} — short tarafı sıkışmış",
                        advice="Short açma, short squeeze riski",
                    )
                )

        # 5. Volume exhaustion (long için)
        if direction == "long":
            dec_count = _consecutive_volume_decreasing(df)
            if dec_count >= VOLUME_EXHAUSTION_BARS:
                warnings.append(
                    CounterTrendWarning(
                        type="volume_exhaustion",
                        severity="medium",
                        message=f"Son {dec_count} mum hacim azalıyor — yükselişte güç kaybı",
                        advice="Hacim teyidi olmadan giriş riskli",
                    )
                )

        # 6. RSI stall (her iki yön için anlamlı)
        price_4h = _price_change_pct(df, _bars_per_4h(timeframe))
        rsi = momentum.rsi.current
        if rsi > RSI_STALL_LEVEL and price_4h is not None and abs(price_4h) < RSI_STALL_PRICE_THRESHOLD:
            warnings.append(
                CounterTrendWarning(
                    type="rsi_stall",
                    severity="medium",
                    message=f"RSI {rsi:.0f} aşırı ama fiyat duruyor — bearish divergence kuruluyor",
                    advice="Aşağı yönlü dönüş riski",
                )
            )

        # Severity desc sıralı + max 5
        warnings.sort(key=lambda w: SEVERITY_ORDER.get(w.severity, 99))
        return warnings[:MAX_WARNINGS]


counter_trend_detector = CounterTrendDetector()
