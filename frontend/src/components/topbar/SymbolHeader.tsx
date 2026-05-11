/**
 * Topbar Sembol Header — Adım 20.
 *
 * Route `/symbol/:code` aktifken Topbar alt satırında gösterilir.
 *
 * Layout:
 *   [BTC] $80,940.08 +0.15% ▲long [C] Conf:+68.3  [15m][1H][4H][1D]
 *
 * Veri kaynakları:
 *   - Price + 24h%: usePricesStore (WS real-time)
 *   - Grade + direction + final_score: useAnalysis (/analysis/full)
 *
 * TF state: URL ?tf=4H query param (paylaşılabilir link). Default 4H.
 */
import { ChevronDown, ChevronUp, Minus } from "lucide-react";
import { useSearchParams } from "react-router-dom";

import { useAnalysis } from "@/hooks/useAnalysis";
import {
  confluenceColor,
  formatSignedScore,
} from "@/lib/format-macro";
import { formatChangePct, formatPrice, shortenSymbol } from "@/lib/format";
import { cn } from "@/lib/utils";
import { usePricesStore } from "@/stores/usePrices";
import type { Direction, GradeLetter } from "@/types/api";

const TIMEFRAMES = ["15m", "1H", "4H", "1D"] as const;
const DEFAULT_TF = "4H";

function GradeBadge({ grade }: { grade: GradeLetter | null }) {
  if (!grade) {
    return (
      <span className="inline-flex h-5 w-12 items-center justify-center rounded text-[10px] font-bold text-binance-text-muted">
        —
      </span>
    );
  }
  const styles: Record<GradeLetter, string> = {
    A: "bg-binance-long text-white",
    B: "bg-[#4ECCA3] text-binance-bg",
    C: "bg-binance-accent text-binance-bg",
    D: "bg-orange-500 text-white",
    NO_TRADE: "bg-binance-short text-white",
  };
  const label = grade === "NO_TRADE" ? "DUR" : grade;
  return (
    <span
      className={cn(
        "inline-flex h-5 min-w-[28px] items-center justify-center rounded px-1.5 text-[10px] font-bold",
        styles[grade]
      )}
    >
      {label}
    </span>
  );
}

function DirectionIcon({ direction }: { direction: Direction | null }) {
  if (direction === "long") {
    return <ChevronUp className="h-3.5 w-3.5 text-binance-long" />;
  }
  if (direction === "short") {
    return <ChevronDown className="h-3.5 w-3.5 text-binance-short" />;
  }
  return <Minus className="h-3.5 w-3.5 text-binance-text-muted" />;
}

interface Props {
  symbol: string;
}

export function SymbolHeader({ symbol }: Props) {
  const [searchParams, setSearchParams] = useSearchParams();
  const tfParam = searchParams.get("tf");
  const tf =
    tfParam && (TIMEFRAMES as readonly string[]).includes(tfParam)
      ? tfParam
      : DEFAULT_TF;

  const price = usePricesStore((s) => s.prices.get(symbol));
  const { data: analysis, isLoading, isError } = useAnalysis(symbol, tf);

  function setTf(next: string) {
    const params = new URLSearchParams(searchParams);
    params.set("tf", next);
    setSearchParams(params, { replace: true });
  }

  const grade = analysis?.setup_quality.grade ?? null;
  const direction = analysis?.setup_quality.direction ?? null;
  const finalScore = analysis?.final_confluence.final_score ?? null;
  const changePct = price?.change_24h_pct;
  const changeColor =
    changePct === undefined
      ? "text-binance-text-muted"
      : changePct > 0
        ? "text-binance-long"
        : changePct < 0
          ? "text-binance-short"
          : "text-binance-text-secondary";

  return (
    <div className="flex items-center gap-3 text-xs">
      {/* Sembol kodu */}
      <span className="font-mono font-semibold text-binance-text-primary">
        {shortenSymbol(symbol)}
      </span>

      {/* Fiyat (WS real-time) */}
      <span className="font-mono text-binance-text-primary">
        {price ? formatPrice(symbol, price.price) : "—"}
      </span>

      {/* 24h % */}
      <span className={cn("font-mono tabular-nums", changeColor)}>
        {changePct !== undefined ? formatChangePct(changePct) : "—"}
      </span>

      {/* Direction */}
      <DirectionIcon direction={direction} />

      {/* Grade */}
      <GradeBadge grade={grade} />

      {/* Confluence skoru */}
      <span className="flex items-center gap-1 font-mono">
        <span className="text-binance-text-muted">Conf:</span>
        {finalScore !== null ? (
          <span className={cn("font-semibold tabular-nums", confluenceColor(finalScore))}>
            {formatSignedScore(finalScore)}
          </span>
        ) : (
          <span className="text-binance-text-muted">
            {isLoading ? "…" : isError ? "n/a" : "—"}
          </span>
        )}
      </span>

      {/* TF picker */}
      <div className="ml-1 flex items-center gap-0.5 rounded border border-binance-border bg-binance-bg/40 p-0.5">
        {TIMEFRAMES.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setTf(option)}
            className={cn(
              "rounded px-2 py-0.5 text-[10px] font-medium font-mono transition-colors",
              option === tf
                ? "bg-binance-accent text-binance-bg"
                : "text-binance-text-secondary hover:text-binance-text-primary"
            )}
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  );
}
