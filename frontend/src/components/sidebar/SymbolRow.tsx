/**
 * Sidebar tek sembol satırı — Adım 19.
 *
 * Sol:    Sembol kodu (BTC) — direction icon
 * Orta:   Fiyat (monospace)
 * Sağ:    24h% renkli + Grade badge / "Yeni" rozeti
 *
 * Tıklayınca → /symbol/{code}.
 */
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
  const base =
    "flex h-5 w-full items-center justify-center rounded text-[10px] font-bold";

  if (!grade) {
    return (
      <span className={cn(base, "text-binance-text-muted")}>—</span>
    );
  }
  // Yeni listelenen sembol (XAUUSDT senaryosu)
  if (grade.error && !grade.grade) {
    return (
      <span
        title="Bu sembol yeni listelendi, analiz hazır değil"
        className={cn(
          base,
          "border border-blue-400/70 bg-blue-400/10 text-blue-400"
        )}
      >
        Yeni
      </span>
    );
  }

  const letter = grade.grade;
  const styles: Record<string, string> = {
    A: "bg-binance-long text-white",
    B: "bg-[#4ECCA3] text-binance-bg",
    C: "bg-binance-accent text-binance-bg",
    D: "bg-orange-500 text-white",
    NO_TRADE: "bg-binance-short text-white",
  };
  const className = letter ? styles[letter] : "";
  const label = letter === "NO_TRADE" ? "DUR" : letter;
  return <span className={cn(base, className)}>{label}</span>;
}

function DirectionIcon({ direction }: { direction: GradeSummary["direction"] }) {
  if (direction === "long") {
    return (
      <span
        title="Long (yukarı yönlü setup)"
        aria-label="Long"
        className="font-bold leading-none text-binance-long"
      >
        ▲
      </span>
    );
  }
  if (direction === "short") {
    return (
      <span
        title="Short (aşağı yönlü setup)"
        aria-label="Short"
        className="font-bold leading-none text-binance-short"
      >
        ▼
      </span>
    );
  }
  if (direction === "neutral") {
    return (
      <span
        title="Nötr (yön yok)"
        aria-label="Nötr"
        className="leading-none text-binance-text-muted"
      >
        ◇
      </span>
    );
  }
  return (
    <span
      title="Yön bilgisi yok"
      aria-label="Yön bilgisi yok"
      className="leading-none text-binance-text-muted/60"
    >
      ◇
    </span>
  );
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
          "grid items-center gap-1.5 rounded-md border-l-2 border-l-transparent py-1.5 pl-1.5 pr-2 text-xs transition-colors",
          "grid-cols-[16px_44px_minmax(0,1fr)_58px_48px]",
          isActive
            ? "border-l-binance-long bg-white/5 font-medium text-binance-text-primary"
            : "text-binance-text-secondary hover:bg-binance-border/30 hover:text-binance-text-primary"
        )
      }
    >
      <span className="flex justify-center">
        <DirectionIcon direction={grade?.direction ?? null} />
      </span>
      <span className="truncate font-mono text-binance-text-primary">
        {shortenSymbol(symbol)}
      </span>
      <span className="truncate font-mono text-[11px] tabular-nums text-binance-text-secondary">
        {price ? formatPrice(symbol, price.price) : "—"}
      </span>
      <span
        className={cn(
          "text-right font-mono text-[11px] tabular-nums",
          changeColor
        )}
      >
        {changePct !== undefined ? formatChangePct(changePct) : ""}
      </span>
      <GradeBadge grade={grade} />
    </NavLink>
  );
}
