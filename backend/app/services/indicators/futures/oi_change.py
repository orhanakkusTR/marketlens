"""Open Interest yüzde değişim — 1h / 4h / 24h.

Binance OI history 5m granularity → bar count:
    1h  → 12 bar geriye
    4h  → 48 bar geriye
    24h → 288 bar geriye
"""
from __future__ import annotations

from typing import Any

from app.schemas.indicators import OIChangeResult

# 5m bar bazında geriye gitmek için bar sayısı
BARS_1H = 12
BARS_4H = 48
BARS_24H = 288


def _change_pct(history: list[dict[str, Any]], bars_back: int) -> float:
    """En yeni değer ile `bars_back` önceki değer arasındaki yüzde değişim."""
    if len(history) <= bars_back:
        # Yeterli geçmiş yok — referans olarak en eski mevcut bar
        if len(history) < 2:
            return 0.0
        old = float(history[0]["open_interest"])
    else:
        old = float(history[-bars_back - 1]["open_interest"])
    new = float(history[-1]["open_interest"])
    if old <= 0:
        return 0.0
    return ((new - old) / old) * 100


def compute_oi_change(history: list[dict[str, Any]]) -> OIChangeResult:
    if not history:
        raise ValueError("OI history boş — değişim hesaplanamaz")

    current = float(history[-1]["open_interest"])
    return OIChangeResult(
        current=current,
        change_1h_pct=_change_pct(history, BARS_1H),
        change_4h_pct=_change_pct(history, BARS_4H),
        change_24h_pct=_change_pct(history, BARS_24H),
    )
