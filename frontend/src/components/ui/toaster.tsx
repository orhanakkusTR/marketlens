/**
 * Sonner Toaster — Binance dark renkleriyle.
 *
 * Toast pozisyonu sağ üst (default), dark theme.
 * Süreler: success 3sn, error 5sn (toast() call'larında override edilir).
 */
import { Toaster as SonnerToaster } from "sonner";

export function Toaster() {
  return (
    <SonnerToaster
      theme="dark"
      position="top-right"
      duration={4000}
      closeButton
      richColors
      toastOptions={{
        classNames: {
          toast:
            "bg-binance-surface border border-binance-border text-binance-text-primary",
          description: "text-binance-text-secondary",
          actionButton: "bg-binance-accent text-binance-bg",
          cancelButton: "bg-binance-border text-binance-text-primary",
        },
      }}
    />
  );
}
