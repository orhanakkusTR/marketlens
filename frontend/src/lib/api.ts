/**
 * Axios HTTP client — auth interceptor + Türkçe error normalizer.
 *
 * Status code → toast eşlemesi UI tarafında yapılır (useApiErrorToast hook).
 * Burada sadece error nesnesini normalize edip raise ediyoruz.
 */
import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
} from "axios";

import { clearAuth, getAccessToken } from "@/lib/auth";
import type { ApiError, ApiErrorBody } from "@/types/api";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});

// ─── Request interceptor: Bearer token ekle ───
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ─── Response interceptor: error normalize + 401 handling ───
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorBody>) => {
    const status = error.response?.status ?? 0;
    const body = (error.response?.data as ApiErrorBody | undefined) ?? null;
    const message = body?.message ?? error.message ?? "Bilinmeyen hata";

    const apiError: ApiError = Object.assign(new Error(message), {
      status,
      body,
    });

    // 401 → token geçersiz / expired → temizle (UI tarafı redirect yapar)
    if (status === 401) {
      clearAuth();
    }

    return Promise.reject(apiError);
  }
);

/**
 * Status code → Türkçe kullanıcı mesajı.
 * UI'da error toast için.
 */
export function getErrorMessage(error: unknown): string {
  if (!isApiError(error)) {
    return "Beklenmeyen bir hata oluştu.";
  }

  const { status, body } = error;

  // Network/timeout
  if (status === 0) {
    return "Bağlantı kurulamadı, lütfen internetinizi kontrol edin.";
  }

  // Backend'in döndüğü Türkçe mesaj varsa onu kullan
  if (body?.message) {
    switch (status) {
      case 401:
        return "Oturum süresi doldu, lütfen tekrar giriş yapın.";
      case 403:
        return "Bu işlem için yetkiniz yok.";
      case 404:
        return body.message;
      case 422:
        return `Geçersiz istek: ${body.message}`;
      case 429:
        return "Çok sık istek, lütfen birkaç saniye bekleyin.";
      case 500:
        return "Sunucu hatası, lütfen tekrar deneyin.";
      case 503:
        return "Bu sembol için yeterli veri yok, lütfen daha sonra tekrar deneyin.";
      default:
        return body.message;
    }
  }

  // Body yoksa fallback
  switch (status) {
    case 401:
      return "Oturum süresi doldu, lütfen tekrar giriş yapın.";
    case 403:
      return "Bu işlem için yetkiniz yok.";
    case 404:
      return "Bulunamadı.";
    case 429:
      return "Çok sık istek, lütfen birkaç saniye bekleyin.";
    case 500:
      return "Sunucu hatası, lütfen tekrar deneyin.";
    case 503:
      return "Servis şu anda kullanılamıyor.";
    default:
      return error.message || "Bilinmeyen hata.";
  }
}

export function isApiError(error: unknown): error is ApiError {
  return (
    error instanceof Error &&
    "status" in error &&
    typeof (error as ApiError).status === "number"
  );
}

// ─── Tiny wrappers (TanStack Query fetcher'ları için) ───

export async function apiGet<T>(
  url: string,
  config?: AxiosRequestConfig
): Promise<T> {
  const res = await api.get<T>(url, config);
  return res.data;
}

export async function apiPost<T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig
): Promise<T> {
  const res = await api.post<T>(url, body, config);
  return res.data;
}
