/**
 * Sidebar tek sembol satırı — Adım 19.
 *
 * Sol:    Sembol kodu (BTC) — direction icon
 * Orta:   Fiyat (monospace)
 * Sağ:    24h% renkli + Grade badge / "Yeni" rozeti
 *
 * Tıklayınca → /symbol/{code}.
 */
import { ChevronDown, ChevronUp, Diamond, Minus } from "lucide-react";
import { NavLink } from "react-router-dom";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { formatChangePct, formatPrice, shortenSymbol } from "@/lib/format";
import type { GradeSummary, PriceMessage } from "@/types/api";

interface Props {
  symbol: string;
  price: PriceMessage | undefined;
  grade: GradeSummary | undefined;
}

function GradeBadge({ grade }: { grade: GradeSummary | undefined }) {
  if (!grade) {
    return (
      <span className="inline-block w-7 text-center text-[10px] text-binance-text-muted">
        —
      </span>
    );
  }
  // Yeni listelenen sembol (XAUUSDT senaryosu)
  if (grade.error && !grade.grade) {
    return (
      <span
        title="Bu sembol yeni listelendi, analiz hazır değil"
        className="inline-flex h-4 items-center rounded-md border border-blue-400/60 px-1 text-[10px] font-medium text-blue-400"
      >
        Yeni
      </span>
    );
  }

  const letter = grade.grade;
  const styles: Record<string, string> = {
    A: "bg-binance-long/20 text-binance-long border border-binance-long/40",
    B: "bg-[#4ECCA3]/20 text-[#4ECCA3] border border-[#4ECCA3]/40",
    C: "bg-binance-accent/20 text-binance-accent border border-binance-accent/40",
    D: "bg-orange-400/20 text-orange-400 border border-orange-400/40",
    NO_TRADE: "bg-binance-short/20 text-binance-short border border-binance-short/40",
  };
  const className = letter ? styles[letter] : "";
  return (
    <span
      className={cn(
        "inline-flex h-4 items-center rounded-md px-1 text-[10px] font-medium",
        className
      )}
    >
      {letter === "NO_TRADE" ? "✕" : letter}
    </span>
  );
}

function DirectionIcon({ direction }: { direction: GradeSummary["direction"] }) {
  if (direction === "long") {
    return <ChevronUp className="h-3 w-3 text-binance-long" />;
  }
  if (direction === "short") {
    return <ChevronDown className="h-3 w-3 text-binance-short" />;
  }
  if (direction === "neutral") {
    return <Minus className="h-3 w-3 text-binance-text-muted" />;
  }
  return <Diamond className="h-3 w-3 text-binance-text-muted" />;
}

export function SymbolRow({ symbol, price, grade }: Props) {
  const isNewSymbol = Boolean(grade?.error && !grade?.grade);

  function handleClick(e: React.MouseEvent) {
    if (isNewSymbol) {
      e.preventDefault();
      toast.error(
        "Bu sembol için yeterli veri yok, lütfen daha sonra tekrar deneyin.",
        { duration: 5000 }
      );
    }
  }

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
    <NavLink
      to={`/symbol/${symbol}`}
      onClick={handleClick}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-2 rounded-md px-2 py-1.5 text-xs transition-colors",
          isActive
            ? "bg-binance-border/60 text-binance-text-primary"
            : "text-binance-text-secondary hover:bg-binance-border/30 hover:text-binance-text-primary"
        )
      }
    >
      <DirectionIcon direction={grade?.direction ?? null} />
      <span className="w-12 shrink-0 font-mono text-binance-text-primary">
        {shortenSymbol(symbol)}
      </span>
      <span className="flex-1 truncate font-mono text-[11px] text-binance-text-secondary">
        {price ? formatPrice(symbol, price.price) : "—"}
      </span>
      <span
        className={cn(
          "w-12 shrink-0 text-right font-mono text-[11px]",
          changeColor
        )}
      >
        {changePct !== undefined ? formatChangePct(changePct) : ""}
      </span>
      <GradeBadge grade={grade} />
    </NavLink>
  );
}
