/**
 * Kullanıcı ayarları — Zustand persist (localStorage).
 *
 * Adım 20 MVP: backend endpoint yok, sadece cihaza özel.
 * Adım 22'de PUT /api/v1/users/me/settings eklendiğinde aynı şema sync edilebilir.
 *
 * Persist key: "marketlens:user_settings"
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type NotificationLevel = "info" | "warning" | "blocking";

export interface UserSettings {
  // Risk Yönetimi
  riskPerTradePct: number; // 0.5..5, default 2
  maxLeverage: number; // 1..25, default 10
  defaultBalanceUSDT: number; // default 3000

  // Auto-Watch S/R (Adım 21B)
  autoWatchSymbols: string[]; // default ["BTCUSDT", "ETHUSDT", "XAUUSDT"]
  autoWatchTimeframes: string[]; // default ["4H", "1D"]

  // Bildirim (Adım 21B)
  notifications: {
    telegramBotToken: string;
    soundEnabled: boolean;
    minLevel: NotificationLevel;
  };
}

export const DEFAULT_SETTINGS: UserSettings = {
  riskPerTradePct: 2,
  maxLeverage: 10,
  defaultBalanceUSDT: 3000,
  autoWatchSymbols: ["BTCUSDT", "ETHUSDT", "XAUUSDT"],
  autoWatchTimeframes: ["4H", "1D"],
  notifications: {
    telegramBotToken: "",
    soundEnabled: true,
    minLevel: "warning",
  },
};

interface SettingsState {
  settings: UserSettings;
  update: (patch: Partial<UserSettings>) => void;
  reset: () => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      settings: DEFAULT_SETTINGS,
      update: (patch) =>
        set((state) => ({ settings: { ...state.settings, ...patch } })),
      reset: () => set({ settings: DEFAULT_SETTINGS }),
    }),
    {
      name: "marketlens:user_settings",
      version: 1,
    }
  )
);
