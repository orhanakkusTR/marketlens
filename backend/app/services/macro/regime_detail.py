"""Piyasa Rejimi detay servisi — Adım 20 polish.

Tek endpoint için composite payload:
- macro_service.get_snapshot() (5dk cache)
- setup_quality_engine.evaluate × 27 (per-symbol 60s cache)

Aggregate cache: 60s.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cached_call
from app.core.logging import get_logger
from app.data.symbols_meta import ALL_SYMBOLS
from app.schemas.macro import MacroSnapshot, MarketRegime
from app.schemas.regime_detail import (
    RegimeDetailResponse,
    RegimeMacroSummary,
    SetupDirectionCounts,
    SetupDistribution,
    SetupGradeCounts,
)
from app.services.macro.context import macro_service
from app.services.macro.regime_narrative import build_detailed_analysis
from app.services.quality.setup_quality import setup_quality_engine

logger = get_logger(__name__)

CACHE_KEY = "macro:regime_detail:v2"  # v2: detailed_analysis_tr eklendi
CACHE_TTL = 60

# ─── Rejim → Türkçe UI başlık ───

_REGIME_LABEL_TR: dict[MarketRegime, str] = {
    "BTC_BULL": "BTC YÜKSELİŞ",
    "ALT_BULL": "ALTSEASON",
    "ALT_SEASON_EARLY": "ALTSEASON BAŞLANGICI",
    "MIXED": "KARARSIZ",
    "RISK_OFF": "RİSK-OFF",
}

# ─── F&G Türkçe ───

def _fg_label_tr(value: int) -> str:
    if value < 25:
        return "Aşırı Korku"
    if value < 45:
        return "Korku"
    if value < 55:
        return "Nötr"
    if value < 75:
        return "Açgözlü"
    return "Aşırı Açgözlü"


def _tradfi_signal(snapshot: MacroSnapshot) -> str:
    """DXY (ters yön) + SP500 (aynı yön) + VIX (ters yön) → bullish/neutral/bearish."""
    score = 0
    dxy = snapshot.dxy.change_24h_pct
    if dxy is not None:
        if dxy < -0.5:
            score += 1
        elif dxy > 0.5:
            score -= 1
    sp500 = snapshot.sp500.change_24h_pct
    if sp500 is not None:
        if sp500 > 0.3:
            score += 1
        elif sp500 < -0.3:
            score -= 1
    vix = snapshot.vix.change_24h_pct
    if vix is not None:
        if vix < -3:
            score += 1
        elif vix > 3:
            score -= 1
    if score >= 1:
        return "bullish"
    if score <= -1:
        return "bearish"
    return "neutral"


# ─── Setup evaluation ───

async def _evaluate_one(
    symbol: str, timeframe: str, session: AsyncSession, user_id: Any
) -> dict[str, Any] | None:
    """Tek sembol; exception → None (sayım dışında kalır)."""
    try:
        result = await setup_quality_engine.evaluate(
            symbol, timeframe, session=session, user_id=user_id
        )
        return result.model_dump(mode="json")
    except Exception as e:
        logger.debug(
            "regime_detail_symbol_failed", symbol=symbol, error=str(e)
        )
        return None


def _build_distribution(
    payloads: list[dict[str, Any] | None],
) -> tuple[SetupDistribution, int]:
    """Sayım + counter_trend high count (warnings için)."""
    grades = SetupGradeCounts()
    directions = SetupDirectionCounts()
    counter_trend_high = 0

    for payload in payloads:
        if payload is None:
            grades.none += 1
            directions.none += 1
            continue

        grade = payload.get("grade")
        if grade in ("A", "B", "C", "D", "NO_TRADE"):
            setattr(grades, grade, getattr(grades, grade) + 1)
        else:
            grades.none += 1

        direction = payload.get("direction")
        if direction in ("long", "short", "neutral"):
            setattr(directions, direction, getattr(directions, direction) + 1)
        else:
            directions.none += 1

        # Counter-trend high warning sayımı
        for w in payload.get("counter_trend_warnings", []) or []:
            if w.get("severity") == "high":
                counter_trend_high += 1
                break  # sembol başına sadece 1 say

    distribution = SetupDistribution(
        grade_counts=grades,
        direction_counts=directions,
        total_symbols=len(payloads),
    )
    return distribution, counter_trend_high


# ─── Weekend logic ───

def _weekend_message_tr(now: datetime) -> str | None:
    """CLAUDE.md spec: weekend window Cuma 22:00 UTC → Pzt 02:00 UTC.
    Yaklaşma: Cuma 14:00–22:00 UTC.
    """
    day = now.weekday()  # 0=Mon ... 4=Fri 5=Sat 6=Sun
    hour = now.hour

    # Aktif
    if (
        (day == 4 and hour >= 22)
        or day == 5
        or day == 6
        or (day == 0 and hour < 2)
    ):
        return "Hafta sonu aktif — kripto'da düşük likidite, dikkat"

    # Yaklaşıyor (Cuma 14:00 sonrası, 22:00'a kadar)
    if day == 4 and 14 <= hour < 22:
        hours_to_close = 22 - hour
        return f"Hafta sonu yaklaşıyor (~{hours_to_close} saat)"

    return None


# ─── Warnings sentezi (max 3) ───

def _build_warnings(
    snapshot: MacroSnapshot,
    counter_trend_high_count: int,
    now: datetime,
) -> list[str]:
    msgs: list[str] = []

    # 1. Parabolik (counter-trend high)
    if counter_trend_high_count >= 3:
        msgs.append(f"{counter_trend_high_count} sembolde parabolik hareket")

    # 2. Hafta sonu
    weekend = _weekend_message_tr(now)
    if weekend:
        msgs.append(weekend)

    # 3. F&G ekstrem
    fg = snapshot.fear_greed.value
    if fg < 25:
        msgs.append("F&G Aşırı Korku — contrarian fırsat olabilir")
    elif fg > 75:
        msgs.append("F&G Aşırı Açgözlü — düzeltme riski")

    # 4. BTC.D yüksek
    if snapshot.crypto_caps.btc_dominance > 60:
        msgs.append("BTC.D yüksek — altcoinler baskı altında")

    # 5. DXY güçleniyor
    dxy_pct = snapshot.dxy.change_24h_pct
    if dxy_pct is not None and dxy_pct > 0.5:
        msgs.append("DXY güçleniyor — kripto'ya baskı")

    return msgs[:3]


# ─── Strategy (rejim + setup distribution → dinamik) ───

def _build_strategy(
    regime: MarketRegime, distribution: SetupDistribution
) -> str:
    a_count = distribution.grade_counts.A

    if regime == "MIXED":
        if a_count == 0:
            return "A-setup yok — bekle, küçük pozisyon dene"
        if a_count <= 2:
            return "Seçici ol, sadece A-B kalite + macro destekli setup'lar"
        return "Birkaç fırsat var, A-B setup'larda küçük pozisyon"

    if regime == "BTC_BULL":
        return "BTC ve major'larda long, altcoin'lerden kaçın"
    if regime == "ALT_BULL":
        return "Altcoin long fırsatları, agresif olabilirsin"
    if regime == "ALT_SEASON_EARLY":
        return "Kademeli altcoin long, ihtiyatlı agresiflik"
    # RISK_OFF
    return "Bekle veya short fırsatları ara, sermayeni koru"


# ─── Public service ───

async def build_regime_detail(
    session: AsyncSession, user_id: Any = None, timeframe: str = "4H"
) -> RegimeDetailResponse:
    """Composite payload — kendi cache'i 60s."""

    user_key = str(user_id) if user_id is not None else "anonymous"
    cache_key = f"{CACHE_KEY}:{timeframe}:{user_key}"

    async def _build() -> dict[str, Any]:
        snapshot = await macro_service.get_snapshot()

        # 27 sembol paralel evaluate
        tasks = [
            _evaluate_one(sym, timeframe, session, user_id)
            for sym in ALL_SYMBOLS
        ]
        payloads = await asyncio.gather(*tasks, return_exceptions=False)

        distribution, ct_high = _build_distribution(payloads)
        now = datetime.now(UTC)
        warnings = _build_warnings(snapshot, ct_high, now)
        strategy = _build_strategy(snapshot.market_regime.regime, distribution)

        macro_summary = RegimeMacroSummary(
            btc_trend_7d_pct=snapshot.btc_market_cap.change_7d_pct,
            eth_btc_change_pct=snapshot.eth_btc_ratio.change_7d_pct,
            btc_dominance=snapshot.crypto_caps.btc_dominance,
            fear_greed_value=snapshot.fear_greed.value,
            fear_greed_label_tr=_fg_label_tr(snapshot.fear_greed.value),
            tradfi_signal=_tradfi_signal(snapshot),
        )

        detailed = build_detailed_analysis(
            regime=snapshot.market_regime.regime,
            distribution=distribution,
            macro=macro_summary,
            now=now,
        )

        response = RegimeDetailResponse(
            regime=snapshot.market_regime.regime,
            regime_label_tr=_REGIME_LABEL_TR.get(
                snapshot.market_regime.regime, snapshot.market_regime.regime
            ),
            reasoning_tr=snapshot.market_regime.label,
            macro_summary=macro_summary,
            setup_distribution=distribution,
            warnings_tr=warnings,
            strategy_tr=strategy,
            detailed_analysis_tr=detailed,
            computed_at=now,
        )
        return response.model_dump(mode="json")

    raw = await cached_call(key=cache_key, ttl=CACHE_TTL, fetch_fn=_build)
    return RegimeDetailResponse.model_validate(raw)
