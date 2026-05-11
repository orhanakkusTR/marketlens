/**
 * Macro strip formatters — Adım 20.
 *
 * Number formats, direction icons, F&G Türkçe label/color.
 */

const COMPACT_USD = new Intl.NumberFormat("en-US", {
  notation: "compact",
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

const PLAIN_INT = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
});

/** "$2.78T", "$881B" gibi compact USD formatı. */
export function formatCompactUSD(value: number): string {
  return COMPACT_USD.format(value);
}

/** "5,180" gibi binlik virgüllü tamsayı (SP500 için). */
export function formatThousands(value: number): string {
  return PLAIN_INT.format(value);
}

/** Belirtilen ondalığa yuvarla, 0 atma. "54.2%", "103.2". */
export function formatFixed(value: number, decimals = 1): string {
  return value.toFixed(decimals);
}

// ─── Direction arrows ───

export type ArrowIcon = "↑↑" | "↑" | "→" | "↓" | "↓↓";

export interface DirectionVisual {
  icon: ArrowIcon;
  /** Tailwind class. */
  color: string;
}

/**
 * 24h yüzde değişimine göre ok ikonu + renk.
 *
 * Eşikler:
 *   pct > +2          → ↑↑   yeşil
 *   +0.5 < pct ≤ +2   → ↑    yeşil
 *   -0.5 ≤ pct ≤ +0.5 → →    muted (yatay band)
 *   -2 ≤ pct < -0.5   → ↓    kırmızı
 *   pct < -2          → ↓↓   kırmızı
 *
 * pct null/undefined → "→" muted (trend verisi yok).
 */
export function directionVisual(pct: number | null | undefined): DirectionVisual {
  if (pct === null || pct === undefined) {
    return { icon: "→", color: "text-binance-text-muted" };
  }
  if (pct > 2) return { icon: "↑↑", color: "text-binance-long" };
  if (pct > 0.5) return { icon: "↑", color: "text-binance-long" };
  if (pct >= -0.5) return { icon: "→", color: "text-binance-text-muted" };
  if (pct >= -2) return { icon: "↓", color: "text-binance-short" };
  return { icon: "↓↓", color: "text-binance-short" };
}

// ─── F&G ───

export interface FearGreedVisual {
  /** 0-100 değere göre Türkçe etiket. */
  label: string;
  /** Tailwind utility class for text. */
  textColor: string;
  /** Background tinted (low opacity) for badge. */
  bgColor: string;
  /** Pure hex (style attribute fallback için). */
  hex: string;
}

/**
 * Alternative.me F&G 0-100 değerinden Türkçe label + renk paleti üret.
 *
 * Eşikler (user spec):
 *   0-24   → Aşırı Korku    (#F84960)
 *   25-44  → Korku           (#FF9933)
 *   45-54  → Nötr            (#FCD535)
 *   55-74  → Açgözlü         (#02C076)
 *   75-100 → Aşırı Açgözlü   (#00A86B)
 */
export function fearGreedVisual(value: number): FearGreedVisual {
  if (value < 25) {
    return {
      label: "Aşırı Korku",
      textColor: "text-binance-short",
      bgColor: "bg-binance-short/10",
      hex: "#F84960",
    };
  }
  if (value < 45) {
    return {
      label: "Korku",
      textColor: "text-orange-400",
      bgColor: "bg-orange-400/10",
      hex: "#FF9933",
    };
  }
  if (value < 55) {
    return {
      label: "Nötr",
      textColor: "text-binance-accent",
      bgColor: "bg-binance-accent/10",
      hex: "#FCD535",
    };
  }
  if (value < 75) {
    return {
      label: "Açgözlü",
      textColor: "text-binance-long",
      bgColor: "bg-binance-long/10",
      hex: "#02C076",
    };
  }
  return {
    label: "Aşırı Açgözlü",
    textColor: "text-emerald-400",
    bgColor: "bg-emerald-400/10",
    hex: "#00A86B",
  };
}

/** Confluence skoru renk (-100..+100). */
export function confluenceColor(score: number): string {
  if (score >= 40) return "text-binance-long";
  if (score >= 15) return "text-[#4ECCA3]";
  if (score > -15) return "text-binance-text-secondary";
  if (score > -40) return "text-orange-400";
  return "text-binance-short";
}

/** "+68.3" / "-12.5" formatı. */
export function formatSignedScore(score: number): string {
  const sign = score >= 0 ? "+" : "";
  return `${sign}${score.toFixed(1)}`;
}
