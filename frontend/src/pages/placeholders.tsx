/**
 * Placeholder sayfalar — Adım 22+'da gerçek içerik eklenecek.
 *
 * Layout iskeletinin görsel olarak test edilebilir olması için.
 */
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

interface PlaceholderProps {
  title: string;
  description: string;
  step: string;
}

function PlaceholderPage({ title, description, step }: PlaceholderProps) {
  useDocumentTitle(title);
  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-binance-text-secondary">
            İçerik <span className="font-mono">{step}</span>'de
            implement edilecek.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

export function Heatmap() {
  return (
    <PlaceholderPage
      title="Heatmap"
      description="27 sembol için matrix görünümü (TF × confluence + grade)"
      step="Adım 22"
    />
  );
}

export function Scanner() {
  return (
    <PlaceholderPage
      title="Scanner"
      description="Setup tarayıcı + watchlist"
      step="Adım 23+"
    />
  );
}

export function Journal() {
  return (
    <PlaceholderPage
      title="Trade Journal"
      description="Manuel kayıt + pattern detection (Future Phase)"
      step="Adım 31+"
    />
  );
}

export function Risk() {
  return (
    <PlaceholderPage
      title="Risk Hesaplayıcı"
      description="Bağımsız position size + R/R kalkülatörü"
      step="Adım 22"
    />
  );
}

export function Settings() {
  return (
    <PlaceholderPage
      title="Ayarlar"
      description="Risk parametreleri, Auto-Watch, alarm tercihleri"
      step="Adım 22-25"
    />
  );
}

export function Glossary() {
  return (
    <PlaceholderPage
      title="Sözlük"
      description="Teknik terimler + tooltip'lerin tam açıklamaları"
      step="Adım 22"
    />
  );
}
