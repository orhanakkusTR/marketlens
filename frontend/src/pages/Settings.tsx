/**
 * Ayarlar sayfası — Adım 20 MVP.
 *
 * 3 bölüm: Risk Yönetimi, Auto-Watch S/R, Bildirim Tercihleri.
 * Draft pattern: local form state, "Kaydet" commit → Zustand persist
 * (localStorage marketlens:user_settings).
 *
 * Backend endpoint Adım 22'de eklendiğinde aynı şema PUT'a aktarılır.
 */
import { RotateCcw, Save } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { SYMBOL_TIERS } from "@/lib/symbols";
import { cn } from "@/lib/utils";
import {
  DEFAULT_SETTINGS,
  type NotificationLevel,
  type UserSettings,
  useSettingsStore,
} from "@/stores/useSettings";

const AUTO_WATCH_TIMEFRAMES = ["4H", "1D"] as const;

const LEVEL_OPTIONS: { value: NotificationLevel; label: string }[] = [
  { value: "info", label: "Bilgi (her şey)" },
  { value: "warning", label: "Uyarı (önerilen)" },
  { value: "blocking", label: "Sadece bloklayıcı" },
];

function clampNumber(raw: string, fallback: number, min: number, max: number): number {
  const n = Number(raw);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(max, Math.max(min, n));
}

export function Settings() {
  useDocumentTitle("Ayarlar");
  const stored = useSettingsStore((s) => s.settings);
  const update = useSettingsStore((s) => s.update);
  const reset = useSettingsStore((s) => s.reset);

  const [draft, setDraft] = useState<UserSettings>(stored);

  function set<K extends keyof UserSettings>(key: K, value: UserSettings[K]) {
    setDraft((d) => ({ ...d, [key]: value }));
  }

  function toggleSymbol(sym: string) {
    setDraft((d) => {
      const has = d.autoWatchSymbols.includes(sym);
      return {
        ...d,
        autoWatchSymbols: has
          ? d.autoWatchSymbols.filter((s) => s !== sym)
          : [...d.autoWatchSymbols, sym],
      };
    });
  }

  function toggleTimeframe(tf: string) {
    setDraft((d) => {
      const has = d.autoWatchTimeframes.includes(tf);
      return {
        ...d,
        autoWatchTimeframes: has
          ? d.autoWatchTimeframes.filter((t) => t !== tf)
          : [...d.autoWatchTimeframes, tf],
      };
    });
  }

  function handleSave() {
    update(draft);
    toast.success("Ayarlar kaydedildi", { duration: 3000 });
  }

  function handleReset() {
    reset();
    setDraft(DEFAULT_SETTINGS);
    toast("Varsayılan ayarlara dönüldü", {
      duration: 3000,
      style: { borderColor: "#FF9933" },
    });
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 pb-12">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-medium text-binance-text-primary">
            Ayarlar
          </h1>
          <p className="mt-1 text-sm text-binance-text-secondary">
            Cihaza özel — multi-device sync Adım 22'de.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={handleReset}>
            <RotateCcw className="h-4 w-4" />
            Sıfırla
          </Button>
          <Button size="sm" onClick={handleSave}>
            <Save className="h-4 w-4" />
            Kaydet
          </Button>
        </div>
      </div>

      {/* ───── Risk Yönetimi ───── */}
      <Card>
        <CardHeader>
          <CardTitle>Risk Yönetimi</CardTitle>
          <CardDescription>
            Pozisyon hesaplayıcı bu parametreleri kullanır.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="space-y-1.5">
              <Label htmlFor="risk-per-trade">Risk per trade (%)</Label>
              <Input
                id="risk-per-trade"
                type="number"
                min={0.5}
                max={5}
                step={0.1}
                value={draft.riskPerTradePct}
                onChange={(e) =>
                  set(
                    "riskPerTradePct",
                    clampNumber(e.target.value, draft.riskPerTradePct, 0.5, 5)
                  )
                }
              />
              <p className="text-[11px] text-binance-text-muted">
                Önerilen: %2. Aralık: 0.5–5.
              </p>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="max-leverage">Max kaldıraç (x)</Label>
              <Input
                id="max-leverage"
                type="number"
                min={1}
                max={25}
                step={1}
                value={draft.maxLeverage}
                onChange={(e) =>
                  set(
                    "maxLeverage",
                    clampNumber(e.target.value, draft.maxLeverage, 1, 25)
                  )
                }
              />
              <p className="text-[11px] text-binance-text-muted">
                Önerilen: 10x. Aralık: 1–25.
              </p>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="default-balance">Varsayılan bakiye (USDT)</Label>
              <Input
                id="default-balance"
                type="number"
                min={0}
                step={100}
                value={draft.defaultBalanceUSDT}
                onChange={(e) =>
                  set(
                    "defaultBalanceUSDT",
                    clampNumber(
                      e.target.value,
                      draft.defaultBalanceUSDT,
                      0,
                      10_000_000
                    )
                  )
                }
              />
              <p className="text-[11px] text-binance-text-muted">
                Position sizer hesabı için.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ───── Auto-Watch S/R ───── */}
      <Card>
        <CardHeader>
          <CardTitle>Auto-Watch S/R</CardTitle>
          <CardDescription>
            Otomatik destek/direnç alarm sistemi — Adım 21B'de aktif olur. Şu an
            sadece tercih kaydedilir.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label className="mb-2 block text-xs">Sembol seçimi</Label>
            <div className="space-y-3">
              {SYMBOL_TIERS.map((tier) => (
                <div key={tier.title}>
                  <div className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
                    {tier.title}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {tier.symbols.map((sym) => {
                      const checked = draft.autoWatchSymbols.includes(sym);
                      return (
                        <button
                          key={sym}
                          type="button"
                          onClick={() => toggleSymbol(sym)}
                          className={cn(
                            "rounded border px-2 py-1 font-mono text-[11px] transition-colors",
                            checked
                              ? "border-binance-long bg-binance-long/15 text-binance-long"
                              : "border-binance-border text-binance-text-secondary hover:border-binance-text-muted"
                          )}
                        >
                          {sym.replace(/USDT$/, "")}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-2 text-[11px] text-binance-text-muted">
              Seçili: {draft.autoWatchSymbols.length} sembol
            </p>
          </div>

          <div>
            <Label className="mb-2 block text-xs">Timeframe seçimi</Label>
            <div className="flex gap-1.5">
              {AUTO_WATCH_TIMEFRAMES.map((tf) => {
                const checked = draft.autoWatchTimeframes.includes(tf);
                return (
                  <button
                    key={tf}
                    type="button"
                    onClick={() => toggleTimeframe(tf)}
                    className={cn(
                      "rounded border px-3 py-1 font-mono text-xs transition-colors",
                      checked
                        ? "border-binance-long bg-binance-long/15 text-binance-long"
                        : "border-binance-border text-binance-text-secondary hover:border-binance-text-muted"
                    )}
                  >
                    {tf}
                  </button>
                );
              })}
            </div>
            <p className="mt-2 text-[11px] text-binance-text-muted">
              CLAUDE.md spec: 4H ve 1D destekli. 15m/1H çok gürültülü.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* ───── Bildirim Tercihleri ───── */}
      <Card>
        <CardHeader>
          <CardTitle>Bildirim Tercihleri</CardTitle>
          <CardDescription>
            Telegram + browser push + ses — Adım 21B'de aktif olur.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="telegram-token">Telegram bot token</Label>
            <Input
              id="telegram-token"
              type="text"
              placeholder="123456:ABC-DEF... (henüz aktif değil)"
              value={draft.notifications.telegramBotToken}
              onChange={(e) =>
                set("notifications", {
                  ...draft.notifications,
                  telegramBotToken: e.target.value,
                })
              }
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              id="sound-enabled"
              type="checkbox"
              className="h-4 w-4 cursor-pointer accent-binance-long"
              checked={draft.notifications.soundEnabled}
              onChange={(e) =>
                set("notifications", {
                  ...draft.notifications,
                  soundEnabled: e.target.checked,
                })
              }
            />
            <Label
              htmlFor="sound-enabled"
              className="cursor-pointer text-sm"
            >
              Bildirim sesi
            </Label>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="min-level">Minimum bildirim seviyesi</Label>
            <select
              id="min-level"
              value={draft.notifications.minLevel}
              onChange={(e) =>
                set("notifications", {
                  ...draft.notifications,
                  minLevel: e.target.value as NotificationLevel,
                })
              }
              className="block h-9 w-full rounded-md border border-binance-border bg-binance-bg px-3 text-sm text-binance-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-binance-accent"
            >
              {LEVEL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <p className="text-[11px] text-binance-text-muted">
              "Uyarı" tüm B+ setup'ları ve no-trade-zone uyarılarını içerir.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
