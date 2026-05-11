/**
 * Top-level React error boundary.
 *
 * Render-time exception'ları yakalar, Türkçe fallback UI gösterir.
 * Async hatalar (axios) için axios interceptor + toast kullanılır.
 */
import * as React from "react";

import { Button } from "@/components/ui/button";

interface State {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  State
> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    // Konsola yaz — production'da Sentry'ye (Adım 22+)
    // eslint-disable-next-line no-console
    console.error("ErrorBoundary caught:", error, info);
  }

  reset = () => {
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-binance-bg p-6">
          <div className="w-full max-w-md rounded-lg border border-binance-border bg-binance-surface p-6 text-center">
            <h1 className="mb-2 text-xl font-medium text-binance-text-primary">
              Bir hata oluştu
            </h1>
            <p className="mb-4 text-sm text-binance-text-secondary">
              Beklenmeyen bir sorunla karşılaşıldı. Sayfayı yenileyerek tekrar
              deneyebilirsiniz.
            </p>
            <p className="mb-4 font-mono text-xs text-binance-text-muted">
              {this.state.error.message}
            </p>
            <div className="flex justify-center gap-2">
              <Button variant="secondary" onClick={this.reset}>
                Yeniden dene
              </Button>
              <Button onClick={() => window.location.reload()}>
                Sayfayı yenile
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
