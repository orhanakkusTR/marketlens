/**
 * Sembol Detayı — Adım 21.
 *
 * URL: /symbol/:code?tf=4H
 * İçerik: <ActionSummary /> — 6 bölüm composite (Header, Scenario, Position,
 * Warnings, Macro+Korelasyon, İndikatör Özeti).
 *
 * TF state Topbar SymbolHeader'da yönetiliyor (URL ?tf=).
 */
import { useParams, useSearchParams } from "react-router-dom";

import { ActionSummary } from "@/components/dashboard/ActionSummary";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

const VALID_TFS: ReadonlyArray<string> = ["15m", "1H", "4H", "1D"];
const DEFAULT_TF = "4H";

export function SymbolDetail() {
  const { code } = useParams<{ code: string }>();
  const [searchParams] = useSearchParams();
  const symbol = code?.toUpperCase() ?? "";
  const tfParam = searchParams.get("tf");
  const tf =
    tfParam && VALID_TFS.includes(tfParam) ? tfParam : DEFAULT_TF;

  useDocumentTitle(`${symbol.replace(/USDT$/, "")} — ${tf}`);

  if (!symbol) {
    return (
      <div className="mx-auto max-w-5xl text-sm text-binance-text-muted">
        Sembol bulunamadı.
      </div>
    );
  }

  return <ActionSummary symbol={symbol} timeframe={tf} />;
}
