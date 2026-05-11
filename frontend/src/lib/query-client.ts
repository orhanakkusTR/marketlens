import { QueryClient } from "@tanstack/react-query";

import { getErrorMessage, isApiError } from "@/lib/api";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000, // 30sn
      gcTime: 5 * 60_000, // 5dk
      retry: (failureCount, error) => {
        // 4xx hatalarında retry yapma; 5xx / network için 1 kez
        if (isApiError(error) && error.status >= 400 && error.status < 500) {
          return false;
        }
        return failureCount < 1;
      },
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
});

export { getErrorMessage };
