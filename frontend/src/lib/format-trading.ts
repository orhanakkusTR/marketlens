/**
 * Trading-specific formatters — Adım 21.
 *
 * USD para (komma + decimals), signed percent, leverage, ATR units, küçük helpers.
 */

const USD = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
});

/** "$4,200.00" — para birimi varsayılan 2 ondalık. */
export function formatMoney(n: number): string {
  return USD.format(n);
}

/** "+0.46%" / "-1.20%" — işaretli yüzde. */
export function formatPctSigned(n: number, decimals = 2): string {
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(decimals)}%`;
}

/** "1.20%" / "2.50%" — işaretsiz yüzde (mesafe için). */
export function formatPct(n: number, decimals = 2): string {
  return `${n.toFixed(decimals)}%`;
}

/** "2x" / "10x" — kaldıraç. */
export function formatLeverage(n: number, decimals = 1): string {
  return `${n.toFixed(decimals)}x`;
}

/** "1.54 ATR" — ATR mesafe. */
export function formatATR(n: number): string {
  return `${n.toFixed(2)} ATR`;
}

/** "+$0.24" / "-$1.50" — işaretli para (funding için). */
export function formatMoneySigned(n: number): string {
  const sign = n >= 0 ? "+" : "−";
  return `${sign}${USD.format(Math.abs(n))}`;
}

/** "0.0025%" — funding rate (küçük yüzde). */
export function formatFundingRate(rate: number): string {
  const pct = rate * 100;
  return `${pct >= 0 ? "+" : ""}${pct.toFixed(4)}%`;
}

/** Plain number, no currency — "5,180". */
export function formatNumber(n: number, decimals = 0): string {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: decimals,
    minimumFractionDigits: decimals,
  }).format(n);
}

/** "R/R 1.79" gösterimi. */
export function formatRR(rr: number): string {
  return `R/R ${rr.toFixed(2)}`;
}

/** Sembol-aware price (8 decimals memecoin için, 2 default). */
const MEMECOIN = new Set(["SHIBUSDT", "PEPEUSDT", "BONKUSDT", "WIFUSDT"]);
export function formatPriceUSD(symbol: string, price: number): string {
  const decimals = MEMECOIN.has(symbol.toUpperCase()) ? 8 : 2;
  return `$${price.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
}
