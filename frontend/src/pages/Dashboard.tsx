import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

export function Dashboard() {
  useDocumentTitle("Dashboard");

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Dashboard</CardTitle>
          <CardDescription>
            Macro context + sembol özetleri + watchlist akışı
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-binance-text-secondary">
            İçerik <span className="font-mono">Adım 20-21</span>'de
            implement edilecek. Şu an layout iskeleti aktif: sol panelden bir
            sembol seçerek detay sayfasına geçebilirsiniz.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
