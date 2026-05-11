/**
 * Sembol analiz — /analysis/full/{sym}/{tf}.
 *
 * Backend cache 30s; frontend staleTime 30s.
 * Sembol veya TF değişince yeni fetch (queryKey'e ikisi de dahil).
 */
import { useQuery } from "@tanstack/react-query";

import { apiGet } from "@/lib/api";
import type { AnalysisFullResult } from "@/types/analysis";

const STALE_TIME_MS = 30_000;

export function useAnalysis(symbol: string | undefined, timeframe: string) {
  return useQuery({
    queryKey: ["analysis", "full", symbol, timeframe],
    queryFn: () =>
      apiGet<AnalysisFullResult>(
        `/api/v1/analysis/full/${symbol}/${timeframe}`
      ),
    enabled: Boolean(symbol),
    staleTime: STALE_TIME_MS,
    // 503 (yetersiz veri) için tekrar deneme — kullanıcı manuel refresh yapsın
    retry: (failureCount, error) => {
      const status = (error as { status?: number } | null)?.status;
      if (status && status >= 400 && status < 500) return false;
      return failureCount < 1;
    },
  });
}
