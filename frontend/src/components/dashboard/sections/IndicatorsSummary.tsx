/**
 * Indikatör Özeti (F) — Adım 21.
 *
 * Kompakt grid + 6 TF Alignment görselleştirme.
 *
 * 5 alt-blok: Trend / Momentum / Volatilite / Hacim / Futures
 * Her blok: 3-5 anahtar metrik
 */
import {
  formatFundingRate,
  formatPctSigned,
  formatPriceUSD,
} from "@/lib/format-trading";
import { formatSignedScore } from "@/lib/format-macro";
import { cn } from "@/lib/utils";
import type {
  AlignmentResult,
  AlignmentTimeframe,
  IndicatorBundle,
} from "@/types/analysis";

interface Props {
  symbol: string;
  indicators: IndicatorBundle;
  alignment: AlignmentResult;
}

// ─── Mini KV row ───

interface KvProps {
  label: string;
  value: React.ReactNode;
  valueColor?: string;
  hint?: string;
}

function Kv({ label, value, valueColor, hint }: KvProps) {
  return (
    <div className="flex items-baseline justify-between gap-2 text-[11px]" title={hint}>
      <span className="text-binance-text-muted">{label}</span>
      <span
        className={cn(
          "font-mono font-semibold tabular-nums",
          valueColor ?? "text-binance-text-primary"
        )}
      >
        {value}
      </span>
    </div>
  );
}

// ─── Yardımcılar ───

function rsiColor(v: number): string {
  if (v > 70) return "text-binance-short";
  if (v < 30) return "text-binance-long";
  return "text-binance-text-primary";
}

function rsiState(v: number): string {
  if (v > 70) return "aşırı alım";
  if (v < 30) return "aşırı satım";
  return "nötr";
}

function macdColor(cross: string, hist: number): string {
  if (cross === "bullish") return "text-binance-long";
  if (cross === "bearish") return "text-binance-short";
  return hist > 0 ? "text-binance-long" : "text-binance-short";
}

const DIVERGENCE_TR: Record<string, string> = {
  regular_bearish: "Düzenli Düşüş",
  regular_bullish: "Düzenli Yükseliş",
  hidden_bearish: "Gizli Düşüş",
  hidden_bullish: "Gizli Yükseliş",
};

function divergenceLabelTr(type: string | null): string {
  if (!type) return "Tespit edildi";
  return DIVERGENCE_TR[type] ?? type;
}

function alignmentRowColor(label: string): string {
  const l = label.toLowerCase();
  if (l === "bullish") return "text-binance-long";
  if (l === "bearish") return "text-binance-short";
  return "text-binance-text-muted";
}

const TF_ORDER: ReadonlyArray<string> = ["15m", "1H", "4H", "1D", "1W", "1M"];

function sortByTf(items: AlignmentTimeframe[]): AlignmentTimeframe[] {
  return [...items].sort(
    (a, b) => TF_ORDER.indexOf(a.timeframe) - TF_ORDER.indexOf(b.timeframe)
  );
}

// ─── Main ───

export function IndicatorsSummary({ symbol, indicators, alignment }: Props) {
  const t = indicators.trend;
  const m = indicators.momentum;
  const v = indicators.volatility;
  const vol = indicators.volume;
  const f = indicators.futures;

  // Trend MA durumu
  const maAlignment = t.moving_averages.alignment;
  const maColor =
    maAlignment === "bullish_stack"
      ? "text-binance-long"
      : maAlignment === "bearish_stack"
        ? "text-binance-short"
        : "text-binance-text-muted";

  // Market structure
  const structure = t.market_structure.structure;
  const structureColor =
    structure === "uptrend"
      ? "text-binance-long"
      : structure === "downtrend"
        ? "text-binance-short"
        : "text-binance-text-muted";

  // BB position
  const price = t.moving_averages.price;
  const bbPosition =
    price > v.bollinger.upper
      ? "üst bandın üstünde"
      : price > v.bollinger.middle
        ? "üst yarıda"
        : price > v.bollinger.lower
          ? "alt yarıda"
          : "alt bandın altında";

  // Ichimoku
  const cloud = t.ichimoku.cloud_state;
  const cloudColor =
    cloud === "above"
      ? "text-binance-long"
      : cloud === "below"
        ? "text-binance-short"
        : "text-binance-text-muted";

  const alignmentRows = sortByTf(alignment.by_timeframe);

  return (
    <div className="rounded-lg border border-binance-border bg-binance-surface p-4">
      <h2 className="mb-3 text-sm font-semibold text-binance-text-primary">
        İndikatör Özeti
      </h2>

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {/* Trend */}
        <section className="rounded border border-binance-border bg-binance-bg/30 p-2">
          <h3 className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
            Trend
          </h3>
          <div className="space-y-1">
            <Kv
              label="EMA dizilimi"
              value={
                maAlignment === "bullish_stack"
                  ? "Yükseliş (50>100>200)"
                  : maAlignment === "bearish_stack"
                    ? "Düşüş (50<100<200)"
                    : "Karışık"
              }
              valueColor={maColor}
            />
            <Kv
              label="Yapı"
              value={
                structure === "uptrend"
                  ? "Uptrend"
                  : structure === "downtrend"
                    ? "Downtrend"
                    : "Range"
              }
              valueColor={structureColor}
            />
            <Kv
              label="Ichimoku"
              value={
                cloud === "above"
                  ? "Bulutun üstünde"
                  : cloud === "below"
                    ? "Bulutun altında"
                    : "Bulut içinde"
              }
              valueColor={cloudColor}
              hint={`TK cross: ${t.ichimoku.tk_cross}`}
            />
            {t.moving_averages.moving_averages.slice(0, 3).map((ma) => (
              <Kv
                key={ma.period}
                label={`${ma.type}-${ma.period}`}
                value={
                  <>
                    {formatPriceUSD(symbol, ma.value)}{" "}
                    <span className="text-[10px] text-binance-text-muted">
                      ({formatPctSigned(ma.distance_pct, 1)})
                    </span>
                  </>
                }
              />
            ))}
          </div>
        </section>

        {/* Momentum */}
        <section className="rounded border border-binance-border bg-binance-bg/30 p-2">
          <h3 className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
            Momentum
          </h3>
          <div className="space-y-1">
            <Kv
              label="RSI"
              value={`${m.rsi.current.toFixed(1)} (${rsiState(m.rsi.current)})`}
              valueColor={rsiColor(m.rsi.current)}
            />
            <Kv
              label="MACD"
              value={
                m.macd.cross !== "none"
                  ? m.macd.cross === "bullish"
                    ? "Bullish cross"
                    : "Bearish cross"
                  : `Hist ${m.macd.histogram_direction}`
              }
              valueColor={macdColor(m.macd.cross, m.macd.histogram)}
            />
            <Kv
              label="Stoch RSI"
              value={`K ${m.stoch_rsi.k.toFixed(0)} D ${m.stoch_rsi.d.toFixed(0)} (${m.stoch_rsi.state === "oversold" ? "aşırı satım" : m.stoch_rsi.state === "overbought" ? "aşırı alım" : "nötr"})`}
              valueColor={
                m.stoch_rsi.state === "oversold"
                  ? "text-binance-long"
                  : m.stoch_rsi.state === "overbought"
                    ? "text-binance-short"
                    : "text-binance-text-primary"
              }
            />
            {m.divergence_rsi.detected && (
              <Kv
                label="RSI Divergence"
                value={divergenceLabelTr(m.divergence_rsi.type)}
                valueColor="text-binance-accent"
              />
            )}
            {m.divergence_macd.detected && (
              <Kv
                label="MACD Divergence"
                value={divergenceLabelTr(m.divergence_macd.type)}
                valueColor="text-binance-accent"
              />
            )}
          </div>
        </section>

        {/* Volatilite */}
        <section className="rounded border border-binance-border bg-binance-bg/30 p-2">
          <h3 className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
            Volatilite
          </h3>
          <div className="space-y-1">
            <Kv
              label="ATR"
              value={`${v.atr.value_pct.toFixed(2)}%`}
              hint={`USDT: ${formatPriceUSD(symbol, v.atr.value_usdt)}`}
              valueColor={
                v.atr.value_pct > 2
                  ? "text-orange-400"
                  : v.atr.value_pct < 0.5
                    ? "text-binance-text-muted"
                    : "text-binance-text-primary"
              }
            />
            <Kv
              label="BB pozisyon"
              value={bbPosition}
              valueColor={
                price > v.bollinger.upper
                  ? "text-binance-short"
                  : price < v.bollinger.lower
                    ? "text-binance-long"
                    : "text-binance-text-primary"
              }
            />
            <Kv
              label="BB genişliği"
              value={`${v.bollinger.width_pct.toFixed(2)}%`}
              valueColor={
                v.bollinger.squeeze ? "text-binance-accent" : undefined
              }
              hint={v.bollinger.squeeze ? "Squeeze (sıkışma)" : undefined}
            />
            {v.bollinger.squeeze && (
              <Kv
                label="BB durumu"
                value="Squeeze ⚡"
                valueColor="text-binance-accent"
              />
            )}
          </div>
        </section>

        {/* Hacim */}
        <section className="rounded border border-binance-border bg-binance-bg/30 p-2">
          <h3 className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
            Hacim
          </h3>
          <div className="space-y-1">
            <Kv
              label="OBV"
              value={vol.obv.slope === "rising" ? "Yükseliyor" : vol.obv.slope === "falling" ? "Düşüyor" : "Yatay"}
              valueColor={
                vol.obv.slope === "rising"
                  ? "text-binance-long"
                  : vol.obv.slope === "falling"
                    ? "text-binance-short"
                    : "text-binance-text-muted"
              }
            />
            <Kv
              label="VWAP"
              value={vol.vwap !== null ? formatPriceUSD(symbol, vol.vwap) : "—"}
              hint="Günlük reset; TF=1D olmadıkça null olabilir"
            />
            <Kv
              label="POC"
              value={formatPriceUSD(symbol, vol.volume_profile.poc)}
            />
            <Kv
              label="VAH / VAL"
              value={
                <>
                  {formatPriceUSD(symbol, vol.volume_profile.vah)}{" / "}
                  {formatPriceUSD(symbol, vol.volume_profile.val)}
                </>
              }
            />
          </div>
        </section>

        {/* Futures */}
        {f && (
          <section className="rounded border border-binance-border bg-binance-bg/30 p-2">
            <h3 className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
              Futures
            </h3>
            <div className="space-y-1">
              <Kv
                label="Funding"
                value={formatFundingRate(f.funding.current_rate)}
                valueColor={
                  f.funding.extreme
                    ? "text-orange-400"
                    : f.funding.current_rate > 0
                      ? "text-binance-long"
                      : "text-binance-short"
                }
                hint={`24h avg: ${formatFundingRate(f.funding.avg_24h)}`}
              />
              <Kv
                label="OI 24h"
                value={
                  f.open_interest.change_24h_pct !== null
                    ? formatPctSigned(f.open_interest.change_24h_pct)
                    : "—"
                }
                valueColor={
                  f.open_interest.change_24h_pct !== null
                    ? f.open_interest.change_24h_pct > 0
                      ? "text-binance-long"
                      : "text-binance-short"
                    : undefined
                }
                hint={`1h: ${f.open_interest.change_1h_pct !== null ? formatPctSigned(f.open_interest.change_1h_pct) : "—"} · 4h: ${f.open_interest.change_4h_pct !== null ? formatPctSigned(f.open_interest.change_4h_pct) : "—"}`}
              />
              <Kv
                label="L/S oranı"
                value={f.long_short.ratio.toFixed(2)}
                valueColor={
                  f.long_short.extreme
                    ? "text-orange-400"
                    : "text-binance-text-primary"
                }
                hint={`Long ${(f.long_short.long_account * 100).toFixed(0)}% / Short ${(f.long_short.short_account * 100).toFixed(0)}%`}
              />
            </div>
          </section>
        )}

        {/* 6 TF Alignment görselleştirme */}
        <section className="rounded border border-binance-border bg-binance-bg/30 p-2">
          <h3 className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
            6 TF Hizalama
          </h3>
          <div className="space-y-0.5">
            {alignmentRows.map((row) => (
              <div
                key={row.timeframe}
                className="grid grid-cols-[36px_1fr_auto] items-center gap-2 text-[11px]"
              >
                <span className="font-mono text-binance-text-muted">
                  {row.timeframe}
                </span>
                <span className={cn(alignmentRowColor(row.label))}>
                  {row.direction === "long"
                    ? "▲"
                    : row.direction === "short"
                      ? "▼"
                      : "◇"}{" "}
                  {row.label.toLowerCase() === "bullish"
                    ? "Bullish"
                    : row.label.toLowerCase() === "bearish"
                      ? "Bearish"
                      : "Nötr"}
                </span>
                <span
                  className={cn(
                    "font-mono font-semibold tabular-nums",
                    alignmentRowColor(row.label)
                  )}
                >
                  {formatSignedScore(row.final_score)}
                </span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
