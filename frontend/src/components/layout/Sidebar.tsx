/**
 * Sol Sidebar — 240px.
 *
 * - Logo (60px üst)
 * - 27 sembol tier başlıklarıyla placeholder listesi (scrollable)
 *   (gerçek implementasyon Adım 19 — multi-symbol WebSocket akışı)
 * - Alt nav linkler (Dashboard, Heatmap, Scanner, Journal, Settings)
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

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// CLAUDE.md sembol tier'ları (placeholder; gerçek veri Adım 19'da)
const SYMBOL_TIERS: ReadonlyArray<{
  title: string;
  symbols: ReadonlyArray<string>;
}> = [
  {
    title: "Tier 1 — Major",
    symbols: [
      "BTCUSDT",
      "ETHUSDT",
      "SOLUSDT",
      "BNBUSDT",
      "XRPUSDT",
      "AVAXUSDT",
      "ADAUSDT",
      "DOGEUSDT",
      "POLUSDT",
      "DOTUSDT",
    ],
  },
  {
    title: "Tier 2 — Popüler",
    symbols: ["LINKUSDT", "ATOMUSDT", "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT"],
  },
  {
    title: "Tier 3 — Meme",
    symbols: ["SHIBUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT"],
  },
  {
    title: "Tier 4 — DeFi",
    symbols: ["UNIUSDT", "AAVEUSDT", "LDOUSDT", "INJUSDT", "SUIUSDT", "SEIUSDT"],
  },
  {
    title: "Emtia",
    symbols: ["XAUUSDT"],
  },
];

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
  return (
    <aside className="flex h-screen w-60 flex-col border-r border-binance-border bg-binance-surface">
      {/* Logo (60px) */}
      <div className="flex h-[60px] items-center gap-2 border-b border-binance-border px-4">
        <span className="text-2xl">📊</span>
        <span className="text-lg font-medium text-binance-text-primary">
          MarketLens
        </span>
      </div>

      {/* Sembol listesi — scrollable, kalan dikey alan */}
      <div className="flex-1 overflow-y-auto px-2 py-3">
        {SYMBOL_TIERS.map((tier) => (
          <div key={tier.title} className="mb-4">
            <div className="mb-1 px-2 text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
              {tier.title}
            </div>
            <ul className="space-y-0.5">
              {tier.symbols.map((sym) => (
                <li key={sym}>
                  <NavLink
                    to={`/symbol/${sym}`}
                    className={({ isActive }) =>
                      cn(
                        "flex items-center justify-between rounded-md px-2 py-1.5 text-xs transition-colors",
                        isActive
                          ? "bg-binance-border/60 text-binance-text-primary"
                          : "text-binance-text-secondary hover:bg-binance-border/30 hover:text-binance-text-primary"
                      )
                    }
                  >
                    <span className="font-mono">{sym.replace("USDT", "")}</span>
                    <Badge variant="outline" className="text-[10px]">
                      —
                    </Badge>
                  </NavLink>
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
