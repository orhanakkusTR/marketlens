/**
 * Backend API tipleri (minimal subset).
 *
 * NOT: İleride openapi-typescript ile otomatik üretim eklenebilir
 * (Phase 3+ — frontend tip tam senkronizasyonu için).
 */

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface ApiErrorBody {
  error: string;
  message: string;
  details?: Record<string, unknown>;
  request_id?: string;
}

export interface ApiError extends Error {
  status: number;
  body: ApiErrorBody | null;
}

// ─── Symbols (Adım 19) ───

export type GradeLetter = "A" | "B" | "C" | "D" | "NO_TRADE";
export type Direction = "long" | "short" | "neutral";

export interface GradeSummary {
  symbol: string;
  grade: GradeLetter | null;
  direction: Direction | null;
  final_score: number | null;
  is_blocking: boolean;
  error: string | null;
}

export interface GradesResponse {
  computed_at: string;
  timeframe: string;
  items: GradeSummary[];
}

// ─── WebSocket ───

export interface PriceMessage {
  type: "price";
  symbol: string;
  price: number;
  change_24h_pct: number;
  ts: number;
}

export interface SnapshotMessage {
  type: "snapshot";
  prices: PriceMessage[];
}

export type ServerMessage = PriceMessage | SnapshotMessage;
