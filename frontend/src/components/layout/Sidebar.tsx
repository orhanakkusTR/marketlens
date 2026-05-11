/**
 * Sol Sidebar — 240px (Adım 19 gerçek implementasyon).
 *
 * Yapı:
 * - Logo (60px üst)
 * - ConnectionStatus (WS bağlantı dot + manuel reconnect)
 * - 27 sembol tier başlıklarıyla (real-time fiyat + 24h% + grade badge)
 * - Alt nav linkler
 *
 * Data kaynakları:
 * - Real-time fiyat: usePricesStore (WS upstream)
 * - Grade + direction: useGrades (TanStack Query — /api/v1/symbols/grades 60s)
 */
import {
  Activity,
  BarChart3,
  BookOpen,
  LayoutDashboard,
  Notebook,
  Settings as SettingsIcon,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { ConnectionStatus } from "@/components/sidebar/ConnectionStatus";
import { SymbolRow } from "@/components/sidebar/SymbolRow";
import { useGrades } from "@/hooks/useGrades";
import { SYMBOL_TIERS } from "@/lib/symbols";
import { cn } from "@/lib/utils";
import { usePricesStore } from "@/stores/usePrices";

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

export function Sidebar() {
  const prices = usePricesStore((s) => s.prices);
  const { bySymbol: grades } = useGrades("4H");

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-binance-border bg-binance-surface">
      {/* Logo (60px) */}
      <div className="flex h-[60px] items-center gap-2 border-b border-binance-border px-4">
        <span className="text-2xl">📊</span>
        <span className="text-lg font-medium text-binance-text-primary">
          MarketLens
        </span>
      </div>

      {/* WS connection status */}
      <ConnectionStatus />

      {/* Sembol listesi — scrollable */}
      <div className="flex-1 overflow-y-auto px-2 py-3">
        {SYMBOL_TIERS.map((tier) => (
          <div key={tier.title} className="mb-4">
            <div className="mb-1 px-2 text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
              {tier.title}
            </div>
            <ul className="space-y-0.5">
              {tier.symbols.map((sym) => (
                <li key={sym}>
                  <SymbolRow
                    symbol={sym}
                    price={prices.get(sym)}
                    grade={grades.get(sym)}
                  />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Alt nav */}
      <nav className="border-t border-binance-border px-2 py-2">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-binance-border/60 text-binance-text-primary"
                    : "text-binance-text-secondary hover:bg-binance-border/30 hover:text-binance-text-primary"
                )
              }
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}
