import { useParams } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

export function SymbolDetail() {
  const { code } = useParams<{ code: string }>();
  const symbol = code?.toUpperCase() ?? "BİLİNMEYEN";
  useDocumentTitle(symbol);

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <CardTitle className="font-mono">{symbol}</CardTitle>
            <Badge variant="accent">placeholder</Badge>
          </div>
          <CardDescription>
            Sembol detayı — confluence, alignment, scenario, risk, Aksiyon Özeti
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-binance-text-secondary">
            İçerik <span className="font-mono">Adım 21-22</span>'de
            implement edilecek. Backend{" "}
            <span className="font-mono">
              GET /api/v1/analysis/full/{symbol}/{"{tf}"}
            </span>{" "}
            tek istekte tüm verisi hazır.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
