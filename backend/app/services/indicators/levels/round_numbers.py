"""Round-number level üretimi — sembol bazlı.

Tier'lar (CLAUDE.md kuralı):
    > $10,000      → minor=$1,000, major=$5,000
    $1,000-10,000  → minor=$100,  major=$500
    $100-1,000     → minor=$10,   major=$50
    $10-100        → minor=$1,    major=$5
    $1-10          → minor=$0.10, major=$0.50
    $0.01-1        → minor=$0.01, major=$0.05
    < $0.01        → 5 anlamlı basamak (PEPE/SHIB tarzı)
"""
from __future__ import annotations

import math


def _round_steps(price: float) -> tuple[float, float]:
    """(minor_step, major_step) döner."""
    if price >= 10_000:
        return 1_000.0, 5_000.0
    if price >= 1_000:
        return 100.0, 500.0
    if price >= 100:
        return 10.0, 50.0
    if price >= 10:
        return 1.0, 5.0
    if price >= 1:
        return 0.1, 0.5
    if price >= 0.01:
        return 0.01, 0.05
    # < $0.01: 5 anlamlı basamak — örn. 0.00001234 için 0.00001000
    if price <= 0:
        return 0.0, 0.0
    # 5 anlamlı basamak ölçeği
    digits = int(math.floor(math.log10(price)))
    base = 10.0 ** (digits - 4)  # 5 sig fig: digit + 4 ondalık
    return base, base * 5


def round_levels_around(
    price: float, range_pct: float = 5.0
) -> list[tuple[float, str]]:
    """Current price etrafında ±range_pct yüzde içindeki round level'ları dön.

    Returns: list of (price, kind) — kind ∈ {"round_minor", "round_major"}.
    Major'lar minor'lardan önce gelir (priority).
    """
    if price <= 0:
        return []

    minor_step, major_step = _round_steps(price)
    if minor_step <= 0:
        return []

    band_lo = price * (1 - range_pct / 100)
    band_hi = price * (1 + range_pct / 100)

    levels: list[tuple[float, str]] = []

    # Major
    start_major = math.floor(band_lo / major_step) * major_step
    p = start_major
    while p <= band_hi + 1e-12:
        if band_lo <= p <= band_hi:
            levels.append((p, "round_major"))
        p += major_step

    # Minor (major'a denk gelenleri dahil etme — major skoru zaten alır)
    major_set = {round(p, 8) for p, _ in levels}
    start_minor = math.floor(band_lo / minor_step) * minor_step
    p = start_minor
    while p <= band_hi + 1e-12:
        if band_lo <= p <= band_hi and round(p, 8) not in major_set:
            levels.append((p, "round_minor"))
        p += minor_step

    return levels
