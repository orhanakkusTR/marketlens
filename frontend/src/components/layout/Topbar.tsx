/**
 * Üst Topbar — 60px.
 *
 * Sol: mevcut sembol header placeholder
 * Orta: macro şeridi placeholder (gerçek Adım 20'de — TOTAL/BTC.D/DXY/VIX akışı)
 * Sağ: kullanıcı menüsü — basit "Çıkış" butonu (Radix dropdown Adım 21+'da)
 */
import { LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/useAuth";

export function Topbar() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  function handleLogout() {
    logout();
    toast.success("Çıkış yapıldı", { duration: 3000 });
    navigate("/login", { replace: true });
  }

  return (
    <header className="flex h-[60px] items-center justify-between border-b border-binance-border bg-binance-surface px-4">
      {/* Sol: placeholder sembol header */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-binance-text-muted">
          Sembol seçilmedi
        </span>
      </div>

      {/* Orta: macro şeridi placeholder (Adım 20'de gerçek veri) */}
      <div className="flex items-center gap-3 text-xs font-mono">
        <MacroPlaceholder label="TOTAL" />
        <MacroPlaceholder label="BTC.D" />
        <MacroPlaceholder label="DXY" />
        <MacroPlaceholder label="VIX" />
        <Badge variant="outline" className="text-[10px]">
          Adım 20'de aktif
        </Badge>
      </div>

      {/* Sağ: kullanıcı menüsü */}
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
        >
          <LogOut className="h-4 w-4" />
          <span className="hidden md:inline">Çıkış</span>
        </Button>
      </div>
    </header>
  );
}

function MacroPlaceholder({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-1">
      <span className="text-binance-text-muted">{label}:</span>
      <span className="text-binance-text-secondary">—</span>
    </div>
  );
}
