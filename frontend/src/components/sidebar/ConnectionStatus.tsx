/**
 * WebSocket bağlantı durumu — küçük dot + tooltip + manuel reconnect.
 */
import { RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useReconnectPrices } from "@/components/ws/PriceWebSocketProvider";
import { cn } from "@/lib/utils";
import { usePricesStore } from "@/stores/usePrices";

const LABELS: Record<string, string> = {
  idle: "Bekliyor",
  connecting: "Bağlanıyor...",
  connected: "Bağlandı",
  reconnecting: "Bağlantı koptu, yeniden deneniyor",
  disconnected: "Bağlantı kapalı",
};

const COLORS: Record<string, string> = {
  idle: "bg-binance-text-muted",
  connecting: "bg-binance-accent animate-pulse",
  connected: "bg-binance-long",
  reconnecting: "bg-binance-accent animate-pulse",
  disconnected: "bg-binance-short",
};

export function ConnectionStatus() {
  const status = usePricesStore((s) => s.status);
  const reconnect = useReconnectPrices();

  const showReconnect = status === "disconnected";

  return (
    <div className="flex items-center justify-between border-b border-binance-border px-3 py-1.5">
      <div className="flex items-center gap-2" title={LABELS[status]}>
        <span className={cn("h-2 w-2 rounded-full", COLORS[status])} />
        <span className="text-[10px] text-binance-text-muted">
          {LABELS[status]}
        </span>
      </div>
      {showReconnect && (
        <Button
          variant="ghost"
          size="sm"
          className="h-6 px-2 text-[10px]"
          onClick={reconnect}
        >
          <RefreshCw className="h-3 w-3" />
          Yeniden Bağlan
        </Button>
      )}
    </div>
  );
}
