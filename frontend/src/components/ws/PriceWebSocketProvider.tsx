/**
 * WebSocket connection lifecycle — AppShell altında mount edilir.
 *
 * - URL: ws://<host>:8000/api/v1/ws/prices?token=<access>
 * - Bağlandığında: 27 sembol'e subscribe
 * - Mesaj: snapshot → setSnapshot; price → setPrice
 * - Reconnect: useWebSocket exponential backoff
 */
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { useWebSocket } from "@/hooks/useWebSocket";
import { ALL_SYMBOLS } from "@/lib/symbols";
import { useAuthStore } from "@/stores/useAuth";
import { usePricesStore } from "@/stores/usePrices";
import type { ServerMessage } from "@/types/api";

function buildWsUrl(token: string | null): string | null {
  if (!token) return null;
  const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
  const wsBase = apiUrl
    .replace(/^http:/, "ws:")
    .replace(/^https:/, "wss:")
    .replace(/\/$/, "");
  return `${wsBase}/api/v1/ws/prices?token=${encodeURIComponent(token)}`;
}

interface Props {
  children: React.ReactNode;
}

export function PriceWebSocketProvider({ children }: Props) {
  const token = useAuthStore((s) => s.token);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  const url = buildWsUrl(token);

  const setPrice = usePricesStore((s) => s.setPrice);
  const setSnapshot = usePricesStore((s) => s.setSnapshot);
  const setStatus = usePricesStore((s) => s.setStatus);

  const { status, send, reconnect } = useWebSocket({
    url,
    enabled: Boolean(url),
    onOpen: () => {
      // 27 sembol'e subscribe
      send({
        action: "subscribe",
        symbols: ALL_SYMBOLS,
      });
    },
    onMessage: (raw) => {
      const data = raw as ServerMessage;
      if (data.type === "snapshot") {
        setSnapshot(data.prices);
      } else if (data.type === "price") {
        setPrice(data);
      }
    },
    onClose: (event) => {
      // 4401 = auth fail → logout + redirect
      if (event.code === 4401) {
        toast.error("Oturum süresi doldu, lütfen tekrar giriş yapın.");
        logout();
        navigate("/login", { replace: true });
      }
    },
  });

  // useWebSocket status → store status
  useEffect(() => {
    setStatus(status);
  }, [status, setStatus]);

  // reconnect helper'ı window'a expose etme (test/debug için değil — Sidebar
  // butonu kullanır). Bu yüzden context yerine store'a koymak yerine prop ile
  // geçmek istemiyoruz: basit pattern olarak Sidebar useWebSocketReconnect
  // hook'u kullanır.
  useEffect(() => {
    (window as unknown as { __mlReconnect?: () => void }).__mlReconnect =
      reconnect;
    return () => {
      delete (window as unknown as { __mlReconnect?: () => void }).__mlReconnect;
    };
  }, [reconnect]);

  return <>{children}</>;
}

/** Sidebar bu hook ile manuel reconnect butonu çağırır. */
export function useReconnectPrices(): () => void {
  return () => {
    const fn = (window as unknown as { __mlReconnect?: () => void })
      .__mlReconnect;
    fn?.();
  };
}
