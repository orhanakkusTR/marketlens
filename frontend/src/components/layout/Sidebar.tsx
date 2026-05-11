/**
 * Sol Sidebar — 300px (Adım 19 round 3).
 *
 * Yapı:
 * - Logo + WS status dot (60px)
 * - KALİTE lejantı (collapsible)
 * - 27 sembol tier başlıklarıyla (real-time fiyat + 24h% + grade badge)
 *
 * Menü Topbar'a taşındı (Adım 19 round 3).
 *
 * Data kaynakları:
 * - Real-time fiyat: usePricesStore (WS upstream)
 * - Grade + direction: useGrades (TanStack Query — /api/v1/symbols/grades 60s)
 */
import { ConnectionStatus } from "@/components/sidebar/ConnectionStatus";
import { Legend } from "@/components/sidebar/Legend";
import { SymbolRow } from "@/components/sidebar/SymbolRow";
import { useGrades } from "@/hooks/useGrades";
import { SYMBOL_TIERS } from "@/lib/symbols";
import { usePricesStore } from "@/stores/usePrices";

export function Sidebar() {
  const prices = usePricesStore((s) => s.prices);
  const { bySymbol: grades } = useGrades("4H");

  return (
    <aside className="flex h-screen w-[300px] flex-col border-r border-binance-border bg-binance-surface">
      {/* Logo + WS status dot (60px) */}
      <div className="flex h-[60px] items-center justify-between gap-2 border-b border-binance-border px-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl">📊</span>
          <span className="text-lg font-medium text-binance-text-primary">
            MarketLens
          </span>
        </div>
        <ConnectionStatus />
      </div>

      {/* KALİTE lejantı (collapsible) */}
      <Legend />

      {/* Sembol listesi — scrollable */}
      <div className="flex-1 overflow-y-auto px-1.5 py-2">
        {SYMBOL_TIERS.map((tier) => (
          <div key={tier.title} className="mb-3">
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
    </aside>
  );
}
