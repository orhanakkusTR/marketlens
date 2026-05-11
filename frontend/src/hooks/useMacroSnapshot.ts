/**
 * Macro snapshot — TanStack Query, 60s frontend cache + background refresh.
 *
 * Backend cache 5dk; bizim 60s refresh yeterli yenilik için.
 */
import { useQuery } from "@tanstack/react-query";

import { apiGet } from "@/lib/api";
import type { MacroSnapshot } from "@/types/macro";

const REFRESH_INTERVAL_MS = 60_000;

export function useMacroSnapshot() {
  return useQuery({
    queryKey: ["macro", "snapshot"],
    queryFn: () => apiGet<MacroSnapshot>("/api/v1/macro/snapshot"),
    staleTime: REFRESH_INTERVAL_MS,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
}
