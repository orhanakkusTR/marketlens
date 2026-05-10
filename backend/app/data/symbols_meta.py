"""Sembol metadata helper'ı (in-memory).

DB-driven hale getirmek için ileride `services/symbol_service.py` yazılır,
ama bu adım için Python-side sabit liste yeterli (seed.py ile aynı kaynak truth).
"""
from __future__ import annotations

# Binance USDT-Futures destekleyen sembollerimiz (seed.py ile birebir).
# Ocak 2026: Binance TradFi Perpetual Contracts başlattı → XAUUSDT artık futures destekli.
SYMBOLS_WITH_FUTURES: frozenset[str] = frozenset(
    {
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "AVAXUSDT",
        "ADAUSDT", "DOGEUSDT", "POLUSDT", "DOTUSDT", "LINKUSDT", "ATOMUSDT",
        "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "SHIBUSDT", "PEPEUSDT",
        "WIFUSDT", "BONKUSDT", "UNIUSDT", "AAVEUSDT", "LDOUSDT", "INJUSDT",
        "SUIUSDT", "SEIUSDT",
        "XAUUSDT",  # Binance TradFi Perpetual (Ocak 2026)
    }
)

# CLAUDE.md sektör mapping'i — 27 sembol (26 kripto + XAUUSDT/Commodity).
# Frontend filter, korelasyon sektör avg, rotation tracker (Adım 26) bu mapping'i kullanır.
SECTORS: dict[str, str] = {
    # L1
    "BTCUSDT": "L1", "ETHUSDT": "L1", "SOLUSDT": "L1", "BNBUSDT": "L1",
    "AVAXUSDT": "L1", "ADAUSDT": "L1", "DOTUSDT": "L1", "NEARUSDT": "L1",
    "APTUSDT": "L1", "SUIUSDT": "L1", "SEIUSDT": "L1",
    # L2
    "ARBUSDT": "L2", "OPUSDT": "L2", "POLUSDT": "L2",
    # DeFi
    "UNIUSDT": "DeFi", "AAVEUSDT": "DeFi", "LDOUSDT": "DeFi", "INJUSDT": "DeFi",
    # Meme
    "DOGEUSDT": "Meme", "SHIBUSDT": "Meme", "PEPEUSDT": "Meme",
    "WIFUSDT": "Meme", "BONKUSDT": "Meme",
    # Other
    "XRPUSDT": "Other", "LINKUSDT": "Other", "ATOMUSDT": "Other",
    # Commodity — XAUUSDT (Binance TradFi Perpetual; Ocak 2026)
    "XAUUSDT": "Commodity",
}

ALL_SYMBOLS: tuple[str, ...] = tuple(SECTORS.keys())  # 27 sembol


def has_futures(symbol: str) -> bool:
    """Sembol için futures verisi var mı (funding/OI/L-S)."""
    return symbol.upper() in SYMBOLS_WITH_FUTURES


def sector_of(symbol: str) -> str | None:
    """Sembolün sektörü. Bilinmiyorsa None."""
    return SECTORS.get(symbol.upper())
