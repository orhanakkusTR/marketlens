"""Sembol metadata helper'ı (in-memory).

DB-driven hale getirmek için ileride `services/symbol_service.py` yazılır,
ama bu adım için Python-side sabit liste yeterli (seed.py ile aynı kaynak truth).
"""
from __future__ import annotations

# Binance USDT-Futures destekleyen sembollerimiz (seed.py ile birebir).
# GOLD/XAUUSD futures yok → has_futures=False.
SYMBOLS_WITH_FUTURES: frozenset[str] = frozenset(
    {
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "AVAXUSDT",
        "ADAUSDT", "DOGEUSDT", "POLUSDT", "DOTUSDT", "LINKUSDT", "ATOMUSDT",
        "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "SHIBUSDT", "PEPEUSDT",
        "WIFUSDT", "BONKUSDT", "UNIUSDT", "AAVEUSDT", "LDOUSDT", "INJUSDT",
        "SUIUSDT", "SEIUSDT",
    }
)


def has_futures(symbol: str) -> bool:
    """Sembol için futures verisi var mı (funding/OI/L-S)."""
    return symbol.upper() in SYMBOLS_WITH_FUTURES
