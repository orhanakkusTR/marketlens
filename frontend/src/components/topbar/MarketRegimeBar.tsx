/**
 * Piyasa Rejimi Bar — Adım 20 polish (collapsible + setup distribution).
 *
 * Kapalı (default): tek satır özet — rejim ikonu + Türkçe başlık + kısa strateji.
 * Açık: setup distribution + yön + macro özeti + warnings + tam strateji.
 *
 * Veri: GET /api/v1/macro/regime-detail (composite, 60s cache).
 *
 * State persistence: localStorage `marketlens:topbar:regime_detail_open` (default false).
 */
import { ChevronDown, ChevronUp } from "lucide-react";
import { useEffect, useState } from "react";

import { useRegimeDetail } from "@/hooks/useRegimeDetail";
import { cn } from "@/lib/utils";
import type { MarketRegime } from "@/types/macro";

const STORAGE_KEY = "marketlens:topbar:regime_detail_open";

interface RegimeView {
  icon: string;
  textColor: string;
  bgColor: string;
  borderColor: string;
}

const REGIME_MAP: Record<MarketRegime, RegimeView> = {
  BTC_BULL: {
    icon: "🟢",
    textColor: "text-binance-long",
    bgColor: "bg-binance-long/5",
    borderColor: "border-l-binance-long",
  },
  ALT_BULL: {
    icon: "🟢",
    textColor: "text-binance-long",
    bgColor: "bg-binance-long/5",
    borderColor: "border-l-binance-long",
  },
  ALT_SEASON_EARLY: {
    icon: "🟡",
    textColor: "text-binance-accent",
    bgColor: "bg-binance-accent/5",
    borderColor: "border-l-binance-accent",
  },
  MIXED: {
    icon: "🟡",
    textColor: "text-binance-accent",
    bgColor: "bg-binance-accent/5",
    borderColor: "border-l-binance-accent",
  },
  RISK_OFF: {
    icon: "🔴",
    textColor: "text-binance-short",
    bgColor: "bg-binance-short/5",
    borderColor: "border-l-binance-short",
  },
};

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function readInitial(): boolean {
  if (typeof window === "undefined") return false;
  const v = window.localStorage.getItem(STORAGE_KEY);
  return v === "true";
}

interface PillProps {
  value: number;
  label: string;
  /** Tailwind background utility (örn: "bg-emerald-500/15") */
  bg: string;
  /** Tailwind text utility (örn: "text-emerald-400") */
  fg: string;
  /** Opsiyonel iç ikon (örn ▲ ▼ ◇) — sayıdan sonra */
  icon?: string;
}

function Pill({ value, label, bg, fg, icon }: PillProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[11px] font-semibold tabular-nums",
        bg,
        fg
      )}
    >
      <span>{value}</span>
      {icon && <span className="leading-none">{icon}</span>}
      <span className="font-medium">{label}</span>
    </span>
  );
}

export function MarketRegimeBar() {
  const { data, isLoading, error } = useRegimeDetail();
  const [open, setOpen] = useState<boolean>(readInitial);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, String(open));
  }, [open]);

  if (isLoading) {
    return (
      <div className="border-b border-binance-border px-4 py-1.5 text-[11px] text-binance-text-muted">
        Piyasa rejimi yükleniyor…
      </div>
    );
  }

  if (error || !data) return null;

  const view = REGIME_MAP[data.regime];
  const shortStrategy = truncate(data.strategy_tr, 50);
  const headerSummary = open ? data.reasoning_tr : shortStrategy;

  const grades = data.setup_distribution.grade_counts;
  const dirs = data.setup_distribution.direction_counts;
  const macro = data.macro_summary;

  return (
    <div
      className={cn(
        "border-b border-binance-border border-l-4",
        view.bgColor,
        view.borderColor
      )}
    >
      {/* Başlık satırı (her zaman görünür, tıklanabilir) */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-4 py-1.5 text-left transition-colors hover:bg-white/[0.02]"
        aria-expanded={open}
      >
        <span className="text-base leading-none">{view.icon}</span>
        <span className="text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
          Rejim:
        </span>
        <span className={cn("text-sm font-semibold", view.textColor)}>
          {data.regime_label_tr}
        </span>
        <span className="truncate text-xs text-binance-text-secondary">
          — {headerSummary}
        </span>
        <span className="ml-auto inline-flex shrink-0 items-center gap-1 rounded border border-binance-border bg-binance-bg/40 px-2 py-0.5 text-[10px] text-binance-text-secondary hover:text-binance-text-primary">
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

      {/* Açık detay */}
      {open && (
        <div className="space-y-1.5 border-t border-binance-border/60 px-4 py-2 text-[11px]">
          {/* Setup distribution — kapsüller */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-binance-text-muted">
              Setup ({data.setup_distribution.total_symbols}):
            </span>
            <Pill
              value={grades.A}
              label="A"
              bg="bg-emerald-500/15"
              fg="text-emerald-400"
            />
            <Pill
              value={grades.B}
              label="B"
              bg="bg-emerald-400/15"
              fg="text-emerald-300"
            />
            <Pill
              value={grades.C}
              label="C"
              bg="bg-yellow-500/15"
              fg="text-yellow-400"
            />
            <Pill
              value={grades.D}
              label="D"
              bg="bg-orange-500/15"
              fg="text-orange-400"
            />
            <Pill
              value={grades.NO_TRADE}
              label="DUR"
              bg="bg-red-500/15"
              fg="text-red-400"
            />
            {grades.none > 0 && (
              <Pill
                value={grades.none}
                label="Yeni"
                bg="bg-blue-500/15"
                fg="text-blue-400"
              />
            )}
          </div>

          {/* Direction distribution — kapsüller */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-binance-text-muted">
              Yön ({data.setup_distribution.total_symbols}):
            </span>
            <Pill
              value={dirs.long}
              label="Long"
              icon="▲"
              bg="bg-emerald-500/15"
              fg="text-emerald-400"
            />
            <Pill
              value={dirs.short}
              label="Short"
              icon="▼"
              bg="bg-red-500/15"
              fg={dirs.short > 0 ? "text-red-400" : "text-red-400/60"}
            />
            <Pill
              value={dirs.neutral}
              label="Nötr"
              icon="◇"
              bg="bg-zinc-500/15"
              fg="text-zinc-400"
            />
            {dirs.none > 0 && (
              <Pill
                value={dirs.none}
                label="Yön Yok"
                bg="bg-zinc-700/30"
                fg="text-zinc-500"
              />
            )}
          </div>

          {/* Macro özet */}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-binance-text-secondary">
            <span>
              <span className="text-binance-text-muted">BTC.D</span>{" "}
              {macro.btc_dominance.toFixed(1)}%
            </span>
            <span className="text-binance-text-muted">|</span>
            <span>
              <span className="text-binance-text-muted">F&G</span>{" "}
              {macro.fear_greed_value} {macro.fear_greed_label_tr}
            </span>
            <span className="text-binance-text-muted">|</span>
            <span>
              <span className="text-binance-text-muted">ETH/BTC 7g</span>{" "}
              {macro.eth_btc_change_pct !== null
                ? `${macro.eth_btc_change_pct >= 0 ? "+" : ""}${macro.eth_btc_change_pct.toFixed(2)}%`
                : "—"}
            </span>
            <span className="text-binance-text-muted">|</span>
            <span>
              <span className="text-binance-text-muted">TradFi</span>{" "}
              {macro.tradfi_signal}
            </span>
          </div>

          {/* Warnings */}
          {data.warnings_tr.length > 0 && (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-orange-400">
              {data.warnings_tr.map((w) => (
                <span key={w} className="inline-flex items-center gap-1.5">
                  <span className="leading-none">⚠</span>
                  <span>{w}</span>
                </span>
              ))}
            </div>
          )}

          {/* Strategy — vurgulu (kısa özet, detay aşağıda) */}
          <div className="text-xs">
            <span className="font-medium text-binance-text-primary">
              Strateji:
            </span>{" "}
            <span className="text-binance-text-secondary">
              {data.strategy_tr}
            </span>
          </div>

          {/* ───── İnsan dilinde detay (4 bölüm) ───── */}
          <div className="space-y-3 border-t border-binance-border/60 pt-3 text-xs leading-relaxed">
            {/* 1. Piyasa Durumu */}
            <section>
              <h3 className="mb-1 text-sm font-semibold text-binance-text-primary">
                📊 Piyasa Durumu
              </h3>
              <p className="text-binance-text-secondary">
                {data.detailed_analysis_tr.market_state}
              </p>
            </section>

            {/* 2. Sistem Analizi */}
            <section>
              <h3 className="mb-1 text-sm font-semibold text-binance-text-primary">
                🎯 Sistem Analizi
              </h3>
              <p className="text-binance-text-secondary">
                {data.detailed_analysis_tr.system_state}
              </p>
            </section>

            {/* 3. Risk Faktörleri */}
            {data.detailed_analysis_tr.risk_factors.length > 0 && (
              <section>
                <h3 className="mb-1 text-sm font-semibold text-binance-accent">
                  ⚠️ Risk Faktörleri
                </h3>
                <ul className="space-y-0.5 pl-4">
                  {data.detailed_analysis_tr.risk_factors.map((f) => (
                    <li
                      key={f}
                      className="relative text-binance-text-secondary before:absolute before:-left-3 before:text-binance-text-muted before:content-['•']"
                    >
                      {f}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {/* 4. Öneri */}
            <section>
              <h3 className="mb-1 text-sm font-semibold text-binance-long">
                💡 Öneri
              </h3>
              <p className="text-binance-text-secondary">
                {data.detailed_analysis_tr.recommendation.summary}
              </p>
              {data.detailed_analysis_tr.recommendation.bullets.length > 0 && (
                <ul className="mt-1 space-y-0.5 pl-4">
                  {data.detailed_analysis_tr.recommendation.bullets.map((b) => (
                    <li
                      key={b}
                      className="relative text-binance-text-secondary before:absolute before:-left-3 before:text-binance-text-muted before:content-['•']"
                    >
                      {b}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
