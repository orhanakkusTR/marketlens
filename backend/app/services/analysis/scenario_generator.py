"""Scenario Generator — Adım 16.

Direction-aware auto entry/stop/TP üretici.

Stop logic:
  - Long: candidates = supports (current_price'tan küçük, asc by distance)
  - Short: candidates = resistances (current_price'tan büyük, asc by distance)
  - İlk uygun level (0.5 ≤ distance_atr ≤ 3.0) seçilir
  - Buffer: level ∓ 0.5 ATR (level'in dışında — long'da altta, short'ta üstte)
  - Hiç uygun level yoksa: ATR × 1.5 fallback

TP logic:
  - Long: resistances; Short: supports
  - R/R ≥ 1.0 filtresi (kötü TP atılır)
  - Cluster prevention: ardışık TP'ler arası ≥ 0.5 ATR
  - 3 TP yoksa fallback: ATR × 2 / 4 / 6 progression

Entry: current_price ± 0.3 ATR band (slippage buffer).

Output: Türkçe reasoning + structured schemas.
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.core.logging import get_logger
from app.schemas.confluence import TradeDirection
from app.schemas.indicators import LevelEntry, LevelsResult
from app.schemas.scenario import (
    EntryBand,
    ScenarioResult,
    StopLevel,
    TPLevel,
)

logger = get_logger(__name__)

# ─── Tunables ───
ENTRY_BAND_HALF_ATR = 0.3
STOP_BUFFER_ATR = 0.5
STOP_LEVEL_MIN_DISTANCE_ATR = 0.5
STOP_LEVEL_MAX_DISTANCE_ATR = 3.0
STOP_FALLBACK_ATR_MULTIPLIER = 1.5

TP_CLUSTER_MIN_GAP_ATR = 0.5
TP_RR_MIN = 1.0
TP_FALLBACK_ATR_MULTIPLIERS: tuple[int, int, int] = (2, 4, 6)
TP_FALLBACK_STEP_ATR = 2.0  # Mevcut level üzerine ardışık fallback için ATR step
TP_MAX_COUNT = 3

# R/R weighted ağırlıklar — position_sizer ile aynı
TP_WEIGHTS: tuple[float, float, float] = (0.40, 0.35, 0.25)


def _select_stop_long(
    current_price: float, atr: float, supports: list[LevelEntry]
) -> StopLevel:
    """Long stop: en yakın uygun support - 0.5 ATR buffer; fallback ATR×1.5."""
    for s in supports:
        if s.price >= current_price:
            continue
        distance = current_price - s.price
        distance_atr = distance / atr
        if STOP_LEVEL_MIN_DISTANCE_ATR <= distance_atr <= STOP_LEVEL_MAX_DISTANCE_ATR:
            stop_price = s.price - STOP_BUFFER_ATR * atr
            stop_dist = current_price - stop_price
            sources = " + ".join(s.sources) if s.sources else "level"
            return StopLevel(
                price=stop_price,
                source=f"support level ({sources})",
                distance_atr=stop_dist / atr,
                distance_pct=(stop_dist / current_price) * 100,
                reasoning=(
                    f"En yakın uygun support ${s.price:.4g} "
                    f"({distance_atr:.2f} ATR mesafe) altında 0.5 ATR buffer."
                ),
            )

    # Fallback
    stop_price = current_price - STOP_FALLBACK_ATR_MULTIPLIER * atr
    stop_dist = current_price - stop_price
    return StopLevel(
        price=stop_price,
        source=f"ATR×{STOP_FALLBACK_ATR_MULTIPLIER} fallback",
        distance_atr=stop_dist / atr,
        distance_pct=(stop_dist / current_price) * 100,
        reasoning=(
            "Uygun support level yok (yakın <0.5 ATR veya uzak >3 ATR) — "
            f"ATR×{STOP_FALLBACK_ATR_MULTIPLIER} kullanıldı."
        ),
    )


def _select_stop_short(
    current_price: float, atr: float, resistances: list[LevelEntry]
) -> StopLevel:
    """Short stop: en yakın uygun resistance + 0.5 ATR buffer; fallback ATR×1.5."""
    for r in resistances:
        if r.price <= current_price:
            continue
        distance = r.price - current_price
        distance_atr = distance / atr
        if STOP_LEVEL_MIN_DISTANCE_ATR <= distance_atr <= STOP_LEVEL_MAX_DISTANCE_ATR:
            stop_price = r.price + STOP_BUFFER_ATR * atr
            stop_dist = stop_price - current_price
            sources = " + ".join(r.sources) if r.sources else "level"
            return StopLevel(
                price=stop_price,
                source=f"resistance level ({sources})",
                distance_atr=stop_dist / atr,
                distance_pct=(stop_dist / current_price) * 100,
                reasoning=(
                    f"En yakın uygun resistance ${r.price:.4g} "
                    f"({distance_atr:.2f} ATR mesafe) üstünde 0.5 ATR buffer."
                ),
            )

    stop_price = current_price + STOP_FALLBACK_ATR_MULTIPLIER * atr
    stop_dist = stop_price - current_price
    return StopLevel(
        price=stop_price,
        source=f"ATR×{STOP_FALLBACK_ATR_MULTIPLIER} fallback",
        distance_atr=stop_dist / atr,
        distance_pct=(stop_dist / current_price) * 100,
        reasoning=(
            "Uygun resistance level yok (yakın <0.5 ATR veya uzak >3 ATR) — "
            f"ATR×{STOP_FALLBACK_ATR_MULTIPLIER} kullanıldı."
        ),
    )


def _rr_for_tp(
    direction: TradeDirection,
    entry_mid: float,
    stop_price: float,
    tp_price: float,
) -> float:
    risk = abs(entry_mid - stop_price)
    if risk == 0:
        return 0.0
    if direction == "long":
        reward = tp_price - entry_mid
    else:  # short
        reward = entry_mid - tp_price
    if reward <= 0:
        return 0.0
    return reward / risk


def _select_targets(
    direction: TradeDirection,
    current_price: float,
    entry_mid: float,
    stop_price: float,
    atr: float,
    levels: list[LevelEntry],
) -> list[TPLevel]:
    """Level'lerden 3 TP seçer + cluster prevention + fallback."""
    candidates: list[LevelEntry] = []
    if direction == "long":
        candidates = [lv for lv in levels if lv.price > current_price]
        candidates.sort(key=lambda lv: lv.price - current_price)
    elif direction == "short":
        candidates = [lv for lv in levels if lv.price < current_price]
        candidates.sort(key=lambda lv: current_price - lv.price)

    selected: list[TPLevel] = []
    for lv in candidates:
        if len(selected) >= TP_MAX_COUNT:
            break
        rr = _rr_for_tp(direction, entry_mid, stop_price, lv.price)
        if rr < TP_RR_MIN:
            continue
        # Cluster prevention
        if selected and abs(lv.price - selected[-1].price) < TP_CLUSTER_MIN_GAP_ATR * atr:
            continue
        distance = abs(lv.price - entry_mid)
        sources = " + ".join(lv.sources) if lv.sources else "level"
        selected.append(
            TPLevel(
                price=lv.price,
                source=f"{lv.kind} level ({sources})",
                distance_atr=distance / atr,
                distance_pct=(distance / entry_mid) * 100,
                rr=rr,
                reasoning=(
                    f"{lv.kind.capitalize()} ${lv.price:.4g}, {sources}, "
                    f"R/R {rr:.2f}."
                ),
            )
        )

    # Fallback: 3'e tamamla — son selected'tan progression (sıralı kalmasını garanti et)
    while len(selected) < TP_MAX_COUNT:
        idx = len(selected)
        if selected:
            # Ardışık fallback: son TP'den TP_FALLBACK_STEP_ATR uzak
            step = TP_FALLBACK_STEP_ATR * atr
            if direction == "long":
                tp_price = selected[-1].price + step
            else:
                tp_price = selected[-1].price - step
            source = f"son TP'den +{TP_FALLBACK_STEP_ATR} ATR (fallback)"
            multiplier_note = f"+{TP_FALLBACK_STEP_ATR} ATR"
        else:
            # İlk fallback: current_price'tan multiplier ATR uzak
            multiplier = TP_FALLBACK_ATR_MULTIPLIERS[idx]
            if direction == "long":
                tp_price = current_price + multiplier * atr
            else:
                tp_price = current_price - multiplier * atr
            source = f"ATR×{multiplier} fallback"
            multiplier_note = f"ATR×{multiplier}"

        rr = _rr_for_tp(direction, entry_mid, stop_price, tp_price)
        distance = abs(tp_price - entry_mid)
        selected.append(
            TPLevel(
                price=tp_price,
                source=source,
                distance_atr=distance / atr,
                distance_pct=(distance / entry_mid) * 100,
                rr=rr,
                reasoning=(
                    f"Level yetersiz — {multiplier_note} fallback ({rr:.2f}R)."
                ),
            )
        )

    return selected


def _weighted_rr(targets: list[TPLevel]) -> float | None:
    """0.40*tp1 + 0.35*tp2 + 0.25*tp3 (mevcut TP'ler renormalize)."""
    if not targets:
        return None
    weights = TP_WEIGHTS[: len(targets)]
    total_weight = sum(weights)
    if total_weight <= 0:
        return None
    return sum(t.rr * w for t, w in zip(targets, weights)) / total_weight


def _build_reasoning(
    *,
    direction: TradeDirection,
    entry: EntryBand,
    stop: StopLevel,
    targets: list[TPLevel],
    weighted_rr: float | None,
    final_confluence: float,
) -> str:
    direction_tr = "Long" if direction == "long" else "Short"
    parts: list[str] = []
    parts.append(
        f"{direction_tr} senaryo (final confluence {final_confluence:+.1f}). "
        f"Entry ${entry.mid:.4g} (±0.3 ATR band)."
    )
    parts.append(
        f"Stop ${stop.price:.4g} — {stop.source}, {stop.distance_pct:.2f}% mesafe."
    )
    if targets:
        tp_summary = ", ".join(
            f"TP{i+1} ${t.price:.4g} ({t.rr:.2f}R)" for i, t in enumerate(targets)
        )
        parts.append(tp_summary + ".")
    if weighted_rr is not None:
        parts.append(f"Weighted R/R: {weighted_rr:.2f}.")
    return " ".join(parts)


def generate_scenario(
    *,
    symbol: str,
    timeframe: str,
    direction: TradeDirection,
    current_price: float,
    atr: float,
    levels: LevelsResult,
    final_confluence: float,
) -> ScenarioResult | None:
    """Direction-aware senaryo. Neutral → None."""
    if direction == "neutral":
        return None
    if atr <= 0 or current_price <= 0:
        return None

    entry = EntryBand(
        low=current_price - ENTRY_BAND_HALF_ATR * atr,
        mid=current_price,
        high=current_price + ENTRY_BAND_HALF_ATR * atr,
        width_atr=ENTRY_BAND_HALF_ATR * 2,
    )

    if direction == "long":
        stop = _select_stop_long(current_price, atr, list(levels.supports))
        tp_source_levels = list(levels.resistances)
    else:  # short
        stop = _select_stop_short(current_price, atr, list(levels.resistances))
        tp_source_levels = list(levels.supports)

    targets = _select_targets(
        direction=direction,
        current_price=current_price,
        entry_mid=entry.mid,
        stop_price=stop.price,
        atr=atr,
        levels=tp_source_levels,
    )

    weighted = _weighted_rr(targets)

    reasoning = _build_reasoning(
        direction=direction,
        entry=entry,
        stop=stop,
        targets=targets,
        weighted_rr=weighted,
        final_confluence=final_confluence,
    )

    return ScenarioResult(
        symbol=symbol,
        timeframe=timeframe,
        direction=direction,  # type: ignore[arg-type]  # neutral already filtered out
        entry=entry,
        stop=stop,
        targets=targets,
        rr_weighted=weighted,
        final_confluence=final_confluence,
        reasoning=reasoning,
        computed_at=datetime.now(UTC),
    )
