/**
 * Topbar Piyasa Bağlamı — Adım 20 round 2 (görsel hiyerarşi).
 *
 * Yapı:
 *   Üst:  "PİYASA BAĞLAMI" başlığı (text-[10px] uppercase, muted)
 *   Alt:  8 eşit kolon grid — her hücre: label (üst, küçük/soluk) + value (alt, renkli/mono)
 *
 * Sıra: TOTAL, TOTAL3, BTC.D, ETH.D, DXY, SP500, VIX, F&G
 *
 * Crypto caps (ilk 4) trend yok → "→" + muted renk + tooltip.
 * TradFi (DXY/SP500/VIX) → MetricTrend.change_24h_pct'ten ok + renk.
 * F&G → value-based 5-renk skala, label dar viewport'ta gizlenir.
 */
import { useMacroSnapshot } from "@/hooks/useMacroSnapshot";
import {
  type ArrowIcon,
  directionVisual,
  fearGreedVisual,
  formatCompactUSD,
  formatFixed,
  formatThousands,
} from "@/lib/format-macro";
import { cn } from "@/lib/utils";
import type { MetricTrend } from "@/types/macro";

const CAPS_TOOLTIP = "Trend verisi yok (CoinGecko free tier kısıtı)";
const MUTED_VALUE = "text-binance-text-secondary";

interface CellProps {
  label: string;
  arrow: ArrowIcon;
  value: string;
  /** Tailwind text-* class. Hem arrow hem value bunu kullanır. */
  color: string;
  /** Opsiyonel ekstra (F&G label gibi) — geniş ekranda gösterilir. */
  trailing?: React.ReactNode;
  title?: string;
}

function Cell({ label, arrow, value, color, trailing, title }: CellProps) {
  return (
    <div
      className="flex min-w-0 flex-col items-start gap-0.5 rounded-md border border-binance-border bg-binance-bg/30 px-2 py-1"
      title={title}
    >
      <span className="text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
        {label}
      </span>
      <span
        className={cn(
          "flex items-baseline gap-1 truncate font-mono text-[11px] font-semibold tabular-nums",
          color
        )}
      >
        <span>{arrow}</span>
        <span>{value}</span>
        {trailing}
      </span>
    </div>
  );
}

function TradFiCell({
  label,
  metric,
  formatter,
}: {
  label: string;
  metric: MetricTrend;
  formatter: (n: number) => string;
}) {
  const vis = directionVisual(metric.change_24h_pct);
  const title =
    metric.change_24h_pct !== null
      ? `24h: ${metric.change_24h_pct >= 0 ? "+" : ""}${metric.change_24h_pct.toFixed(2)}%`
      : undefined;
  return (
    <Cell
      label={label}
      arrow={vis.icon}
      value={formatter(metric.current)}
      color={vis.color}
      title={title}
    />
  );
}

export function MacroStrip() {
  const { data, isLoading, error } = useMacroSnapshot();

  if (isLoading) {
    return (
      <div className="text-[10px] text-binance-text-muted">
        Piyasa bağlamı yükleniyor…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-[10px] text-binance-short">
        Piyasa verisi alınamadı
      </div>
    );
  }

  const caps = data.crypto_caps;
  const fg = data.fear_greed;
  const fgVis = fearGreedVisual(fg.value);
  const fgTitle = (() => {
    const diff = fg.change_7d ?? 0;
    return `Fear & Greed Index — 7g değişim: ${diff >= 0 ? "+" : ""}${diff}`;
  })();

  return (
    <div className="flex flex-col gap-1">
      <div className="text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
        Piyasa Bağlamı
      </div>
      <div className="grid grid-cols-8 gap-3">
        {/* Crypto caps — trend yok, sabit → + muted renk */}
        <Cell
          label="TOTAL"
          arrow="→"
          value={formatCompactUSD(caps.total)}
          color={MUTED_VALUE}
          title={CAPS_TOOLTIP}
        />
        <Cell
          label="TOTAL3"
          arrow="→"
          value={formatCompactUSD(caps.total3)}
          color={MUTED_VALUE}
          title={CAPS_TOOLTIP}
        />
        <Cell
          label="BTC.D"
          arrow="→"
          value={`${formatFixed(caps.btc_dominance, 1)}%`}
          color={MUTED_VALUE}
          title={CAPS_TOOLTIP}
        />
        <Cell
          label="ETH.D"
          arrow="→"
          value={`${formatFixed(caps.eth_dominance, 1)}%`}
          color={MUTED_VALUE}
          title={CAPS_TOOLTIP}
        />

        {/* TradFi — yön + renk dinamik */}
        <TradFiCell
          label="DXY"
          metric={data.dxy}
          formatter={(n) => formatFixed(n, 1)}
        />
        <TradFiCell
          label="SP500"
          metric={data.sp500}
          formatter={formatThousands}
        />
        <TradFiCell
          label="VIX"
          metric={data.vix}
          formatter={(n) => formatFixed(n, 1)}
        />

        {/* F&G — value-based renk + Türkçe label (dar ekranda gizli) */}
        <div
          className="flex min-w-0 flex-col items-start gap-0.5 rounded-md border border-binance-border bg-binance-bg/30 px-2 py-1"
          title={fgTitle}
        >
          <span className="text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
            F&G
          </span>
          <span
            className={cn(
              "flex items-baseline gap-1 truncate font-mono text-[11px] font-semibold tabular-nums",
              fgVis.textColor
            )}
          >
            <span>{fg.value}</span>
            <span className="hidden truncate xl:inline">{fgVis.label}</span>
          </span>
        </div>
      </div>
    </div>
  );
}
