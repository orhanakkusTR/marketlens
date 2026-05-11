/**
 * Regime detail — TanStack Query, 60s frontend cache + background refresh.
 */
import { useQuery } from "@tanstack/react-query";

import { apiGet } from "@/lib/api";
import type { RegimeDetailResponse } from "@/types/regime-detail";

const REFRESH_INTERVAL_MS = 60_000;

export function useRegimeDetail() {
  return useQuery({
    queryKey: ["macro", "regime-detail"],
    queryFn: () =>
      apiGet<RegimeDetailResponse>("/api/v1/macro/regime-detail"),
    staleTime: REFRESH_INTERVAL_MS,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
}
