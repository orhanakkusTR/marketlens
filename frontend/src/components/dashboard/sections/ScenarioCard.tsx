/**
 * Senaryo Kartı (B) — Adım 21.
 *
 * Entry band + Stop (reasoning tooltip) + 3 Hedef (R/R'li) + Ağırlıklı R/R.
 * 📋 Kopyala butonu — direction-aware clipboard metni.
 */
import { ClipboardCopy, HelpCircle } from "lucide-react";
import { toast } from "sonner";

import {
  formatATR,
  formatPctSigned,
  formatPriceUSD,
  formatRR,
} from "@/lib/format-trading";
import { cn } from "@/lib/utils";
import type { ScenarioResult } from "@/types/analysis";

interface Props {
  symbol: string;
  timeframe: string;
  scenario: ScenarioResult | null;
  positionUsd?: number;
  leverage?: number;
  riskUsd?: number;
  riskPct?: number;
}

function buildClipboardText({
  symbol,
  timeframe,
  scenario,
  positionUsd,
  leverage,
  riskUsd,
  riskPct,
}: Props): string {
  if (!scenario) return "";
  const dir = scenario.direction.toUpperCase();
  const lines: string[] = [
    `${symbol} ${timeframe} ${dir}`,
    `Entry: ${formatPriceUSD(symbol, scenario.entry.low)} - ${formatPriceUSD(symbol, scenario.entry.high)} (band ${scenario.entry.width_atr.toFixed(2)} ATR)`,
    `Stop: ${formatPriceUSD(symbol, scenario.stop.price)} (${formatPctSigned(-scenario.stop.distance_pct, 2)})`,
  ];
  scenario.targets.forEach((t, i) => {
    lines.push(
      `TP${i + 1}: ${formatPriceUSD(symbol, t.price)} (${formatRR(t.rr)})`
    );
  });
  lines.push(`Ağırlıklı R/R: ${scenario.rr_weighted.toFixed(2)}`);
  if (positionUsd !== undefined && leverage !== undefined) {
    lines.push(
      `Position: $${positionUsd.toFixed(0)}, ${leverage.toFixed(1)}x leverage`
    );
  }
  if (riskUsd !== undefined && riskPct !== undefined) {
    lines.push(`Risk: $${riskUsd.toFixed(2)} (%${riskPct.toFixed(1)})`);
  }
  return lines.join("\n");
}

async function copyToClipboard(text: string): Promise<boolean> {
  if (!text) return false;
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

export function ScenarioCard(props: Props) {
  const { symbol, scenario } = props;

  async function handleCopy() {
    const text = buildClipboardText(props);
    const ok = await copyToClipboard(text);
    if (ok) {
      toast.success("Aksiyon kopyalandı", { duration: 3000 });
    } else {
      toast.error("Kopyalama başarısız", { duration: 3000 });
    }
  }

  if (!scenario) {
    return (
      <div className="rounded-lg border border-binance-border bg-binance-surface p-4">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-binance-text-primary">
            İşlem Senaryosu
          </h2>
        </div>
        <p className="text-xs text-binance-text-muted">
          Nötr yön — senaryo üretilmedi. Yön belirginleşene kadar bekleyin.
        </p>
      </div>
    );
  }

  const dirColor =
    scenario.direction === "long"
      ? "text-binance-long"
      : scenario.direction === "short"
        ? "text-binance-short"
        : "text-binance-text-muted";

  return (
    <div className="rounded-lg border border-binance-border bg-binance-surface p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-binance-text-primary">
          İşlem Senaryosu
          <span className={cn("ml-2 text-xs font-medium", dirColor)}>
            {scenario.direction === "long" ? "▲ LONG" : "▼ SHORT"}
          </span>
        </h2>
        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1.5 rounded border border-binance-border bg-binance-bg/40 px-2 py-1 text-[11px] text-binance-text-secondary transition-colors hover:border-binance-text-muted hover:text-binance-text-primary"
        >
          <ClipboardCopy className="h-3 w-3" />
          Kopyala
        </button>
      </div>

      {/* Giriş Aralığı */}
      <div className="mb-3">
        <div className="text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
          Giriş Aralığı
        </div>
        <div className="mt-0.5 font-mono text-sm font-semibold tabular-nums text-binance-text-primary">
          {formatPriceUSD(symbol, scenario.entry.low)}{" "}
          <span className="text-binance-text-muted">—</span>{" "}
          {formatPriceUSD(symbol, scenario.entry.high)}
        </div>
        <div className="text-[11px] text-binance-text-muted">
          Bant genişliği: {scenario.entry.width_atr.toFixed(2)} ATR · orta:{" "}
          <span className="font-mono">
            {formatPriceUSD(symbol, scenario.entry.mid)}
          </span>
        </div>
      </div>

      {/* Stop */}
      <div className="mb-3">
        <div className="flex items-center gap-1 text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
          Stop
          <span title={scenario.stop.reasoning}>
            <HelpCircle className="h-3 w-3 cursor-help" />
          </span>
        </div>
        <div className="mt-0.5 font-mono text-sm font-semibold tabular-nums text-binance-short">
          {formatPriceUSD(symbol, scenario.stop.price)}
        </div>
        <div className="text-[11px] text-binance-text-muted">
          <span className="font-mono">
            {formatPctSigned(
              scenario.direction === "long"
                ? -scenario.stop.distance_pct
                : scenario.stop.distance_pct
            )}
          </span>{" "}
          · {formatATR(scenario.stop.distance_atr)} · kaynak: {scenario.stop.source}
        </div>
      </div>

      {/* Hedefler */}
      <div className="mb-3">
        <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
          Hedefler
        </div>
        <div className="space-y-1.5">
          {scenario.targets.map((t, i) => (
            <div
              key={i}
              className="grid grid-cols-[auto_1fr_auto_auto] items-center gap-2 text-xs"
              title={t.reasoning}
            >
              <span className="font-mono font-medium text-binance-text-muted">
                TP{i + 1}
              </span>
              <span className="font-mono font-semibold tabular-nums text-binance-long">
                {formatPriceUSD(symbol, t.price)}
              </span>
              <span className="font-mono text-[11px] tabular-nums text-binance-text-secondary">
                {formatPctSigned(
                  scenario.direction === "long"
                    ? t.distance_pct
                    : -t.distance_pct
                )}
              </span>
              <span className="rounded bg-binance-long/10 px-1.5 py-0.5 font-mono text-[10px] font-medium tabular-nums text-binance-long">
                {formatRR(t.rr)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Ağırlıklı R/R */}
      <div className="border-t border-binance-border/60 pt-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
            Ağırlıklı R/R
          </span>
          <span
            className={cn(
              "font-mono text-base font-bold tabular-nums",
              scenario.rr_weighted >= 1.5
                ? "text-binance-long"
                : "text-orange-400"
            )}
          >
            {scenario.rr_weighted.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
}
