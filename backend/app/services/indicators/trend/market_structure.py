"""Market Structure — HH/HL/LH/LL via ZigZag swing detection.

ZigZag algoritması:
    Her mum için, sol+sağ `lookback` (5) mum içindeki en yüksek/düşük noktalar
    aday swing'lerdir. Pivot high: bar.high == max(window). Pivot low: bar.low == min(window).

Sınıflandırma:
    Önceki swing yüksekten daha yüksek → HH
    Önceki swing yüksekten daha düşük  → LH
    Önceki swing düşükten daha yüksek → HL
    Önceki swing düşükten daha düşük  → LL

Yapı:
    Son 4 swing içinde 2 high + 2 low → HH+HL = uptrend, LH+LL = downtrend, karışık = ranging
"""
from __future__ import annotations

import pandas as pd

from app.schemas.indicators import (
    MarketStructureResult,
    StructureState,
    SwingPoint,
    SwingKind,
)

LOOKBACK = 5  # plan: parametrik değil, sabit


def _detect_pivots(df: pd.DataFrame, lookback: int = LOOKBACK) -> list[SwingPoint]:
    """High/low pivot noktalarını sıralı olarak döndür."""
    if len(df) < 2 * lookback + 1:
        return []

    high = df["high"].values
    low = df["low"].values
    open_time_ms = df["open_time_ms"].values

    swings: list[SwingPoint] = []
    n = len(df)

    prev_high_price: float | None = None
    prev_low_price: float | None = None

    for i in range(lookback, n - lookback):
        window_lo = i - lookback
        window_hi = i + lookback + 1
        h_window = high[window_lo:window_hi]
        l_window = low[window_lo:window_hi]

        # Tek-bar pivot şartı: bar i window'daki maksimum/minimum DEĞER ve
        # bu değere window'da sadece bir kere ulaşılıyor (flat pencere yanılgısını engelle).
        h_max = h_window.max()
        l_min = l_window.min()
        is_pivot_high = high[i] == h_max and int((h_window == h_max).sum()) == 1
        is_pivot_low = low[i] == l_min and int((l_window == l_min).sum()) == 1

        # Aynı mumda hem high hem low pivot olabilir (dar window). Önce high'ı kaydet.
        if is_pivot_high:
            kind: SwingKind = "HH"
            if prev_high_price is not None:
                kind = "HH" if high[i] > prev_high_price else "LH"
            swings.append(
                SwingPoint(
                    index=int(i),
                    timestamp_ms=int(open_time_ms[i]),
                    price=float(high[i]),
                    kind=kind,
                )
            )
            prev_high_price = float(high[i])

        if is_pivot_low:
            kind = "LL"
            if prev_low_price is not None:
                kind = "HL" if low[i] > prev_low_price else "LL"
            swings.append(
                SwingPoint(
                    index=int(i),
                    timestamp_ms=int(open_time_ms[i]),
                    price=float(low[i]),
                    kind=kind,
                )
            )
            prev_low_price = float(low[i])

    # Index'e göre sırala (high+low aynı barda farklı sıraya düşmüş olabilir)
    swings.sort(key=lambda s: s.index)
    return swings


def _classify(swings: list[SwingPoint]) -> StructureState:
    """Son 4 swing'e bakarak yapıyı sınıflandır."""
    if len(swings) < 4:
        return "ranging"

    last = swings[-4:]
    kinds = [s.kind for s in last]

    bullish_count = sum(1 for k in kinds if k in ("HH", "HL"))
    bearish_count = sum(1 for k in kinds if k in ("LH", "LL"))

    if bullish_count >= 3:
        return "uptrend"
    if bearish_count >= 3:
        return "downtrend"
    return "ranging"


def compute_market_structure(df: pd.DataFrame) -> MarketStructureResult:
    swings = _detect_pivots(df, lookback=LOOKBACK)
    structure = _classify(swings)

    last_high = next((s for s in reversed(swings) if s.kind in ("HH", "LH")), None)
    last_low = next((s for s in reversed(swings) if s.kind in ("HL", "LL")), None)

    return MarketStructureResult(
        structure=structure,
        recent_swings=swings[-8:],  # son 8 swing
        last_swing_high=last_high,
        last_swing_low=last_low,
    )
