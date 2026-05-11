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
