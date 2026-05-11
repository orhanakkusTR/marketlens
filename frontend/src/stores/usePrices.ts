/**
 * Real-time fiyat store — Adım 19.
 *
 * Map<symbol, PriceMessage>. WS upstream'den her mesaj `setPrice` çağrısı yapar.
 * Connection status sidebar dot için.
 *
 * NOT: Map içeren bir state'i Zustand reactivity tetiklemek için yeni Map
 * instance yarat (immutable update).
 */
import { create } from "zustand";

import type { PriceMessage } from "@/types/api";

export type ConnectionStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected";

interface PricesState {
  prices: Map<string, PriceMessage>;
  status: ConnectionStatus;
  lastError: string | null;
  setPrice: (msg: PriceMessage) => void;
  setSnapshot: (prices: PriceMessage[]) => void;
  setStatus: (status: ConnectionStatus, error?: string | null) => void;
  clear: () => void;
}

export const usePricesStore = create<PricesState>((set) => ({
  prices: new Map(),
  status: "idle",
  lastError: null,
  setPrice: (msg) =>
    set((state) => {
      const next = new Map(state.prices);
      next.set(msg.symbol, msg);
      return { prices: next };
    }),
  setSnapshot: (prices) =>
    set((state) => {
      const next = new Map(state.prices);
      for (const p of prices) {
        next.set(p.symbol, p);
      }
      return { prices: next };
    }),
  setStatus: (status, error = null) =>
    set({ status, lastError: error }),
  clear: () =>
    set({ prices: new Map(), status: "idle", lastError: null }),
}));
