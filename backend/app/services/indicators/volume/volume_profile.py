"""Volume Profile — POC, VAH, VAL.

Algorithm:
    1. Pencere = TF'ye göre N son mum
    2. Min/max fiyat aralığını N bin'e böl
    3. Her mum için: hacmini (high-low aralığı) içindeki tüm bin'lere uniform dağıt
       (basit yaklaşım: her bin range proportional pay alır)
    4. POC = max hacim bin'inin orta-fiyatı
    5. Value Area: POC'tan dışa doğru, toplam hacmin %70'ine ulaşana kadar bin ekle
    6. VAH/VAL: Value Area'nın üst/alt sınırı
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.schemas.indicators import VolumeProfileResult

# TF'ye göre default pencere bar sayısı (24h proxy)
TF_WINDOW_BARS: dict[str, int] = {
    "15m": 96,   # 24h
    "1H": 24,    # 24h
    "4H": 30,    # ~5 gün (24h çok dar olduğu için)
    "1D": 30,    # 1 ay
    "1W": 26,    # ~6 ay
    "1M": 24,    # 2 yıl
}

DEFAULT_BIN_COUNT = 50
VALUE_AREA_PCT = 0.70


def _pick_window_bars(timeframe: str) -> int:
    return TF_WINDOW_BARS.get(timeframe, 30)


def compute_volume_profile(
    df: pd.DataFrame,
    timeframe: str,
    bin_count: int = DEFAULT_BIN_COUNT,
    window_bars: int | None = None,
) -> VolumeProfileResult:
    n = window_bars if window_bars is not None else _pick_window_bars(timeframe)
    n = min(n, len(df))
    if n < 2:
        raise ValueError(f"Volume Profile için en az 2 mum gerekli, {len(df)} verildi")

    sub = df.tail(n)
    price_min = float(sub["low"].min())
    price_max = float(sub["high"].max())
    if price_max <= price_min:
        raise ValueError("Volume Profile için fiyat aralığı geçersiz")

    edges = np.linspace(price_min, price_max, bin_count + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    bin_volume = np.zeros(bin_count)

    for _, row in sub.iterrows():
        h = float(row["high"])
        low_p = float(row["low"])
        v = float(row["volume"])
        if v <= 0 or h <= low_p:
            continue
        # Mumun range'i içindeki bin'lere uniform dağıt
        # Bin i: edges[i] - edges[i+1]. Mumun bu bin ile kesişimi proportional
        bin_lo = edges[:-1]
        bin_hi = edges[1:]
        overlap_lo = np.maximum(bin_lo, low_p)
        overlap_hi = np.minimum(bin_hi, h)
        overlap = np.maximum(0.0, overlap_hi - overlap_lo)
        candle_range = h - low_p
        weights = overlap / candle_range
        bin_volume += weights * v

    total_volume = float(bin_volume.sum())
    if total_volume <= 0:
        raise ValueError("Volume Profile: toplam hacim 0")

    poc_idx = int(np.argmax(bin_volume))
    poc_price = float(centers[poc_idx])

    # Value Area: POC'tan dışa doğru greedy
    target = total_volume * VALUE_AREA_PCT
    accumulated = float(bin_volume[poc_idx])
    lo_idx = poc_idx
    hi_idx = poc_idx

    while accumulated < target and (lo_idx > 0 or hi_idx < bin_count - 1):
        # Hangi taraf daha çok hacim ekler?
        next_lo = bin_volume[lo_idx - 1] if lo_idx > 0 else -1
        next_hi = bin_volume[hi_idx + 1] if hi_idx < bin_count - 1 else -1
        if next_lo < 0 and next_hi < 0:
            break
        if next_hi >= next_lo:
            hi_idx += 1
            accumulated += float(bin_volume[hi_idx])
        else:
            lo_idx -= 1
            accumulated += float(bin_volume[lo_idx])

    val_price = float(edges[lo_idx])
    vah_price = float(edges[hi_idx + 1])

    return VolumeProfileResult(
        poc=poc_price,
        vah=vah_price,
        val=val_price,
        total_volume=total_volume,
        bin_count=bin_count,
        window_bars=n,
    )
