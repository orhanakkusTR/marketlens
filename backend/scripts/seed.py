"""Sembol seed scripti — 27 sembol (26 kripto + GOLD).

Idempotent: var olan sembolleri tekrar eklemez (code unique).

Kullanım:
    docker compose exec backend uv run python scripts/seed.py
"""
from __future__ import annotations

import asyncio
import sys
from typing import TypedDict

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.symbol import AssetType, Sector, Symbol


class SymbolSeed(TypedDict, total=False):
    code: str
    display_name: str
    sector: str
    sort_order: int
    has_futures: bool
    asset_type: str
    quote_currency: str
    exchange: str


# Default değerler — kriptolar için (commodity kendi alanlarını override eder)
_CRYPTO_DEFAULTS = {
    "asset_type": AssetType.CRYPTO.value,
    "quote_currency": "USDT",
    "exchange": "binance",
    "has_futures": True,
}


SYMBOLS: list[SymbolSeed] = [
    # ─── Tier 1 — Major (10) ───
    {"code": "BTCUSDT",  "display_name": "Bitcoin",   "sector": Sector.L1.value,    "sort_order": 1},
    {"code": "ETHUSDT",  "display_name": "Ethereum",  "sector": Sector.L1.value,    "sort_order": 2},
    {"code": "SOLUSDT",  "display_name": "Solana",    "sector": Sector.L1.value,    "sort_order": 3},
    {"code": "BNBUSDT",  "display_name": "BNB",       "sector": Sector.L1.value,    "sort_order": 4},
    {"code": "XRPUSDT",  "display_name": "XRP",       "sector": Sector.OTHER.value, "sort_order": 5},
    {"code": "AVAXUSDT", "display_name": "Avalanche", "sector": Sector.L1.value,    "sort_order": 6},
    {"code": "ADAUSDT",  "display_name": "Cardano",   "sector": Sector.L1.value,    "sort_order": 7},
    {"code": "DOGEUSDT", "display_name": "Dogecoin",  "sector": Sector.MEME.value,  "sort_order": 8},
    # MATIC, Eylül 2024'te POL'a migrate oldu (Polygon). Binance'da POLUSDT pair'i aktif.
    {"code": "POLUSDT",  "display_name": "Polygon",   "sector": Sector.L2.value,    "sort_order": 9},
    {"code": "DOTUSDT",  "display_name": "Polkadot",  "sector": Sector.L1.value,    "sort_order": 10},

    # ─── Tier 2 — Popüler (6) ───
    {"code": "LINKUSDT", "display_name": "Chainlink", "sector": Sector.OTHER.value, "sort_order": 11},
    {"code": "ATOMUSDT", "display_name": "Cosmos",    "sector": Sector.OTHER.value, "sort_order": 12},
    {"code": "NEARUSDT", "display_name": "Near",      "sector": Sector.L1.value,    "sort_order": 13},
    {"code": "APTUSDT",  "display_name": "Aptos",     "sector": Sector.L1.value,    "sort_order": 14},
    {"code": "ARBUSDT",  "display_name": "Arbitrum",  "sector": Sector.L2.value,    "sort_order": 15},
    {"code": "OPUSDT",   "display_name": "Optimism",  "sector": Sector.L2.value,    "sort_order": 16},

    # ─── Tier 3 — Trend/Meme (4) ───
    {"code": "SHIBUSDT", "display_name": "Shiba Inu", "sector": Sector.MEME.value,  "sort_order": 17},
    {"code": "PEPEUSDT", "display_name": "Pepe",      "sector": Sector.MEME.value,  "sort_order": 18},
    {"code": "WIFUSDT",  "display_name": "dogwifhat", "sector": Sector.MEME.value,  "sort_order": 19},
    {"code": "BONKUSDT", "display_name": "Bonk",      "sector": Sector.MEME.value,  "sort_order": 20},

    # ─── Tier 4 — DeFi/sektör (6) ───
    {"code": "UNIUSDT",  "display_name": "Uniswap",   "sector": Sector.DEFI.value,  "sort_order": 21},
    {"code": "AAVEUSDT", "display_name": "Aave",      "sector": Sector.DEFI.value,  "sort_order": 22},
    {"code": "LDOUSDT",  "display_name": "Lido",      "sector": Sector.DEFI.value,  "sort_order": 23},
    {"code": "INJUSDT",  "display_name": "Injective", "sector": Sector.DEFI.value,  "sort_order": 24},
    {"code": "SUIUSDT",  "display_name": "Sui",       "sector": Sector.L1.value,    "sort_order": 25},
    {"code": "SEIUSDT",  "display_name": "Sei",       "sector": Sector.L1.value,    "sort_order": 26},

    # ─── Emtia (1) ───
    {
        "code": "XAUUSD",
        "display_name": "Gold",
        "sector": Sector.COMMODITY.value,
        "sort_order": 27,
        "asset_type": AssetType.COMMODITY.value,
        "quote_currency": "USD",
        "exchange": "yfinance",
        "has_futures": False,
    },
]


def _build_kwargs(seed: SymbolSeed) -> dict[str, object]:
    """Seed dict'ini (kripto default'ları ile birleştirip) Symbol kwargs'a çevir."""
    kwargs: dict[str, object] = {**_CRYPTO_DEFAULTS, **seed}
    return kwargs


async def seed() -> None:
    inserted = 0
    skipped = 0

    async with AsyncSessionLocal() as session:
        # Var olan code'lar (idempotency için)
        existing_result = await session.execute(select(Symbol.code))
        existing_codes = {row[0] for row in existing_result.all()}

        for seed_item in SYMBOLS:
            if seed_item["code"] in existing_codes:
                skipped += 1
                continue
            session.add(Symbol(**_build_kwargs(seed_item)))
            inserted += 1

        await session.commit()

    print(f"✓ Seed tamamlandı — {inserted} yeni, {skipped} atlandı (zaten vardı)")
    print(f"  Beklenen toplam: {len(SYMBOLS)} sembol")


if __name__ == "__main__":
    try:
        asyncio.run(seed())
    except Exception as e:
        print(f"✗ Seed hata: {e}", file=sys.stderr)
        sys.exit(1)
