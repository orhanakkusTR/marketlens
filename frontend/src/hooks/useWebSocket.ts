/**
 * Native WebSocket wrapper + exponential backoff auto-reconnect.
 *
 * Reconnect schedule: 1s → 2s → 4s → 8s → 16s → 30s (max).
 * Page kapanırken cleanup; component unmount'ta da cleanup.
 */
import { useEffect, useRef, useState } from "react";

interface UseWebSocketOptions {
  url: string | null;
  enabled?: boolean;
  onOpen?: (ws: WebSocket) => void;
  onMessage?: (data: unknown) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
  reconnectMaxDelayMs?: number;
}

export type WebSocketStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected";

const INITIAL_RETRY_DELAY = 1000;
const DEFAULT_MAX_DELAY = 30_000;

export function useWebSocket({
  url,
  enabled = true,
  onOpen,
  onMessage,
  onClose,
  onError,
  reconnectMaxDelayMs = DEFAULT_MAX_DELAY,
}: UseWebSocketOptions): {
  status: WebSocketStatus;
  send: (data: unknown) => void;
  reconnect: () => void;
} {
  const [status, setStatus] = useState<WebSocketStatus>("idle");
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const timeoutRef = useRef<number | null>(null);
  const closedByUserRef = useRef(false);

  // Callback ref'leri — re-render her seferinde yeni effect tetiklemesin
  const handlersRef = useRef({ onOpen, onMessage, onClose, onError });
  handlersRef.current = { onOpen, onMessage, onClose, onError };

  function clearReconnect() {
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }

  function scheduleReconnect() {
    const delay = Math.min(
      reconnectMaxDelayMs,
      INITIAL_RETRY_DELAY * 2 ** retryRef.current
    );
    retryRef.current += 1;
    setStatus("reconnecting");
    timeoutRef.current = window.setTimeout(() => {
      connect();
    }, delay);
  }

  function connect() {
    if (!url || !enabled) {
      return;
    }
    setStatus("connecting");
    closedByUserRef.current = false;

    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch (e) {
      // Geçersiz URL vs.
      // eslint-disable-next-line no-console
      console.warn("ws_construct_failed", e);
      scheduleReconnect();
      return;
    }
    wsRef.current = ws;

    ws.onopen = () => {
      retryRef.current = 0;
      setStatus("connected");
      handlersRef.current.onOpen?.(ws);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handlersRef.current.onMessage?.(data);
      } catch (e) {
        // eslint-disable-next-line no-console
        console.warn("ws_message_parse_failed", e);
      }
    };

    ws.onerror = (event) => {
      handlersRef.current.onError?.(event);
    };

    ws.onclose = (event) => {
      handlersRef.current.onClose?.(event);
      wsRef.current = null;
      if (closedByUserRef.current) {
        setStatus("disconnected");
        return;
      }
      // Auth fail (4401) gibi durumlarda da reconnect denersek dizi atar — durdur
      if (event.code === 4401) {
        setStatus("disconnected");
        return;
      }
      scheduleReconnect();
    };
  }

  function disconnect() {
    closedByUserRef.current = true;
    clearReconnect();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus("disconnected");
  }

  // Bağlantı lifecycle'ı
  useEffect(() => {
    if (!enabled || !url) {
      return;
    }
    retryRef.current = 0;
    connect();
    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, enabled]);

  function send(data: unknown) {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
    }
  }

  function reconnect() {
    retryRef.current = 0;
    disconnect();
    closedByUserRef.current = false;
    connect();
  }

  return { status, send, reconnect };
}
