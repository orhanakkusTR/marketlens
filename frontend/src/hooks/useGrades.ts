/**
 * Symbols grades — TanStack Query ile 60s cache + background refresh.
 *
 * Backend cache de 60s; frontend interval'i aynı tutuyoruz.
 */
import { useQuery } from "@tanstack/react-query";

import { apiGet } from "@/lib/api";
import type { GradesResponse, GradeSummary } from "@/types/api";

const REFRESH_INTERVAL_MS = 60_000;

export function useGrades(timeframe: string = "4H") {
  const query = useQuery({
    queryKey: ["symbols", "grades", timeframe],
    queryFn: () =>
      apiGet<GradesResponse>(`/api/v1/symbols/grades?timeframe=${timeframe}`),
    staleTime: REFRESH_INTERVAL_MS,
    refetchInterval: REFRESH_INTERVAL_MS,
  });

  // Map<symbol, GradeSummary> erişim kolaylığı için
  const bySymbol = new Map<string, GradeSummary>(
    query.data?.items.map((item) => [item.symbol, item]) ?? []
  );

  return {
    ...query,
    bySymbol,
  };
}
