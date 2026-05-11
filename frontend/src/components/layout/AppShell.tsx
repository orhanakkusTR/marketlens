/**
 * Tüm protected sayfalar için ortak shell.
 *
 * CSS Grid: [sidebar(240px)][main]
 *           main = topbar(60px) + content (kalan)
 *
 * NOT (Future Roadmap): Mobile responsive yok (desktop-first). Tablet/mobile
 * için hamburger nav + collapsible sidebar Adım 22+'da eklenebilir.
 */
import { Outlet } from "react-router-dom";

import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { PriceWebSocketProvider } from "@/components/ws/PriceWebSocketProvider";

export function AppShell() {
  return (
    <PriceWebSocketProvider>
      <div className="grid h-screen grid-cols-[300px_1fr] bg-binance-bg">
        <Sidebar />
        <div className="flex h-screen flex-col overflow-hidden">
          <Topbar />
          <main className="flex-1 overflow-y-auto px-4 py-4">
            <Outlet />
          </main>
        </div>
      </div>
    </PriceWebSocketProvider>
  );
}
