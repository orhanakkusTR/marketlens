"""Bollinger Bands (20, 2) + Width + Squeeze tespiti.

Width = (upper - lower) / middle * 100  (yüzde olarak)
Squeeze = current width son 100 mumun en alt %25'inde mi
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pandas_ta as ta

from app.schemas.indicators import BollingerResult


def _resolve_columns(bb_df: pd.DataFrame) -> tuple[str, str, str]:
    """pandas-ta sürümleri kolon adlandırmasında farklı (BBL_20_2.0 / BBL_20_2.0_2.0).
    Prefix'le bul.
    """
    cols = bb_df.columns.tolist()
    upper = next((c for c in cols if c.startswith("BBU_")), None)
    middle = next((c for c in cols if c.startswith("BBM_")), None)
    lower = next((c for c in cols if c.startswith("BBL_")), None)
    if not (upper and middle and lower):
        raise ValueError(f"BB kolonları bulunamadı: {cols}")
    return upper, middle, lower


def _width_series(bb_df: pd.DataFrame) -> pd.Series:
    upper_col, middle_col, lower_col = _resolve_columns(bb_df)
    return ((bb_df[upper_col] - bb_df[lower_col]) / bb_df[middle_col]) * 100


def compute_bollinger(
    df: pd.DataFrame, length: int = 20, std: float = 2.0
) -> BollingerResult:
    bb = ta.bbands(df["close"], length=length, std=std)
    if bb is None or bb.empty:
        raise ValueError("Bollinger Bands hesaplanamadı")

    upper_col, middle_col, lower_col = _resolve_columns(bb)

    if bb[middle_col].dropna().empty:
        raise ValueError("BB middle serisi tamamen NaN")

    upper = float(bb[upper_col].iloc[-1])
    middle = float(bb[middle_col].iloc[-1])
    lower = float(bb[lower_col].iloc[-1])
    width_pct = ((upper - lower) / middle) * 100 if middle > 0 else 0.0

    # Squeeze: son 100 mumun width'ine bak, current bottom 25%'de mi
    width_series = _width_series(bb).dropna().tail(100)
    squeeze = False
    if len(width_series) >= 20:
        threshold = float(np.percentile(width_series.values, 25))
        squeeze = width_pct <= threshold

    return BollingerResult(
        upper=upper,
        middle=middle,
        lower=lower,
        width_pct=width_pct,
        squeeze=squeeze,
    )
