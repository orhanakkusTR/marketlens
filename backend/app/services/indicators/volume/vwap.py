"""VWAP — Volume Weighted Average Price.

Sadece intraday TF (15m, 1H) için anlamlı — günlük reset.
4H ve üstü için None döner (UI gizler).
"""
from __future__ import annotations

import pandas as pd

from app.schemas.indicators import VWAPResult

INTRADAY_TIMEFRAMES = {"15m", "1H"}


def is_intraday_timeframe(tf: str) -> bool:
    return tf in INTRADAY_TIMEFRAMES


def compute_vwap(df: pd.DataFrame, timeframe: str) -> VWAPResult | None:
    """4H+ için None döner. 15m/1H için son UTC günü reset'iyle hesaplanır."""
    if not is_intraday_timeframe(timeframe):
        return None

    # Son UTC gününün başlangıcını bul (yeni gün = 00:00 UTC)
    last_dt = df.index[-1]
    session_start = last_dt.normalize()  # 00:00 UTC same day
    session_df = df[df.index >= session_start]

    if len(session_df) == 0:
        return None

    typical_price = (session_df["high"] + session_df["low"] + session_df["close"]) / 3
    total_pv = (typical_price * session_df["volume"]).sum()
    total_vol = session_df["volume"].sum()
    if total_vol <= 0:
        return None

    vwap_value = float(total_pv / total_vol)
    price = float(df["close"].iloc[-1])
    distance_pct = ((price - vwap_value) / vwap_value) * 100 if vwap_value > 0 else 0.0
    session_start_ms = int(session_start.value // 1_000_000)

    return VWAPResult(
        value=vwap_value,
        distance_pct=distance_pct,
        session_start_ms=session_start_ms,
    )
