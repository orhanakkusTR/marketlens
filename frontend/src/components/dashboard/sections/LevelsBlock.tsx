/**
 * S/R Seviyeleri — Adım 21 polish v4 (collapsible + label width fix).
 *
 * Default kapalı: tek satır özet (R1, S1).
 * Açık: 7-kolon ladder grid (R3-R1, Şu an, S1-S3).
 *
 * State persistence: localStorage `marketlens:action_header:levels_open`
 * (default false).
 *
 * Distance dash formula:
 *   min(5, max(2, ceil(atr_distance * 4)))
 *
 * Status badge:
 *   |distance| < 0.3 ATR        → "⚠ yakın"
 *   score >= 8 && distance<0.5  → "⚡ güçlü"
 *
 * ATR note: TF-özel — 15m ATR < 4H ATR, dolayısıyla aynı fiyat farkı 15m'de
 * daha büyük ATR multiplier olur. Bu doğru/anlamlı (her TF'in kendi normal aralığı).
 */
import { ChevronDown, ChevronUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { formatPriceUSD } from "@/lib/format-trading";
import { cn } from "@/lib/utils";
import { usePricesStore } from "@/stores/usePrices";
import type { LevelsBundle, PriceLevel } from "@/types/analysis";

const STORAGE_KEY = "marketlens:action_header:levels_open";

// Grid template — label genişletildi (w-20 = 80px, "Şu an" rahat sığar)
const GRID_COLS =
  "grid-cols-[80px_60px_140px_minmax(60px,1fr)_70px_90px_80px]";

// ─── Source kısaltma (tooltip için) ───

const SOURCE_LABEL: Array<[RegExp, string]> = [
  [/^vp_poc$/i, "POC"],
  [/^vp_vah$/i, "VAH"],
  [/^vp_val$/i, "VAL"],
  [/^fib/i, "Fib"],
  [/^round/i, "Round"],
  [/^swing/i, "Swing"],
  [/^pivot/i, "Pivot"],
  [/^ema/i, "EMA"],
  [/^sma/i, "SMA"],
];

function shortSource(s: string): string {
  for (const [pattern, label] of SOURCE_LABEL) {
    if (pattern.test(s)) return label;
  }
  return s;
}

function sourcesLabel(sources: string[]): string {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const s of sources) {
    const short = shortSource(s);
    if (!seen.has(short)) {
      seen.add(short);
      out.push(short);
    }
    if (out.length >= 3) break;
  }
  return out.join(" + ");
}

function starsForScore(score: number): string {
  if (score >= 8) return "★★★";
  if (score >= 6) return "★★";
  return "★";
}

function distanceDashes(atrDistance: number): string {
  const n = Math.min(5, Math.max(2, Math.ceil(atrDistance * 4)));
  return "─".repeat(n);
}

function readInitial(): boolean {
  if (typeof window === "undefined") return false;
  const v = window.localStorage.getItem(STORAGE_KEY);
  return v === "true";
}

// ─── Top 3 filter helpers ───

function topResistances(
  resistances: PriceLevel[],
  currentPrice: number
): PriceLevel[] {
  return resistances
    .filter((r) => r.price > currentPrice)
    .sort((a, b) => a.price - b.price)
    .slice(0, 3);
}

function topSupports(
  supports: PriceLevel[],
  currentPrice: number
): PriceLevel[] {
  return supports
    .filter((s) => s.price < currentPrice)
    .sort((a, b) => b.price - a.price)
    .slice(0, 3);
}

// ─── Compact row (kapalı mod) ───

function CompactRow({
  symbol,
  variant,
  level,
  currentPrice,
}: {
  symbol: string;
  variant: "support" | "resistance";
  level: PriceLevel | null;
  currentPrice: number;
}) {
  const labelColor =
    variant === "support" ? "text-binance-long" : "text-binance-short";
  const title = variant === "support" ? "Yakın destek" : "Yakın direnç";
  const badge = variant === "support" ? "S1" : "R1";

  if (!level) {
    return (
      <div className="text-[12px]">
        <span className={cn("font-medium", labelColor)}>{title}:</span>{" "}
        <span className="text-binance-text-muted">yok</span>
      </div>
    );
  }
  const distPct = ((level.price - currentPrice) / currentPrice) * 100;
  const sign = distPct >= 0 ? "+" : "";

  return (
    <div className="flex items-baseline gap-2 text-[12px]">
      <span className={cn("font-medium", labelColor)}>{title}:</span>
      <span className={cn("font-mono font-semibold", labelColor)}>
        {badge}
      </span>
      <span className="font-mono font-semibold tabular-nums text-binance-text-primary">
        {formatPriceUSD(symbol, level.price)}
      </span>
      <span className="font-bold text-yellow-400">
        {starsForScore(level.strength_score)}
      </span>
      <span className="font-mono tabular-nums text-binance-text-secondary">
        ({sign}
        {distPct.toFixed(2)}%)
      </span>
    </div>
  );
}

// ─── Ladder row (açık mod) ───

interface LevelRowProps {
  symbol: string;
  badge: string;
  level: PriceLevel;
  currentPrice: number;
  atrUsdt: number;
  variant: "support" | "resistance";
}

function LevelRow({
  symbol,
  badge,
  level,
  currentPrice,
  atrUsdt,
  variant,
}: LevelRowProps) {
  const labelColor =
    variant === "support" ? "text-binance-long" : "text-binance-short";
  const distancePctRaw = ((level.price - currentPrice) / currentPrice) * 100;
  const distanceAtrRaw =
    atrUsdt > 0 ? (level.price - currentPrice) / atrUsdt : 0;
  const distanceAtrAbs = Math.abs(distanceAtrRaw);
  const dashes = distanceDashes(distanceAtrAbs);
  const distSign = distancePctRaw >= 0 ? "+" : "";
  const atrSign = distanceAtrRaw >= 0 ? "+" : "";
  const sources = sourcesLabel(level.sources) || "—";

  let badgeText: string | null = null;
  let badgeClass = "";
  if (distanceAtrAbs < 0.3) {
    badgeText = "⚠ yakın";
    badgeClass = "text-yellow-400";
  } else if (level.strength_score >= 8 && distanceAtrAbs < 0.5) {
    badgeText = "⚡ güçlü";
    badgeClass = labelColor;
  }

  const tooltip =
    `${badge}: ${formatPriceUSD(symbol, level.price)} — ${sources} ` +
    `(skor ${level.strength_score.toFixed(1)}/10) · ` +
    `Mesafe ${distSign}${distancePctRaw.toFixed(2)}% (${atrSign}${distanceAtrRaw.toFixed(2)} ATR)`;

  return (
    <div
      title={tooltip}
      className={cn(
        "grid items-baseline gap-2 py-0.5 text-sm tabular-nums",
        GRID_COLS
      )}
    >
      <span className={cn("font-mono font-semibold", labelColor)}>
        {badge}
      </span>
      <span className="font-bold text-yellow-400">
        {starsForScore(level.strength_score)}
      </span>
      <span className="font-mono text-base font-semibold text-binance-text-primary">
        {formatPriceUSD(symbol, level.price)}
      </span>
      <span className="text-center font-mono text-zinc-600">{dashes}</span>
      <span className="text-right font-mono text-binance-text-secondary">
        {distSign}
        {distancePctRaw.toFixed(2)}%
      </span>
      <span className="text-right font-mono text-binance-text-muted">
        ({atrSign}
        {distanceAtrRaw.toFixed(2)} ATR)
      </span>
      <span className={cn("text-[12px] font-medium", badgeClass)}>
        {badgeText ?? ""}
      </span>
    </div>
  );
}

// ─── Şu an divider — ortalı, live ───

function CurrentRow({
  symbol,
  displayPrice,
  isLive,
}: {
  symbol: string;
  displayPrice: number;
  isLive: boolean;
}) {
  return (
    <div className="my-2 flex items-center justify-center gap-3 border-y border-binance-border py-2.5">
      <span
        title="Canlı fiyat (WebSocket, her saniye güncel)"
        className="text-[11px] font-semibold uppercase tracking-wider text-binance-text-muted"
      >
        Şu An:
      </span>
      <span className="font-mono text-lg font-bold tabular-nums text-binance-text-primary">
        {formatPriceUSD(symbol, displayPrice)}
      </span>
      <span
        title={
          isLive
            ? "WebSocket bağlantısı aktif"
            : "WebSocket bağlantısı kopuk — snapshot fiyat"
        }
        className="inline-flex items-center gap-1"
      >
        <span
          className={cn(
            "h-2 w-2 rounded-full",
            isLive
              ? "bg-binance-long animate-pulse"
              : "bg-binance-short"
          )}
        />
        <span
          className={cn(
            "text-[11px]",
            isLive ? "text-binance-long" : "text-binance-short"
          )}
        >
          {isLive ? "canlı" : "snapshot"}
        </span>
      </span>
    </div>
  );
}

// ─── Main ───

interface Props {
  symbol: string;
  timeframe: string;
  levels: LevelsBundle;
  atrUsdt: number;
}

export function LevelsBlock({ symbol, timeframe, levels, atrUsdt }: Props) {
  const [open, setOpen] = useState<boolean>(readInitial);
  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, String(open));
  }, [open]);

  // Canlı WS fiyatı — fallback olarak snapshot
  const livePrice = usePricesStore((s) => s.prices.get(symbol)?.price);
  const wsStatus = usePricesStore((s) => s.status);
  const isLive = wsStatus === "connected" && livePrice !== undefined;
  const current = livePrice ?? levels.current_price;

  // Live price değişince filtre + bar/dash yeniden hesaplanır.
  // useMemo: liste sıralaması/filtresi pahalı olmasa da gereksiz re-render azalır.
  const resistances = useMemo(
    () => topResistances(levels.resistances, current),
    [levels.resistances, current]
  );
  const supports = useMemo(
    () => topSupports(levels.supports, current),
    [levels.supports, current]
  );
  const resistancesDisplay = resistances.slice().reverse();

  return (
    <div>
      {/* Header — toggle */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between text-left text-[10px] font-medium uppercase tracking-wider text-binance-text-muted transition-colors hover:text-binance-text-secondary"
        aria-expanded={open}
      >
        <span>
          📍 Seviyeler{" "}
          <span className="font-mono lowercase">({timeframe})</span>
        </span>
        <span className="inline-flex items-center gap-1 rounded border border-binance-border bg-binance-bg/40 px-2 py-0.5 text-[10px] text-binance-text-secondary hover:text-binance-text-primary">
          {open ? (
            <>
              <ChevronUp className="h-3 w-3" />
              Kapat
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3" />
              Detay
            </>
          )}
        </span>
      </button>

      {/* Body */}
      {open ? (
        <div className="mt-2 space-y-0.5">
          {/* Direnç */}
          {resistancesDisplay.length > 0 ? (
            resistancesDisplay.map((r, i) => {
              const badgeIndex = resistancesDisplay.length - i;
              return (
                <LevelRow
                  key={`R${badgeIndex}`}
                  symbol={symbol}
                  badge={`R${badgeIndex}`}
                  level={r}
                  currentPrice={current}
                  atrUsdt={atrUsdt}
                  variant="resistance"
                />
              );
            })
          ) : (
            <div className="py-1 text-[12px] text-binance-text-muted">
              Yakın direnç yok
            </div>
          )}

          <CurrentRow
            symbol={symbol}
            displayPrice={current}
            isLive={isLive}
          />

          {/* Destek */}
          {supports.length > 0 ? (
            supports.map((s, i) => (
              <LevelRow
                key={`S${i + 1}`}
                symbol={symbol}
                badge={`S${i + 1}`}
                level={s}
                currentPrice={current}
                atrUsdt={atrUsdt}
                variant="support"
              />
            ))
          ) : (
            <div className="py-1 text-[12px] text-binance-text-muted">
              Yakın destek yok
            </div>
          )}
        </div>
      ) : (
        <div className="mt-1.5 space-y-0.5">
          <CompactRow
            symbol={symbol}
            variant="resistance"
            level={resistances[0] ?? null}
            currentPrice={current}
          />
          <CompactRow
            symbol={symbol}
            variant="support"
            level={supports[0] ?? null}
            currentPrice={current}
          />
        </div>
      )}
    </div>
  );
}
