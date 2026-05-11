/**
 * Auth Zustand store — localStorage'la senkronize.
 *
 * Hydrate: ilk yüklenmede localStorage'dan oku.
 * Mutasyon: setAuth/clearAuth localStorage'ı da günceller.
 */
import { create } from "zustand";

import {
  clearAuth as clearAuthStorage,
  getAccessToken,
  getStoredUser,
  setAuth as setAuthStorage,
} from "@/lib/auth";
import type { User } from "@/types/api";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (accessToken: string, refreshToken: string, user: User) => void;
  logout: () => void;
}

const initialToken = getAccessToken();
const initialUser = getStoredUser();

export const useAuthStore = create<AuthState>((set) => ({
  user: initialUser,
  token: initialToken,
  isAuthenticated: Boolean(initialToken && initialUser),
  login: (accessToken, refreshToken, user) => {
    setAuthStorage(accessToken, refreshToken, user);
    set({ user, token: accessToken, isAuthenticated: true });
  },
  logout: () => {
    clearAuthStorage();
    set({ user: null, token: null, isAuthenticated: false });
  },
}));
