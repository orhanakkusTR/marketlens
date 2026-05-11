/**
 * Sayı formatlama helpers — sembol başına ondalık + lokalize ayraç.
 *
 * Kararlar (kullanıcı tercihi):
 * - Memecoin / micro-price (SHIB/PEPE/BONK):  8 ondalık
 * - XAUUSDT, mid-price:                         2 ondalık (varsayılan crypto ile aynı)
 * - Genel crypto:                                2 ondalık ($80,627.40)
 */

const EIGHT_DECIMAL_SYMBOLS: ReadonlySet<string> = new Set([
  "SHIBUSDT",
  "PEPEUSDT",
  "BONKUSDT",
  "WIFUSDT",
]);

function priceDecimals(symbol: string): number {
  return EIGHT_DECIMAL_SYMBOLS.has(symbol.toUpperCase()) ? 8 : 2;
}

/**
 * "$80,627.40" gibi USD formatı (sembol başına ondalık).
 */
export function formatPrice(symbol: string, price: number): string {
  const decimals = priceDecimals(symbol);
  return `$${price.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
}

/**
 * "+2.40%" veya "-1.83%" formatı (renk caller tarafından kullanılır).
 */
export function formatChangePct(pct: number): string {
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}

/**
 * Sembol başlığı: USDT eki çıkartılır ("BTC" gibi).
 */
export function shortenSymbol(symbol: string): string {
  return symbol.replace(/USDT$/, "");
}
