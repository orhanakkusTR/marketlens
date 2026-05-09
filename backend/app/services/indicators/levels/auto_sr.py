"""Auto Support/Resistance — pivot + Fib + Volume cluster + Round numbers.

Cluster:
    - Tolerance: ±0.3% × current_price (yakın seviyeler birleştirilir)
    - Greedy: en güçlü kaynak etrafında kümeleme

Strength score:
    pivot_high/pivot_low: 1.0 (recent: 1.5)
    fib_0.5 / fib_0.618: 1.5
    fib_0.382 / fib_0.786: 1.0
    fib_ext_*: 1.0
    vp_poc: 3.0
    vp_vah / vp_val: 2.0
    round_major: 1.5
    round_minor: 1.0

Output:
    supports: top 5 < current_price (score'a göre)
    resistances: top 5 > current_price
"""
from __future__ import annotations

import pandas as pd

from app.schemas.indicators import (
    FibonacciResult,
    LevelEntry,
    LevelKind,
    LevelSource,
    LevelsResult,
    MarketStructureResult,
    VolumeProfileResult,
)
from app.services.indicators.levels.round_numbers import round_levels_around

CLUSTER_TOLERANCE_PCT = 0.3
RECENT_PIVOT_COUNT = 30  # Son 30 swing recent sayılır

SOURCE_WEIGHTS: dict[LevelSource, float] = {
    "pivot_high": 1.0,  # default; recent ise 1.5'a yükseltiliyor
    "pivot_low": 1.0,
    "fib_0.382": 1.0,
    "fib_0.5": 1.5,
    "fib_0.618": 1.5,
    "fib_0.786": 1.0,
    "fib_ext_1.272": 1.0,
    "fib_ext_1.618": 1.0,
    "fib_ext_2.618": 1.0,
    "vp_poc": 3.0,
    "vp_vah": 2.0,
    "vp_val": 2.0,
    "round_major": 1.5,
    "round_minor": 1.0,
}


def _gather_raw_levels(
    market_structure: MarketStructureResult,
    fibonacci: FibonacciResult | None,
    volume_profile: VolumeProfileResult,
    current_price: float,
) -> list[tuple[float, LevelSource, float]]:
    """(price, source, weight) tuple listesi üretir."""
    raw: list[tuple[float, LevelSource, float]] = []

    # Pivot high/low — son 50 swing
    swings = market_structure.recent_swings
    n_swings = len(swings)
    for idx, sw in enumerate(swings):
        is_recent = (n_swings - idx) <= RECENT_PIVOT_COUNT
        weight = 1.5 if is_recent else 1.0
        if sw.kind in ("HH", "LH"):
            raw.append((sw.price, "pivot_high", weight))
        else:
            raw.append((sw.price, "pivot_low", weight))

    # Fibonacci — major retracements + extensions
    if fibonacci is not None:
        for level in fibonacci.levels:
            r = level.ratio
            src: LevelSource | None = None
            if level.kind == "retracement":
                if abs(r - 0.382) < 1e-9:
                    src = "fib_0.382"
                elif abs(r - 0.5) < 1e-9:
                    src = "fib_0.5"
                elif abs(r - 0.618) < 1e-9:
                    src = "fib_0.618"
                elif abs(r - 0.786) < 1e-9:
                    src = "fib_0.786"
            else:  # extension
                if abs(r - 1.272) < 1e-9:
                    src = "fib_ext_1.272"
                elif abs(r - 1.618) < 1e-9:
                    src = "fib_ext_1.618"
                elif abs(r - 2.618) < 1e-9:
                    src = "fib_ext_2.618"
            if src is not None:
                raw.append((level.price, src, SOURCE_WEIGHTS[src]))

    # Volume Profile
    raw.append((volume_profile.poc, "vp_poc", SOURCE_WEIGHTS["vp_poc"]))
    raw.append((volume_profile.vah, "vp_vah", SOURCE_WEIGHTS["vp_vah"]))
    raw.append((volume_profile.val, "vp_val", SOURCE_WEIGHTS["vp_val"]))

    # Round numbers — current price ±5%
    for price, src in round_levels_around(current_price, range_pct=5.0):
        raw.append((price, src, SOURCE_WEIGHTS[src]))  # type: ignore[index]

    return raw


def _cluster_levels(
    raw: list[tuple[float, LevelSource, float]],
    current_price: float,
) -> list[LevelEntry]:
    """Yakın seviyeleri birleştir, score topla."""
    if not raw:
        return []

    tolerance = current_price * (CLUSTER_TOLERANCE_PCT / 100)

    # Önce price'a göre sırala
    raw_sorted = sorted(raw, key=lambda x: x[0])

    clusters: list[dict] = []
    for price, src, weight in raw_sorted:
        if clusters and abs(price - clusters[-1]["weighted_price"]) <= tolerance:
            c = clusters[-1]
            c["sources"].append(src)
            c["score"] += weight
            c["total_weight"] += weight
            # Cluster'ın merkezi: weighted average
            c["weighted_price"] = (c["weighted_price"] * (c["total_weight"] - weight) + price * weight) / c["total_weight"]
        else:
            clusters.append(
                {
                    "weighted_price": price,
                    "sources": [src],
                    "score": weight,
                    "total_weight": weight,
                }
            )

    entries: list[LevelEntry] = []
    for c in clusters:
        price = float(c["weighted_price"])
        kind: LevelKind = "support" if price < current_price else "resistance"
        # Aynı source'tan birden fazla pivot olursa confluence_count = unique source sayısı
        unique_sources: list[LevelSource] = []
        seen: set[str] = set()
        for s in c["sources"]:
            if s not in seen:
                unique_sources.append(s)
                seen.add(s)
        entries.append(
            LevelEntry(
                price=price,
                kind=kind,
                sources=unique_sources,
                confluence_count=len(c["sources"]),
                strength_score=float(c["score"]),
            )
        )

    return entries


def compute_levels(
    df: pd.DataFrame,
    market_structure: MarketStructureResult,
    fibonacci: FibonacciResult | None,
    volume_profile: VolumeProfileResult,
    top_n: int = 5,
) -> LevelsResult:
    current_price = float(df["close"].iloc[-1])

    raw = _gather_raw_levels(market_structure, fibonacci, volume_profile, current_price)
    clustered = _cluster_levels(raw, current_price)

    supports = sorted(
        [e for e in clustered if e.price < current_price],
        key=lambda e: e.strength_score,
        reverse=True,
    )[:top_n]
    resistances = sorted(
        [e for e in clustered if e.price >= current_price],
        key=lambda e: e.strength_score,
        reverse=True,
    )[:top_n]

    # Support'ları fiyata göre yakından uzağa sırala (en yakın destek üstte)
    supports.sort(key=lambda e: current_price - e.price)
    resistances.sort(key=lambda e: e.price - current_price)

    return LevelsResult(
        current_price=current_price,
        supports=supports,
        resistances=resistances,
    )
