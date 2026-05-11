/**
 * Aksiyon Özeti — Adım 21.
 *
 * Orchestrator: useAnalysis(symbol, tf) → 6 bölüm render.
 * Loading skeleton, 503 banner, generic error toast.
 */
import { AlertTriangle, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ActionHeader } from "@/components/dashboard/sections/ActionHeader";
import { IndicatorsSummary } from "@/components/dashboard/sections/IndicatorsSummary";
import { MacroCorrelationCard } from "@/components/dashboard/sections/MacroCorrelationCard";
import { PositionCard } from "@/components/dashboard/sections/PositionCard";
import { ScenarioCard } from "@/components/dashboard/sections/ScenarioCard";
import { WarningsCard } from "@/components/dashboard/sections/WarningsCard";
import { useAnalysis } from "@/hooks/useAnalysis";
import { cn } from "@/lib/utils";
import { getErrorMessage, isApiError } from "@/lib/api";

interface Props {
  symbol: string;
  timeframe: string;
}

// ─── Skeleton ───

function SkeletonCard({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-lg border border-binance-border bg-binance-surface p-4",
        className
      )}
    >
      <div className="mb-3 h-4 w-1/3 rounded bg-binance-border/60" />
      <div className="space-y-2">
        <div className="h-3 w-full rounded bg-binance-border/40" />
        <div className="h-3 w-5/6 rounded bg-binance-border/40" />
        <div className="h-3 w-4/6 rounded bg-binance-border/40" />
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <SkeletonCard className="h-28" />
      <div className="grid gap-4 md:grid-cols-2">
        <SkeletonCard className="h-72" />
        <SkeletonCard className="h-72" />
      </div>
      <SkeletonCard className="h-48" />
      <div className="grid gap-4 md:grid-cols-2">
        <SkeletonCard className="h-56" />
        <SkeletonCard className="h-56" />
      </div>
    </div>
  );
}

// ─── Error banner ───

function ErrorBanner({
  message,
  title,
  is503,
  onRetry,
}: {
  message: string;
  title: string;
  is503: boolean;
  onRetry: () => void;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border-l-4 p-4",
        is503
          ? "border-binance-accent bg-binance-accent/10"
          : "border-binance-short bg-binance-short/10"
      )}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle
          className={cn(
            "h-5 w-5 shrink-0",
            is503 ? "text-binance-accent" : "text-binance-short"
          )}
        />
        <div className="flex-1">
          <h3
            className={cn(
              "font-semibold",
              is503 ? "text-binance-accent" : "text-binance-short"
            )}
          >
            {title}
          </h3>
          <p className="mt-1 text-sm text-binance-text-secondary">{message}</p>
          {is503 && (
            <p className="mt-1 text-[11px] text-binance-text-muted">
              Birkaç gün içinde otomatik açılır. Hesaplama için gereken mum
              sayısına ulaşılınca analiz başlatılır.
            </p>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onRetry}
          className="shrink-0"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Tekrar Dene
        </Button>
      </div>
    </div>
  );
}

// ─── Main ───

export function ActionSummary({ symbol, timeframe }: Props) {
  const { data, isLoading, error, refetch, isFetching } = useAnalysis(
    symbol,
    timeframe
  );

  if (isLoading) return <LoadingSkeleton />;

  if (error) {
    const status = isApiError(error) ? error.status : 0;
    const is503 = status === 503;
    const title = is503
      ? "Yetersiz veri (yeni listelendi)"
      : "Analiz yüklenemedi";
    const message = is503
      ? `${symbol} için ${timeframe} timeframe analizi henüz hazır değil.`
      : getErrorMessage(error);
    return (
      <ErrorBanner
        title={title}
        message={message}
        is503={is503}
        onRetry={() => refetch()}
      />
    );
  }

  if (!data) return null;

  const sq = data.setup_quality;
  // Pozisyon detayları clipboard için (varsa)
  const positionUsd = data.risk_position?.position_size_usd;
  const leverage = data.risk_position?.leverage_actual;
  const riskUsd = data.risk_position?.risk_amount_usd;
  const riskPct = data.risk_position?.adjusted_risk_pct;

  return (
    <div className="space-y-4">
      {isFetching && (
        <div className="text-[11px] text-binance-text-muted">
          Güncelleniyor…
        </div>
      )}

      {/* A. Header */}
      <ActionHeader
        symbol={symbol}
        timeframe={timeframe}
        setupQuality={sq}
        confluence={data.final_confluence}
        alignment={data.multi_tf_alignment}
        levels={data.indicators.levels}
        atrUsdt={data.indicators.volatility.atr.value_usdt}
      />

      {/* B + C 2-kolon */}
      <div className="grid gap-4 lg:grid-cols-2">
        <ScenarioCard
          symbol={symbol}
          timeframe={timeframe}
          scenario={sq.scenario}
          positionUsd={positionUsd}
          leverage={leverage}
          riskUsd={riskUsd}
          riskPct={riskPct}
        />
        <PositionCard symbol={symbol} risk={data.risk_position} />
      </div>

      {/* D. Warnings */}
      <WarningsCard
        counterTrend={sq.counter_trend_warnings}
        noTradeZone={sq.no_trade_zones}
        tradeQuality={sq.trade_quality}
      />

      {/* E + F 2-kolon */}
      <div className="grid gap-4 lg:grid-cols-2">
        <MacroCorrelationCard
          macro={data.macro}
          correlations={data.correlations}
          symbol={symbol}
        />
        <IndicatorsSummary
          symbol={symbol}
          indicators={data.indicators}
          alignment={data.multi_tf_alignment}
        />
      </div>
    </div>
  );
}
