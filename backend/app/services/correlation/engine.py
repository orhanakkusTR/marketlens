"""Korelasyon Engine — sembol-arası Pearson r matrix + per-symbol view.

Data sources:
- 26 USDT crypto → Binance 1D klines (kline cache zaten var)
- GOLD → yfinance get_history (period 35d daily)
- DXY/SP500/NASDAQ → yfinance (cross-asset refs)

Algorithm:
- Tüm sembol kapanışlarını DataFrame'de birleştir
- Log returns: log(close[i] / close[i-1])
- pandas.DataFrame.corr() → 27×27 + tradfi matrix

Cache: marketlens:correlation:matrix:{period_days}:{tf}, TTL 1 saat.
"""
from __future__ import annotations

import asyncio
import math
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

from app.core.cache import cached_call
from app.core.logging import get_logger
from app.data.symbols_meta import ALL_SYMBOLS, SECTORS, sector_of
from app.schemas.correlation import (
    CorrelationCategory,
    CorrelationMatrix,
    CorrelationPair,
    CorrelationSign,
    SymbolCorrelations,
)
from app.services.data_service import data_service
from app.services.macro.trends import yfinance_history_to_series

logger = get_logger(__name__)

CACHE_TTL = 3600  # 1 saat
TRADFI_REFS: tuple[str, ...] = ("DXY", "SP500", "NASDAQ")


def _categorize(r: float) -> tuple[CorrelationCategory, CorrelationSign]:
    sign: CorrelationSign = "positive" if r >= 0 else "negative"
    a = abs(r)
    if a > 0.7:
        return ("strong", sign)
    if a >= 0.4:
        return ("moderate", sign)
    if a >= 0.2:
        return ("weak", sign)
    return ("decoupled", sign)


def _compute_log_returns(closes: list[float]) -> list[float]:
    """ln(c2/c1) — eski → yeni sıralı. NaN/sıfır filtrelenir."""
    out: list[float] = []
    for i in range(1, len(closes)):
        c1, c2 = closes[i - 1], closes[i]
        if c1 <= 0 or c2 <= 0:
            out.append(np.nan)
            continue
        out.append(math.log(c2 / c1))
    return out


async def _fetch_crypto_closes(symbol: str, days: int) -> list[tuple[int, float]]:
    """Binance 1D klines → (ts_ms, close)."""
    klines = await data_service.get_klines(symbol, "1D", limit=days + 5)
    return [(int(k["close_time"]), float(k["close"])) for k in klines]


async def _fetch_tradfi_closes(symbol: str, days: int) -> list[tuple[int, float]]:
    period = f"{days + 5}d"
    history = await data_service.get_yfinance_history(symbol, period=period, interval="1d")
    return yfinance_history_to_series(history)


async def _fetch_series(symbol: str, days: int) -> list[tuple[int, float]]:
    """Generic price series fetcher (Binance crypto + XAUUSDT / yfinance tradfi).

    XAUUSDT artık Binance TradFi Perpetual'da; eski yfinance "GOLD" route'u
    macro snapshot için korunuyor (macro/context.py).
    """
    if symbol in TRADFI_REFS:
        return await _fetch_tradfi_closes(symbol, days)
    # Crypto + XAUUSDT (Binance)
    return await _fetch_crypto_closes(symbol, days)


def _series_to_aligned_close_dict(
    series_by_symbol: dict[str, list[tuple[int, float]]],
    days: int,
) -> dict[str, list[float]]:
    """Tüm sembol serilerini son `days` ile pozisyonel hizala.

    Farklı kaynaklar (Binance UTC, yfinance market hours) tam günde
    eşleşmeyebilir. Basitlik: en son `days` kapanışı kullan (pozisyonel).
    """
    aligned: dict[str, list[float]] = {}
    for sym, series in series_by_symbol.items():
        # Son `days` kapanış
        closes = [c for _, c in series][-days:]
        if len(closes) < 5:
            # Çok kısa seri → atla
            continue
        aligned[sym] = closes
    return aligned


def _build_returns_dataframe(aligned: dict[str, list[float]]) -> pd.DataFrame:
    """Log returns DataFrame (kolonlar = sembol, satırlar = günlük return)."""
    # En kısa seriye göre kırp (kolonlar eşit uzunlukta olsun)
    min_len = min(len(c) for c in aligned.values())
    cols = {
        sym: _compute_log_returns(closes[-min_len:])
        for sym, closes in aligned.items()
    }
    return pd.DataFrame(cols)


class CorrelationEngine:
    """Public facade."""

    async def compute_matrix(
        self,
        period_days: int = 30,
        timeframe: str = "1D",
    ) -> CorrelationMatrix:
        """27 sembol + tradfi referansları için korelasyon matrisi."""
        if timeframe != "1D":
            raise ValueError(
                f"Şimdilik sadece 1D timeframe destekleniyor (verildi: {timeframe})"
            )
        if not 7 <= period_days <= 180:
            raise ValueError(f"period_days 7-180 aralığında olmalı (verildi: {period_days})")

        async def fetch() -> dict[str, Any]:
            all_symbols = list(ALL_SYMBOLS) + list(TRADFI_REFS)
            tasks = [_fetch_series(s, period_days) for s in all_symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            series_by_symbol: dict[str, list[tuple[int, float]]] = {}
            for sym, res in zip(all_symbols, results, strict=True):
                if isinstance(res, Exception):
                    logger.warning("correlation_fetch_failed", symbol=sym, error=str(res))
                    continue
                series_by_symbol[sym] = res

            aligned = _series_to_aligned_close_dict(series_by_symbol, period_days)
            returns_df = _build_returns_dataframe(aligned)
            corr_df = returns_df.corr()

            symbols_in_matrix = list(corr_df.columns)
            matrix: dict[str, dict[str, float | None]] = {}
            for sym_a in symbols_in_matrix:
                row: dict[str, float | None] = {}
                for sym_b in symbols_in_matrix:
                    v = corr_df.at[sym_a, sym_b]
                    if pd.isna(v):
                        row[sym_b] = None
                    else:
                        row[sym_b] = float(v)
                matrix[sym_a] = row

            return CorrelationMatrix(
                symbols=symbols_in_matrix,
                matrix=matrix,
                period_days=period_days,
                timeframe=timeframe,
                computed_at=datetime.now(UTC),
            ).model_dump(mode="json")

        raw = await cached_call(
            key=f"correlation:matrix:{period_days}:{timeframe}",
            ttl=CACHE_TTL,
            fetch_fn=fetch,
        )
        return CorrelationMatrix.model_validate(raw)

    async def get_symbol_correlations(
        self,
        symbol: str,
        period_days: int = 30,
        timeframe: str = "1D",
    ) -> SymbolCorrelations:
        """Tek sembol için tüm korelasyonlar + kategorize + sektör avg + tradfi refs."""
        symbol = symbol.upper()
        matrix_obj = await self.compute_matrix(period_days, timeframe)

        if symbol not in matrix_obj.matrix:
            raise ValueError(
                f"Sembol matrixe dahil değil: {symbol} (data fetch başarısız olabilir)"
            )

        row = matrix_obj.matrix[symbol]

        # Diğer sembollerle korelasyonlar (kendisi hariç, tradfi hariç)
        crypto_pairs: list[CorrelationPair] = []
        for other in ALL_SYMBOLS:
            if other == symbol or other not in row:
                continue
            r = row[other]
            if r is None:
                continue
            cat, sign = _categorize(r)
            crypto_pairs.append(
                CorrelationPair(symbol=other, coefficient=r, category=cat, sign=sign)
            )

        # abs(r) desc sıralı
        all_sorted = sorted(crypto_pairs, key=lambda p: abs(p.coefficient), reverse=True)

        strong = [p for p in all_sorted if p.category == "strong"]
        moderate = [p for p in all_sorted if p.category == "moderate"]
        weak = [p for p in all_sorted if p.category == "weak"]
        decoupled = [p for p in all_sorted if p.category == "decoupled"]

        # Sektör avg — kendi sembol katkısı hariç
        by_sector_avg: dict[str, float] = {}
        sector_groups: dict[str, list[float]] = {}
        for p in crypto_pairs:
            sec = sector_of(p.symbol)
            if sec is None:
                continue
            sector_groups.setdefault(sec, []).append(p.coefficient)
        for sec, vals in sector_groups.items():
            by_sector_avg[sec] = float(sum(vals) / len(vals)) if vals else 0.0

        # Cross-asset refs
        def _ref(ref: str) -> float | None:
            if ref == symbol:
                return None
            v = row.get(ref)
            return v if v is not None else None

        return SymbolCorrelations(
            symbol=symbol,
            period_days=period_days,
            timeframe=timeframe,
            all=all_sorted,
            strong=strong,
            moderate=moderate,
            weak=weak,
            decoupled=decoupled,
            by_sector_avg=by_sector_avg,
            vs_btc=_ref("BTCUSDT"),
            vs_eth=_ref("ETHUSDT"),
            vs_dxy=_ref("DXY"),
            vs_sp500=_ref("SP500"),
            computed_at=matrix_obj.computed_at,
        )


correlation_engine = CorrelationEngine()


__all__ = ["CorrelationEngine", "correlation_engine"]
