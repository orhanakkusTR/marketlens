"""OBV — On-Balance Volume.

Slope: son 20 mumun OBV trend yönü (linear regression slope işareti).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pandas_ta as ta

from app.schemas.indicators import OBVResult, VolumeSlope


def _slope(values: np.ndarray) -> float:
    """Basit lineer regresyon eğimi."""
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values), dtype=float)
    # numpy lstsq: y = m*x + b
    a = np.vstack([x, np.ones_like(x)]).T
    m, _ = np.linalg.lstsq(a, values, rcond=None)[0]
    return float(m)


def compute_obv(df: pd.DataFrame, slope_window: int = 20) -> OBVResult:
    series = ta.obv(df["close"], df["volume"])
    if series is None or series.dropna().empty:
        raise ValueError("OBV hesaplanamadı")

    current = float(series.iloc[-1])

    tail = series.tail(slope_window).values
    raw_slope = _slope(tail)
    # Threshold: tail'in standart sapmasına göre küçük slope'u flat say
    std = float(np.std(tail)) if len(tail) > 1 else 0.0
    threshold = std * 0.05  # %5 std → noise zone

    slope: VolumeSlope
    if raw_slope > threshold:
        slope = "rising"
    elif raw_slope < -threshold:
        slope = "falling"
    else:
        slope = "flat"

    return OBVResult(current=current, slope=slope)
