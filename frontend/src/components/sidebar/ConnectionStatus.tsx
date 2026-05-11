/**
 * WebSocket bağlantı durumu — kompakt dot + tooltip + manuel reconnect.
 *
 * Adım 19 round 3: Label kaldırıldı, sadece dot + (disconnect ise reconnect btn).
 * Tooltip Türkçe açıklamayı taşır.
 */
import { RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useReconnectPrices } from "@/components/ws/PriceWebSocketProvider";
import { cn } from "@/lib/utils";
import { usePricesStore } from "@/stores/usePrices";

const LABELS: Record<string, string> = {
  idle: "Bağlanıyor",
  connecting: "Bağlanıyor",
  connected: "Bağlandı",
  reconnecting: "Bağlanıyor",
  disconnected: "Kopuk",
};

const COLORS: Record<string, string> = {
  idle: "bg-binance-text-muted",
  connecting: "bg-binance-accent animate-pulse",
  connected: "bg-binance-long",
  reconnecting: "bg-binance-accent animate-pulse",
  disconnected: "bg-binance-short",
};

const RING_COLORS: Record<string, string> = {
  idle: "ring-binance-text-muted/30",
  connecting: "ring-binance-accent/40",
  connected: "ring-binance-long/40",
  reconnecting: "ring-binance-accent/40",
  disconnected: "ring-binance-short/40",
};

export function ConnectionStatus() {
  const status = usePricesStore((s) => s.status);
  const reconnect = useReconnectPrices();

  const showReconnect = status === "disconnected";

  return (
    <div className="flex items-center gap-1.5">
      <span
        title={LABELS[status]}
        aria-label={LABELS[status]}
        className={cn(
          "h-3 w-3 rounded-full ring-2",
          COLORS[status],
          RING_COLORS[status]
        )}
      />
      {showReconnect && (
        <Button
          variant="ghost"
          size="sm"
          className="h-6 px-1.5 text-[10px]"
          onClick={reconnect}
          title="Yeniden bağlan"
        >
          <RefreshCw className="h-3 w-3" />
        </Button>
      )}
    </div>
  );
}
