/**
 * Pozisyon Kartı (C) — Adım 21.
 *
 * Position size / leverage / margin / risk / liquidation / funding.
 * Backend `risk_position` payload'ı.
 */
import {
  formatLeverage,
  formatMoney,
  formatMoneySigned,
  formatPct,
  formatPriceUSD,
} from "@/lib/format-trading";
import { cn } from "@/lib/utils";
import type { PositionRiskResult } from "@/types/analysis";

interface Props {
  symbol: string;
  risk: PositionRiskResult | null;
}

interface RowProps {
  label: string;
  value: React.ReactNode;
  hint?: string;
  valueClassName?: string;
}

function Row({ label, value, hint, valueClassName }: RowProps) {
  return (
    <div className="flex items-baseline justify-between gap-2 py-1">
      <span className="text-[11px] text-binance-text-muted">{label}</span>
      <div className="text-right">
        <div
          className={cn(
            "font-mono text-sm font-semibold tabular-nums text-binance-text-primary",
            valueClassName
          )}
        >
          {value}
        </div>
        {hint && (
          <div className="text-[10px] text-binance-text-muted">{hint}</div>
        )}
      </div>
    </div>
  );
}

export function PositionCard({ symbol, risk: riskInput }: Props) {
  if (!riskInput) {
    return (
      <div className="rounded-lg border border-binance-border bg-binance-surface p-4">
        <h2 className="mb-2 text-sm font-semibold text-binance-text-primary">
          Pozisyon
        </h2>
        <p className="text-xs text-binance-text-muted">
          Nötr yön — pozisyon hesabı yapılamadı.
        </p>
      </div>
    );
  }
  const risk = riskInput;

  const dirColor =
    risk.direction === "long"
      ? "text-binance-long"
      : risk.direction === "short"
        ? "text-binance-short"
        : "text-binance-text-muted";

  // Funding: long + pozitif rate = gider; short + pozitif rate = gelir
  // Backend h24/h72/w1 already in USD; pozitif değer demek long için gider, short için gelir.
  // Sign convention'ı kullanıcıya göre çevir:
  const fundingForUser = (value: number): number =>
    risk.direction === "long" ? -value : value;

  return (
    <div className="rounded-lg border border-binance-border bg-binance-surface p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-binance-text-primary">
          Pozisyon
          <span className={cn("ml-2 text-xs font-medium", dirColor)}>
            {risk.direction === "long" ? "▲ LONG" : "▼ SHORT"}
          </span>
        </h2>
        <span className="text-[10px] text-binance-text-muted">
          Bakiye: {formatMoney(risk.balance)}
        </span>
      </div>

      <div className="divide-y divide-binance-border/40">
        <Row
          label="Risk"
          value={formatMoney(risk.risk_amount_usd)}
          hint={`%${risk.adjusted_risk_pct.toFixed(2)} ayarlanmış (taban %${risk.base_risk_pct.toFixed(1)})`}
          valueClassName="text-orange-400"
        />
        <Row
          label="Pozisyon Boyutu"
          value={formatMoney(risk.position_size_usd)}
          hint={`Stop mesafe ${formatPct(risk.stop_distance_pct, 2)}`}
        />
        <Row
          label="Kaldıraç"
          value={formatLeverage(risk.leverage_actual)}
          hint={`Gerekli: ${formatLeverage(risk.leverage_required)}`}
          valueClassName={
            risk.leverage_actual > 10 ? "text-binance-short" : ""
          }
        />
        <Row
          label="Margin"
          value={formatMoney(risk.margin_used)}
          hint={`%${((risk.margin_used / risk.balance) * 100).toFixed(1)} bakiyenin`}
        />
        <Row
          label="Likidasyon"
          value={formatPriceUSD(symbol, risk.liquidation.actual)}
          hint={`5x: ${formatPriceUSD(symbol, risk.liquidation.at_5x)} · 10x: ${formatPriceUSD(symbol, risk.liquidation.at_10x)}`}
          valueClassName="text-binance-short"
        />
        <Row
          label="Funding (24h)"
          value={formatMoneySigned(fundingForUser(risk.funding_costs.h24))}
          hint={`72h: ${formatMoneySigned(fundingForUser(risk.funding_costs.h72))} · 1w: ${formatMoneySigned(fundingForUser(risk.funding_costs.w1))}`}
        />
      </div>

      {/* Volatility adjustment notu */}
      {risk.volatility_adjustment.factor !== 1 && (
        <div className="mt-3 rounded border-l-2 border-binance-accent bg-binance-accent/5 px-2 py-1.5 text-[11px] text-binance-text-secondary">
          <span className="font-medium text-binance-accent">
            Volatilite ayarı:
          </span>{" "}
          {risk.volatility_adjustment.reason} (faktör ×
          {risk.volatility_adjustment.factor.toFixed(2)})
        </div>
      )}

      {/* Warnings */}
      {risk.warnings.length > 0 && (
        <div className="mt-2 space-y-0.5">
          {risk.warnings.map((w) => (
            <div
              key={w}
              className="rounded border-l-2 border-orange-400 bg-orange-400/5 px-2 py-1 text-[11px] text-orange-300"
            >
              ⚠ {w}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
