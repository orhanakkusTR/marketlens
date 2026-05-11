/**
 * Uyarılar Kartı (D) — Adım 21.
 *
 * 3 sub-block:
 *   🚨 Counter-Trend Uyarıları
 *   🛑 No-Trade Zone
 *   📊 Trade Quality (5 faktör)
 */
import { Check, X } from "lucide-react";

import { cn } from "@/lib/utils";
import type {
  CounterTrendSeverity,
  CounterTrendWarning,
  NoTradeSeverity,
  NoTradeZoneResult,
  TradeQualityResult,
  TradeQualityVerdict,
} from "@/types/analysis";

// ─── Counter-Trend ───

const CT_SEVERITY_COLOR: Record<CounterTrendSeverity, string> = {
  high: "border-binance-short bg-binance-short/5",
  medium: "border-orange-400 bg-orange-400/5",
  low: "border-binance-accent bg-binance-accent/5",
};

const CT_SEVERITY_BADGE: Record<CounterTrendSeverity, string> = {
  high: "bg-red-500/15 text-red-400",
  medium: "bg-orange-500/15 text-orange-400",
  low: "bg-yellow-500/15 text-yellow-400",
};

const CT_SEVERITY_LABEL: Record<CounterTrendSeverity, string> = {
  high: "Yüksek",
  medium: "Orta",
  low: "Düşük",
};

function CounterTrendBlock({
  warnings,
}: {
  warnings: CounterTrendWarning[];
}) {
  return (
    <section>
      <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-binance-short">
        🚨 Counter-Trend Uyarıları
        <span className="text-[10px] font-normal text-binance-text-muted">
          ({warnings.length})
        </span>
      </h3>
      {warnings.length === 0 ? (
        <p className="text-xs text-binance-text-muted">
          Counter-trend uyarısı yok — sinyal temiz.
        </p>
      ) : (
        <div className="space-y-1.5">
          {warnings.map((w, i) => (
            <div
              key={i}
              className={cn(
                "rounded border-l-2 px-2 py-1.5",
                CT_SEVERITY_COLOR[w.severity]
              )}
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-xs font-medium text-binance-text-primary">
                  {w.message}
                </span>
                <span
                  className={cn(
                    "shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold",
                    CT_SEVERITY_BADGE[w.severity]
                  )}
                >
                  {CT_SEVERITY_LABEL[w.severity]}
                </span>
              </div>
              {w.advice && (
                <div className="mt-0.5 text-[11px] text-binance-text-secondary">
                  → {w.advice}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// ─── No-Trade Zone ───

const NTZ_SEVERITY_COLOR: Record<NoTradeSeverity, string> = {
  blocking: "border-binance-short bg-binance-short/5 text-binance-short",
  warning: "border-orange-400 bg-orange-400/5 text-orange-400",
  info: "border-binance-text-muted bg-binance-text-muted/5 text-binance-text-secondary",
};

const NTZ_SEVERITY_LABEL: Record<NoTradeSeverity, string> = {
  blocking: "Bloklayıcı",
  warning: "Uyarı",
  info: "Bilgi",
};

function NoTradeBlock({ ntz }: { ntz: NoTradeZoneResult }) {
  const visibleZones = ntz.zones.filter((z) => z.severity !== "info");
  const infoCount = ntz.zones.length - visibleZones.length;

  return (
    <section>
      <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-orange-400">
        🛑 No-Trade Zone
        {ntz.is_blocking && (
          <span className="ml-1 rounded bg-binance-short px-1.5 py-0.5 text-[10px] font-bold text-white">
            BLOKLAYICI
          </span>
        )}
        <span className="ml-auto flex items-center gap-2 text-[10px] font-normal">
          <span className="text-binance-short">
            {ntz.severity_summary.blocking} block
          </span>
          <span className="text-orange-400">
            {ntz.severity_summary.warning} uyarı
          </span>
          <span className="text-binance-text-muted">
            {ntz.severity_summary.info} bilgi
          </span>
        </span>
      </h3>
      {visibleZones.length === 0 ? (
        <p className="text-xs text-binance-text-muted">
          Aktif bloklayıcı veya uyarı yok.
          {infoCount > 0 && ` (${infoCount} bilgi kaydı gizlendi.)`}
        </p>
      ) : (
        <div className="space-y-1.5">
          {visibleZones.map((z, i) => (
            <div
              key={i}
              className={cn(
                "rounded border-l-2 px-2 py-1.5",
                NTZ_SEVERITY_COLOR[z.severity]
              )}
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-xs font-medium text-binance-text-primary">
                  {z.message}
                </span>
                <span className="shrink-0 rounded bg-black/20 px-1.5 py-0.5 text-[10px] font-medium">
                  {NTZ_SEVERITY_LABEL[z.severity]}
                </span>
              </div>
              {z.advice && (
                <div className="mt-0.5 text-[11px] text-binance-text-secondary">
                  → {z.advice}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// ─── Trade Quality ───

const TQ_VERDICT_COLOR: Record<TradeQualityVerdict, string> = {
  EXCELLENT: "bg-binance-long text-white",
  GOOD: "bg-[#4ECCA3] text-binance-bg",
  WEAK: "bg-orange-500 text-white",
  AVOID: "bg-binance-short text-white",
};

const TQ_VERDICT_LABEL: Record<TradeQualityVerdict, string> = {
  EXCELLENT: "Mükemmel",
  GOOD: "İyi",
  WEAK: "Zayıf",
  AVOID: "Kaçın",
};

function TradeQualityBlock({ tq }: { tq: TradeQualityResult }) {
  return (
    <section>
      <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-binance-text-primary">
        📊 Trade Quality
        <span
          className={cn(
            "rounded px-2 py-0.5 text-[10px] font-bold",
            TQ_VERDICT_COLOR[tq.verdict]
          )}
        >
          {TQ_VERDICT_LABEL[tq.verdict]} · {tq.score}/5
        </span>
      </h3>
      <ul className="space-y-1.5">
        {tq.factors.map((f) => (
          <li
            key={f.name}
            className="grid grid-cols-[auto_minmax(160px,auto)_auto_1fr] items-baseline gap-2 text-[11px]"
          >
            {f.passed ? (
              <Check className="h-3.5 w-3.5 shrink-0 text-binance-long" />
            ) : (
              <X className="h-3.5 w-3.5 shrink-0 text-binance-short" />
            )}
            <span
              className={cn(
                "font-medium",
                f.passed
                  ? "text-binance-text-primary"
                  : "text-binance-text-secondary"
              )}
            >
              {f.name}
              {f.value && (
                <span className="ml-1 font-mono text-binance-text-muted">
                  ({f.value})
                </span>
              )}
            </span>
            <span className="text-binance-text-muted">→</span>
            <span className="text-binance-text-secondary">{f.note}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

// ─── Main ───

interface Props {
  counterTrend: CounterTrendWarning[];
  noTradeZone: NoTradeZoneResult;
  tradeQuality: TradeQualityResult;
}

export function WarningsCard({
  counterTrend,
  noTradeZone,
  tradeQuality,
}: Props) {
  return (
    <div className="rounded-lg border border-binance-border bg-binance-surface p-4">
      <h2 className="mb-3 text-sm font-semibold text-binance-text-primary">
        Uyarılar & Kalite Kontrolü
      </h2>
      {/* Üst sıra: Counter-trend + NTZ (2-col) */}
      <div className="grid gap-4 md:grid-cols-2">
        <CounterTrendBlock warnings={counterTrend} />
        <NoTradeBlock ntz={noTradeZone} />
      </div>
      {/* Alt sıra: Trade Quality (full-width, açıklamalar tam görünür) */}
      <div className="mt-4 border-t border-binance-border/60 pt-3">
        <TradeQualityBlock tq={tradeQuality} />
      </div>
    </div>
  );
}
