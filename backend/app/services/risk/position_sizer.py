"""Position Sizer — Adım 15.

Saf hesap modülü. Direction-aware, signed funding, simple liquidation.

Volatility-adjusted formula (build-steps.md):
  |BTC 24h %| > 8  → factor 0.5
  |BTC 24h %| > 5  → factor 0.7
  ATR z-score > 2  → factor 0.7
  default          → factor 1.0

Position size:
  adjusted_risk_pct = base * factor
  risk_amount = balance * adjusted_risk_pct / 100
  stop_distance_pct = |entry - stop| / entry * 100
  position_size_usd = risk_amount / (stop_distance_pct / 100)
  leverage_required = ceil(position_size_usd / balance)
  leverage_actual = min(required, max_leverage)
  margin_used = position_size_usd / leverage_actual

Liquidation (simplified, maintenance margin yok):
  long  : entry * (1 - 1/lev)
  short : entry * (1 + 1/lev)

Funding (direction-aware, signed; 8h period):
  long  + rate > 0 = gider (+)
  long  + rate < 0 = kazanç (-)
  short + rate > 0 = kazanç (-)
  short + rate < 0 = gider (+)
  cost_period = position_size * rate * periods * sign(direction)
"""
from __future__ import annotations

from datetime import UTC, datetime
from math import ceil

from app.schemas.confluence import TradeDirection
from app.schemas.risk import (
    FundingCosts,
    LiquidationPrices,
    PositionRiskResult,
    RiskWarning,
    RRBreakdown,
    VolatilityAdjustment,
)

BTC_VOLATILITY_HIGH = 8.0
BTC_VOLATILITY_MED = 5.0
ATR_ZSCORE_HIGH = 2.0

STOP_TOO_TIGHT_PCT = 0.3

# Futures'ta 1x kaldıraç var olmaz + 1x liquidation formülü entry*0 = 0 üretir
# (edge case bug). Minimum 2x clamp uygulanır.
MIN_LEVERAGE = 2

TP_WEIGHTS: tuple[float, float, float] = (0.40, 0.35, 0.25)

FUNDING_PERIODS_24H = 3  # 8h * 3
FUNDING_PERIODS_72H = 9
FUNDING_PERIODS_1W = 21


def compute_volatility_factor(
    btc_24h_change_pct: float | None,
    atr_zscore: float | None,
) -> VolatilityAdjustment:
    """build-steps.md spec — sırasıyla kontrol, ilk eşleşen kazanır."""
    btc_abs = abs(btc_24h_change_pct) if btc_24h_change_pct is not None else None

    if btc_abs is not None and btc_abs > BTC_VOLATILITY_HIGH:
        return VolatilityAdjustment(
            factor=0.5,
            reason=f"BTC 24h |{btc_24h_change_pct:+.1f}%| > %{BTC_VOLATILITY_HIGH:.0f} — risk yarıya",
            btc_24h_change_pct=btc_24h_change_pct,
            atr_zscore=atr_zscore,
        )
    if btc_abs is not None and btc_abs > BTC_VOLATILITY_MED:
        return VolatilityAdjustment(
            factor=0.7,
            reason=f"BTC 24h |{btc_24h_change_pct:+.1f}%| > %{BTC_VOLATILITY_MED:.0f} — risk %30 düşür",
            btc_24h_change_pct=btc_24h_change_pct,
            atr_zscore=atr_zscore,
        )
    if atr_zscore is not None and atr_zscore > ATR_ZSCORE_HIGH:
        return VolatilityAdjustment(
            factor=0.7,
            reason=f"ATR z-score {atr_zscore:.2f} > {ATR_ZSCORE_HIGH} — risk %30 düşür",
            btc_24h_change_pct=btc_24h_change_pct,
            atr_zscore=atr_zscore,
        )
    return VolatilityAdjustment(
        factor=1.0,
        reason="Normal volatilite — risk tam",
        btc_24h_change_pct=btc_24h_change_pct,
        atr_zscore=atr_zscore,
    )


def _liquidation_prices(
    entry: float, direction: TradeDirection, actual_leverage: int
) -> LiquidationPrices:
    """Basit formül (maintenance margin yok)."""

    def _calc(lev: int) -> float:
        if lev < 1:
            lev = 1
        if direction == "long":
            return entry * (1 - 1 / lev)
        if direction == "short":
            return entry * (1 + 1 / lev)
        return entry  # neutral: tanımsız → entry döner

    return LiquidationPrices(
        at_5x=_calc(5),
        at_10x=_calc(10),
        actual=_calc(actual_leverage),
    )


def _funding_costs(
    position_size_usd: float,
    funding_rate: float,
    direction: TradeDirection,
) -> FundingCosts:
    """Signed: pozitif = gider, negatif = kazanç (kullanıcı pozisyonu yönünden)."""
    # Long + rate > 0 → ödeyen long → gider
    # Short + rate > 0 → kazanan short → kazanç
    sign = 1 if direction == "long" else -1 if direction == "short" else 0
    base = position_size_usd * funding_rate * sign
    return FundingCosts(
        funding_rate=funding_rate,
        h24=base * FUNDING_PERIODS_24H,
        h72=base * FUNDING_PERIODS_72H,
        w1=base * FUNDING_PERIODS_1W,
    )


def _rr_for_target(
    entry: float, stop: float, target: float, direction: TradeDirection
) -> float | None:
    """Direction-aware R/R. Yanlış tarafta hedef → None."""
    risk = abs(entry - stop)
    if risk == 0:
        return None
    if direction == "long":
        reward = target - entry
    elif direction == "short":
        reward = entry - target
    else:
        return None
    if reward <= 0:
        return None
    return reward / risk


def _rr_breakdown(
    entry: float, stop: float, targets: list[float], direction: TradeDirection
) -> RRBreakdown:
    rrs: list[float | None] = []
    for i in range(3):
        if i < len(targets):
            rrs.append(_rr_for_target(entry, stop, targets[i], direction))
        else:
            rrs.append(None)

    # Weighted: TP eksikse mevcut TP'lerin ağırlığı renormalize edilir
    weighted: float | None = None
    valid_pairs = [(rr, w) for rr, w in zip(rrs, TP_WEIGHTS) if rr is not None]
    if valid_pairs:
        total_weight = sum(w for _, w in valid_pairs)
        if total_weight > 0:
            weighted = sum(rr * w for rr, w in valid_pairs) / total_weight

    return RRBreakdown(tp1=rrs[0], tp2=rrs[1], tp3=rrs[2], weighted=weighted)


def _validate_stop_direction(
    entry: float, stop: float, direction: TradeDirection
) -> RiskWarning | None:
    """Long stop entry'nin altında, short stop üstünde olmalı."""
    if direction == "long" and stop >= entry:
        return RiskWarning(
            code="stop_wrong_side",
            severity="blocking",
            message="Long pozisyonda stop entry'nin altında olmalı.",
        )
    if direction == "short" and stop <= entry:
        return RiskWarning(
            code="stop_wrong_side",
            severity="blocking",
            message="Short pozisyonda stop entry'nin üstünde olmalı.",
        )
    return None


def compute_position(
    *,
    symbol: str,
    direction: TradeDirection,
    balance: float,
    base_risk_pct: float,
    entry: float,
    stop: float,
    targets: list[float],
    max_leverage: int,
    funding_rate: float | None = None,
    btc_24h_change_pct: float | None = None,
    atr_zscore: float | None = None,
) -> PositionRiskResult:
    """Tüm pozisyon hesabı — saf fonksiyon."""
    warnings: list[RiskWarning] = []

    # Stop yön kontrolü
    stop_dir_warning = _validate_stop_direction(entry, stop, direction)
    if stop_dir_warning is not None:
        warnings.append(stop_dir_warning)

    # Volatility factor
    vol_adj = compute_volatility_factor(btc_24h_change_pct, atr_zscore)
    adjusted_risk_pct = base_risk_pct * vol_adj.factor

    if vol_adj.factor < 1.0:
        warnings.append(
            RiskWarning(
                code="volatility_reduced",
                severity="info",
                message=f"Risk %{base_risk_pct:.2f} → %{adjusted_risk_pct:.2f} ({vol_adj.reason})",
            )
        )

    risk_amount = balance * adjusted_risk_pct / 100

    stop_distance = abs(entry - stop)
    stop_distance_pct = (stop_distance / entry) * 100 if entry > 0 else 0.0

    if stop_distance_pct < STOP_TOO_TIGHT_PCT:
        warnings.append(
            RiskWarning(
                code="stop_too_tight",
                severity="blocking",
                message=(
                    f"Stop mesafesi %{stop_distance_pct:.3f} < %{STOP_TOO_TIGHT_PCT} — "
                    "noise içinde tetiklenir, daha geniş stop kullan."
                ),
            )
        )
        # Hesabı yine de yap ama position_size aşırı şişer — kullanıcıyı uyar
        position_size_usd = 0.0
        leverage_required = MIN_LEVERAGE
        leverage_actual = MIN_LEVERAGE
        margin_used = 0.0
    else:
        position_size_usd = risk_amount / (stop_distance_pct / 100)
        leverage_required = max(MIN_LEVERAGE, ceil(position_size_usd / balance))
        leverage_actual = max(
            MIN_LEVERAGE, min(leverage_required, max_leverage)
        )
        margin_used = position_size_usd / leverage_actual

        if leverage_required > max_leverage:
            warnings.append(
                RiskWarning(
                    code="leverage_capped",
                    severity="warning",
                    message=(
                        f"Gerekli kaldıraç {leverage_required}x > max {max_leverage}x — "
                        "max'a sabitlendi, fiili risk eşik altında."
                    ),
                )
            )

    # R/R
    rr = _rr_breakdown(entry, stop, targets, direction)
    if not targets:
        warnings.append(
            RiskWarning(
                code="no_targets",
                severity="info",
                message="TP belirtilmedi — R/R hesabı yapılamadı.",
            )
        )
    elif rr.weighted is not None and rr.weighted < 1.0:
        warnings.append(
            RiskWarning(
                code="rr_below_1",
                severity="warning",
                message=f"Weighted R/R {rr.weighted:.2f} < 1.0 — pozisyon risk-ödül açısından zayıf.",
            )
        )

    # Liquidation + funding
    liquidation = _liquidation_prices(entry, direction, leverage_actual)
    funding = _funding_costs(position_size_usd, funding_rate or 0.0, direction)

    return PositionRiskResult(
        symbol=symbol,
        direction=direction,
        entry=entry,
        stop=stop,
        targets=targets,
        balance=balance,
        base_risk_pct=base_risk_pct,
        adjusted_risk_pct=adjusted_risk_pct,
        volatility_adjustment=vol_adj,
        stop_distance_pct=stop_distance_pct,
        risk_amount_usd=risk_amount,
        position_size_usd=position_size_usd,
        leverage_required=leverage_required,
        leverage_actual=leverage_actual,
        margin_used=margin_used,
        liquidation=liquidation,
        funding_costs=funding,
        rr=rr,
        warnings=warnings,
        computed_at=datetime.now(UTC),
    )
