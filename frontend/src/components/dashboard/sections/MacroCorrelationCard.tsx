/**
 * Makro Bağlam + Korelasyon Kartı (E) — Adım 21.
 *
 * Sol: market regime + 4 macro KPI (BTC.D, F&G, DXY, VIX)
 * Sağ: top 5 korelasyon + sektör ortalamaları
 */
import { fearGreedVisual, formatFixed } from "@/lib/format-macro";
import { cn } from "@/lib/utils";
import type { CorrelationItem, SymbolCorrelations } from "@/types/analysis";
import type { MacroSnapshot } from "@/types/macro";

const REGIME_LABEL_TR: Record<string, string> = {
  BTC_BULL: "BTC YÜKSELİŞ",
  ALT_BULL: "ALTSEASON",
  ALT_SEASON_EARLY: "ALTSEASON BAŞLANGICI",
  MIXED: "KARARSIZ",
  RISK_OFF: "RİSK-OFF",
};

interface Props {
  macro: MacroSnapshot | null;
  correlations: SymbolCorrelations | null;
  symbol: string;
}

function MacroKpi({
  label,
  value,
  color = "text-binance-text-primary",
  hint,
}: {
  label: string;
  value: string;
  color?: string;
  hint?: string;
}) {
  return (
    <div className="rounded-md border border-binance-border bg-binance-bg/30 px-2 py-1.5">
      <div className="text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
        {label}
      </div>
      <div
        className={cn(
          "font-mono text-sm font-semibold tabular-nums",
          color
        )}
      >
        {value}
      </div>
      {hint && (
        <div className="text-[10px] text-binance-text-muted">{hint}</div>
      )}
    </div>
  );
}

function CorrelationRow({
  item,
  badge,
}: {
  item: CorrelationItem | null;
  badge?: string;
}) {
  if (!item) {
    return (
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-binance-text-muted">{badge ?? "—"}</span>
        <span className="text-binance-text-muted">—</span>
      </div>
    );
  }
  const coef = item.coefficient;
  const color =
    coef >= 0.7
      ? "text-binance-long"
      : coef >= 0.3
        ? "text-[#4ECCA3]"
        : coef <= -0.7
          ? "text-binance-short"
          : coef <= -0.3
            ? "text-orange-400"
            : "text-binance-text-muted";

  return (
    <div className="flex items-center justify-between text-[11px]">
      <span className="font-mono text-binance-text-secondary">
        {badge ?? item.symbol.replace(/USDT$/, "")}
      </span>
      <span className={cn("font-mono font-semibold tabular-nums", color)}>
        {coef >= 0 ? "+" : ""}
        {coef.toFixed(2)}
      </span>
    </div>
  );
}

export function MacroCorrelationCard({
  macro,
  correlations,
  symbol,
}: Props) {
  return (
    <div className="rounded-lg border border-binance-border bg-binance-surface p-4">
      <h2 className="mb-3 text-sm font-semibold text-binance-text-primary">
        Makro Bağlam & Korelasyon
      </h2>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Sol: Makro */}
        <div>
          <div className="mb-2 text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
            Piyasa Bağlamı
          </div>
          {macro ? (
            <div className="space-y-2">
              <div className="rounded border-l-2 border-binance-accent bg-binance-accent/5 px-2 py-1.5">
                <div className="text-[10px] font-medium uppercase text-binance-text-muted">
                  Rejim
                </div>
                <div className="text-xs font-semibold text-binance-accent">
                  {REGIME_LABEL_TR[macro.market_regime.regime] ??
                    macro.market_regime.regime}
                </div>
                <div className="text-[10px] text-binance-text-secondary">
                  {macro.market_regime.label}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                <MacroKpi
                  label="BTC.D"
                  value={`${formatFixed(macro.crypto_caps.btc_dominance, 1)}%`}
                />
                <MacroKpi
                  label="F&G"
                  value={`${macro.fear_greed.value}`}
                  color={fearGreedVisual(macro.fear_greed.value).textColor}
                  hint={fearGreedVisual(macro.fear_greed.value).label}
                />
                <MacroKpi
                  label="DXY"
                  value={formatFixed(macro.dxy.current, 1)}
                  hint={
                    macro.dxy.change_24h_pct !== null
                      ? `${macro.dxy.change_24h_pct >= 0 ? "+" : ""}${macro.dxy.change_24h_pct.toFixed(2)}% 24h`
                      : undefined
                  }
                />
                <MacroKpi
                  label="VIX"
                  value={formatFixed(macro.vix.current, 1)}
                  hint={
                    macro.vix.change_24h_pct !== null
                      ? `${macro.vix.change_24h_pct >= 0 ? "+" : ""}${macro.vix.change_24h_pct.toFixed(2)}% 24h`
                      : undefined
                  }
                />
              </div>
            </div>
          ) : (
            <p className="text-xs text-binance-text-muted">
              Macro verisi alınamadı.
            </p>
          )}
        </div>

        {/* Sağ: Korelasyon */}
        <div>
          <div className="mb-2 text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
            Korelasyon (
            {correlations ? `${correlations.period_days}g` : "—"})
          </div>
          {correlations ? (
            <div className="space-y-2">
              {/* Anchor'lar */}
              <div className="space-y-0.5 rounded border border-binance-border bg-binance-bg/30 px-2 py-1.5">
                {symbol !== "BTCUSDT" && (
                  <CorrelationRow
                    badge="vs BTC"
                    item={
                      correlations.vs_btc !== null
                        ? {
                            symbol: "BTCUSDT",
                            coefficient: correlations.vs_btc,
                            category: "anchor",
                            sign:
                              correlations.vs_btc >= 0
                                ? "positive"
                                : "negative",
                          }
                        : null
                    }
                  />
                )}
                {symbol !== "ETHUSDT" && (
                  <CorrelationRow
                    badge="vs ETH"
                    item={
                      correlations.vs_eth !== null
                        ? {
                            symbol: "ETHUSDT",
                            coefficient: correlations.vs_eth,
                            category: "anchor",
                            sign:
                              correlations.vs_eth >= 0
                                ? "positive"
                                : "negative",
                          }
                        : null
                    }
                  />
                )}
                <CorrelationRow
                  badge="vs DXY"
                  item={
                    correlations.vs_dxy !== null
                      ? {
                          symbol: "DXY",
                          coefficient: correlations.vs_dxy,
                          category: "macro",
                          sign:
                            correlations.vs_dxy >= 0 ? "positive" : "negative",
                        }
                      : null
                  }
                />
                <CorrelationRow
                  badge="vs SP500"
                  item={
                    correlations.vs_sp500 !== null
                      ? {
                          symbol: "SP500",
                          coefficient: correlations.vs_sp500,
                          category: "macro",
                          sign:
                            correlations.vs_sp500 >= 0
                              ? "positive"
                              : "negative",
                        }
                      : null
                  }
                />
              </div>

              {/* Kategori özet sayıları */}
              <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                <span className="inline-flex items-center gap-1 rounded bg-binance-long/15 px-1.5 py-0.5 font-mono text-binance-long">
                  Güçlü {correlations.strong.length}
                </span>
                <span className="inline-flex items-center gap-1 rounded bg-[#4ECCA3]/15 px-1.5 py-0.5 font-mono text-[#4ECCA3]">
                  Orta {correlations.moderate.length}
                </span>
                <span className="inline-flex items-center gap-1 rounded bg-binance-accent/15 px-1.5 py-0.5 font-mono text-binance-accent">
                  Zayıf {correlations.weak.length}
                </span>
                <span className="inline-flex items-center gap-1 rounded bg-binance-text-muted/20 px-1.5 py-0.5 font-mono text-binance-text-muted">
                  Decoupled {correlations.decoupled.length}
                </span>
              </div>

              {/* Top 5 strong correlations */}
              {correlations.strong.length > 0 && (
                <div>
                  <div className="mb-0.5 text-[10px] font-medium uppercase text-binance-long">
                    Güçlü (top 5)
                  </div>
                  <div className="space-y-0.5 rounded border border-binance-border bg-binance-bg/30 px-2 py-1.5">
                    {correlations.strong.slice(0, 5).map((c) => (
                      <CorrelationRow key={c.symbol} item={c} />
                    ))}
                  </div>
                </div>
              )}

              {/* Sektör özet */}
              <div className="flex flex-wrap gap-1 text-[10px]">
                {Object.entries(correlations.by_sector_avg)
                  .sort((a, b) => b[1] - a[1])
                  .map(([sector, val]) => (
                    <span
                      key={sector}
                      className="inline-flex items-center gap-1 rounded bg-binance-bg/40 px-1.5 py-0.5"
                    >
                      <span className="text-binance-text-muted">{sector}</span>
                      <span className="font-mono font-medium text-binance-text-secondary">
                        {val.toFixed(2)}
                      </span>
                    </span>
                  ))}
              </div>
            </div>
          ) : (
            <p className="text-xs text-binance-text-muted">
              Korelasyon verisi alınamadı.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
