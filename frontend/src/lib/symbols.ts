/**
 * 27 sembol tier başlıklarıyla — backend symbols_meta.py ile aynı.
 *
 * Tek source of truth (frontend tarafı); ileride backend'den fetch edilebilir.
 */

export interface SymbolTier {
  title: string;
  symbols: ReadonlyArray<string>;
}

export const SYMBOL_TIERS: ReadonlyArray<SymbolTier> = [
  {
    title: "Tier 1 — Major",
    symbols: [
      "BTCUSDT",
      "ETHUSDT",
      "SOLUSDT",
      "BNBUSDT",
      "XRPUSDT",
      "AVAXUSDT",
      "ADAUSDT",
      "DOGEUSDT",
      "POLUSDT",
      "DOTUSDT",
    ],
  },
  {
    title: "Tier 2 — Popüler",
    symbols: ["LINKUSDT", "ATOMUSDT", "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT"],
  },
  {
    title: "Tier 3 — Meme",
    symbols: ["SHIBUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT"],
  },
  {
    title: "Tier 4 — DeFi",
    symbols: ["UNIUSDT", "AAVEUSDT", "LDOUSDT", "INJUSDT", "SUIUSDT", "SEIUSDT"],
  },
  {
    title: "Emtia",
    symbols: ["XAUUSDT"],
  },
];

export const ALL_SYMBOLS: ReadonlyArray<string> = SYMBOL_TIERS.flatMap(
  (t) => t.symbols
);
