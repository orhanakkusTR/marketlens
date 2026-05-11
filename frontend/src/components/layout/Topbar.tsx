/**
 * Üst Topbar — 90px, 2 satır (Adım 19 polish + Adım 20).
 *
 * Üst satır (40px): Nav menü + user email + Çıkış
 * Alt satır (50px): Sembol Header (route /symbol/:code'da aktif) + Piyasa Bağlamı
 *
 * Piyasa Bağlamı: gerçek macro snapshot (Adım 10).
 * Sembol Header: gerçek analysis/full payload (Adım 17).
 */
import {
  Activity,
  BarChart3,
  BookOpen,
  LayoutDashboard,
  LogOut,
  Notebook,
  Settings as SettingsIcon,
} from "lucide-react";
import { NavLink, useMatch, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { MacroStrip } from "@/components/topbar/MacroStrip";
import { MarketRegimeBar } from "@/components/topbar/MarketRegimeBar";
import { SymbolHeader } from "@/components/topbar/SymbolHeader";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/useAuth";

const NAV_ITEMS: ReadonlyArray<{
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
}> = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/heatmap", label: "Heatmap", icon: BarChart3 },
  { to: "/scanner", label: "Scanner", icon: Activity },
  { to: "/journal", label: "Journal", icon: Notebook },
  { to: "/risk", label: "Risk", icon: Activity },
  { to: "/glossary", label: "Sözlük", icon: BookOpen },
  { to: "/settings", label: "Ayarlar", icon: SettingsIcon },
];

export function Topbar() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  // Sembol detayı route match — varsa sembol kodu çıkar
  const symbolMatch = useMatch("/symbol/:code");
  const activeSymbol = symbolMatch?.params.code?.toUpperCase();

  function handleLogout() {
    logout();
    toast.success("Çıkış yapıldı", { duration: 3000 });
    navigate("/login", { replace: true });
  }

  return (
    <header className="flex flex-col border-b border-binance-border bg-binance-surface">
      {/* Üst sıra (40px): Nav menü + user */}
      <div className="flex h-10 items-center justify-between border-b border-binance-border/60 px-4">
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  cn(
                    "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs transition-colors",
                    isActive
                      ? "bg-binance-border/60 font-medium text-binance-text-primary"
                      : "text-binance-text-secondary hover:bg-binance-border/30 hover:text-binance-text-primary"
                  )
                }
              >
                <Icon className="h-3.5 w-3.5" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          {user && (
            <span className="hidden text-xs text-binance-text-secondary md:inline">
              {user.email}
            </span>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            aria-label="Çıkış yap"
            className="h-7 px-2"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden md:inline">Çıkış</span>
          </Button>
        </div>
      </div>

      {/* Orta sıra (~68px): Sembol Header (varsa) + Piyasa Bağlamı (2-satır kutulu) */}
      <div className="flex h-[68px] items-center justify-between gap-4 overflow-x-auto px-4">
        <div className="flex shrink-0 items-center">
          {activeSymbol ? (
            <SymbolHeader symbol={activeSymbol} />
          ) : (
            <span className="text-xs text-binance-text-muted">
              Sembol seçilmedi
            </span>
          )}
        </div>
        <div className="shrink-0">
          <MacroStrip />
        </div>
      </div>

      {/* Alt sıra: Piyasa Rejimi (rejim + strateji + bağlam mesajları) */}
      <MarketRegimeBar />
    </header>
  );
}
