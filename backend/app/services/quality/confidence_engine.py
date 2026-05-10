"""Confidence Engine — trade_journal'dan setup tipi başına stats.

Olasılık ≠ kanıt seviyesi. Sistem matematiksel olarak "%82 başarı" der ama
o setup tipinde 3 işlem yapıldıysa kanıt zayıftır.

Setup signature: {symbol_category}:{regime}:{base_grade}:{direction}
Örnek: "alt:MIXED:B:long" — sembol bazlı değil, kategori bazlı (cross-symbol stats).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Integer, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.symbols_meta import sector_of
from app.models.symbol import Symbol
from app.models.trade import Trade
from app.schemas.confluence import SymbolType, TradeDirection
from app.schemas.setup_quality import ConfidenceLevel, ConfidenceResult

LOOKBACK_DAYS = 180


def build_signature(
    symbol_category: SymbolType,
    regime: str,
    base_grade: str,
    direction: TradeDirection,
) -> str:
    """Setup imzası — kategori bazlı (BTC için tek imza, alt için tek imza)."""
    return f"{symbol_category}:{regime}:{base_grade}:{direction}"


def _category_to_sql_filter(symbol_category: SymbolType) -> list[str]:
    """SymbolType → matching symbol code listesi (categorize)."""
    if symbol_category == "btc":
        return ["BTCUSDT"]
    if symbol_category == "commodity":
        return ["GOLD"]
    # alt
    from app.data.symbols_meta import ALL_SYMBOLS

    return [s for s in ALL_SYMBOLS if s != "BTCUSDT" and sector_of(s) != "Commodity"]


def _classify_level(n: int) -> tuple[ConfidenceLevel, str, str]:
    """(level, türkçe label, advice)."""
    if n < 5:
        return (
            "VERY_LOW",
            "⚠️ Kanıt yok, deneme aşaması",
            "İlk 5-10 işlem küçük pozisyonla deneyim toplayın",
        )
    if n < 15:
        return (
            "LOW",
            "⚠️ Az veri, dikkatli",
            "Pozisyon boyutunu %50 küçültün",
        )
    if n < 30:
        return (
            "MEDIUM",
            "🟡 Orta kanıt",
            "Normal pozisyon, izlemeye devam",
        )
    if n < 60:
        return (
            "HIGH",
            "🟢 Güçlü kanıt",
            "Tam pozisyon önerilir",
        )
    return (
        "VERY_HIGH",
        "🟢 Çok güçlü kanıt",
        "Bu setup tipinde sistem güvenilir",
    )


class ConfidenceEngine:
    """Public facade.

    Trade tablosu boşken her zaman VERY_LOW döner — future-ready.
    """

    async def compute(
        self,
        session: AsyncSession,
        *,
        symbol_category: SymbolType,
        regime: str,
        base_grade: str,
        direction: TradeDirection,
        user_id: uuid.UUID | None = None,
    ) -> ConfidenceResult:
        signature = build_signature(symbol_category, regime, base_grade, direction)

        # Direction == "neutral" → confidence anlamlı değil ama yine de döndür
        if direction == "neutral":
            level, label, advice = _classify_level(0)
            return ConfidenceResult(
                level=level,
                label=label,
                trade_count=0,
                actual_win_rate=None,
                advice=advice,
                setup_signature=signature,
            )

        # Symbol kategorisinin DB kodlarını al
        symbol_codes = _category_to_sql_filter(symbol_category)
        if not symbol_codes:
            level, label, advice = _classify_level(0)
            return ConfidenceResult(
                level=level,
                label=label,
                trade_count=0,
                actual_win_rate=None,
                advice=advice,
                setup_signature=signature,
            )

        # Query: closed trades, last 180 days, matching signature
        cutoff = datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)
        wins_expr = func.sum(case((Trade.pnl_usd > 0, 1), else_=0)).label("wins")
        stmt = (
            select(
                func.count(Trade.id).label("n"),
                wins_expr,
            )
            .join(Symbol, Trade.symbol_id == Symbol.id)
            .where(
                Trade.status == "closed",
                Trade.entry_time > cutoff,
                Trade.direction == direction,
                Trade.macro_regime_at_entry == regime,
                Trade.setup_quality_at_entry == base_grade,
                Symbol.code.in_(symbol_codes),
            )
        )
        if user_id is not None:
            stmt = stmt.where(Trade.user_id == user_id)

        try:
            row = (await session.execute(stmt)).one()
            n = int(row.n or 0)
            wins = int(row.wins or 0)
        except Exception:
            n = 0
            wins = 0

        win_rate = (wins / n) if n > 0 else None

        level, label, advice = _classify_level(n)

        return ConfidenceResult(
            level=level,
            label=label,
            trade_count=n,
            actual_win_rate=win_rate,
            advice=advice,
            setup_signature=signature,
        )


confidence_engine = ConfidenceEngine()
