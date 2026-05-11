/**
 * Auth token storage — localStorage.
 *
 * NOT (Production hardening): MVP'de localStorage yeterli (single-user).
 * Production deploy'da (Future Roadmap, Adım 22+) httpOnly cookie auth'a
 * geçilebilir — XSS yüzey alanını minimize eder. Backend cookie endpoint
 * eklenmesi gerekir.
 */
import type { User } from "@/types/api";

const ACCESS_TOKEN_KEY = "marketlens:access_token";
const REFRESH_TOKEN_KEY = "marketlens:refresh_token";
const USER_KEY = "marketlens:user";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getStoredUser(): User | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function setAuth(
  accessToken: string,
  refreshToken: string,
  user: User
): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}
