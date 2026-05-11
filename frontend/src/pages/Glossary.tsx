/**
 * Sözlük sayfası — MarketLens trader terimleri (Türkçe, Adım 20).
 *
 * 7 bölüm:
 *  1. Setup Kalitesi (A/B/C/D/DUR + macro modifier)
 *  2. Confidence Seviyesi (VERY_LOW...VERY_HIGH)
 *  3. Counter-Trend Uyarıları
 *  4. Trade Quality Filter
 *  5. No-Trade Zone Tipleri
 *  6. Risk Yönetimi
 *  7. Confluence İndikatörleri
 *
 * Üstte arama kutusu — Türkçe locale uyumlu substring (term + def).
 */
import { Search } from "lucide-react";
import { useMemo, useState } from "react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

interface Entry {
  term: string;
  def: string;
}

interface Section {
  id: string;
  title: string;
  intro?: string;
  entries: Entry[];
}

const SECTIONS: ReadonlyArray<Section> = [
  {
    id: "setup-kalitesi",
    title: "Setup Kalitesi",
    intro:
      "Confluence skorundan üretilen 4 kademe + DUR. Pozisyon büyüklüğü kararını doğrudan etkiler.",
    entries: [
      {
        term: "A (90–100)",
        def: "En güçlü sinyal. Tüm indikatörler aynı yöne hizalı, macro destekli. Tam pozisyon (varsayılan %2 risk) açılabilir.",
      },
      {
        term: "B (70–89)",
        def: "Güçlü sinyal, küçük çelişkiler olabilir. Normal pozisyon önerilir. Çoğu işlem bu kademede yapılır.",
      },
      {
        term: "C (50–69)",
        def: "Orta sinyal. Belirgin çelişki var. Küçük pozisyon (yarı boyut) veya beklemek tavsiye edilir.",
      },
      {
        term: "D (<50)",
        def: "Zayıf sinyal. İndikatörler dağınık. Pozisyon açma; sadece izleme listesinde tut.",
      },
      {
        term: "DUR",
        def: "No-Trade Zone tetiklendi (weekend, CPI/FOMC ± 4h, aşırı volatilite, art arda stop, vb.). Setup ne olursa olsun pozisyon açılmaz.",
      },
      {
        term: "Macro modifier",
        def: "Lokal skora -25 ile +25 arası eklenir. > +15 ise setup kalitesi +1 not yükselir, < -15 ise -1 not düşer.",
      },
    ],
  },
  {
    id: "confidence",
    title: "Confidence Seviyesi",
    intro:
      "Olasılık ≠ Confidence. Olasılık matematiksel hesap; Confidence bu hesabın kanıt seviyesidir. Trade Journal doldukça yükselir.",
    entries: [
      {
        term: "VERY_LOW (<5 işlem)",
        def: "Bu setup tipinde geçmiş veri çok az. Sistemin kendine güveni minimum, deneme aşaması.",
      },
      {
        term: "LOW (5–14 işlem)",
        def: "Az veri. Dikkatli olun; sonuçlar henüz istatistiksel olarak anlamlı değil.",
      },
      {
        term: "MEDIUM (15–29 işlem)",
        def: "Orta kanıt. Pattern belirginleşiyor ama hâlâ örneklem büyütmek faydalı.",
      },
      {
        term: "HIGH (30–59 işlem)",
        def: "Güçlü kanıt. Olasılık tahminlerine güven daha sağlam.",
      },
      {
        term: "VERY_HIGH (60+ işlem)",
        def: "Çok güçlü kanıt. Sistemin verdiği olasılığa tam güvenebilirsiniz.",
      },
    ],
  },
  {
    id: "counter-trend",
    title: "Counter-Trend Uyarıları",
    intro:
      "Sistem kendi sinyalini sorgular. 2+ uyarı varsa setup kalitesi -1 not, pozisyon %50 küçültme önerisi gelir.",
    entries: [
      {
        term: "Parabolik hareket",
        def: "Son 2 saatte %3+ hareket. Exhaustion (tükenme) riski yüksek — dönüş yakın olabilir.",
      },
      {
        term: "Ekstrem funding",
        def: "Funding > %0.08 veya < -%0.08. Aşırı kalabalık taraf — squeeze (zıt yönde sert dönüş) riski.",
      },
      {
        term: "Aşırı L/S oranı",
        def: "Long/Short oranı > 3 veya < 0.33. Bir taraf çok kalabalık, ters yönde temizleme olabilir.",
      },
      {
        term: "Hacim tükenmesi",
        def: "Yükselişte (veya düşüşte) son 3 mumda hacim azalıyor. Hareketin yakıtı bitiyor.",
      },
    ],
  },
  {
    id: "trade-quality",
    title: "Trade Quality Filter",
    intro:
      "Confluence yüksek olsa bile bazı setup'lar vasattır. 5 faktörden gelen skor: AVOID / WEAK / GOOD / EXCELLENT.",
    entries: [
      {
        term: "Volatilite (ATR > %0.8)",
        def: "Yeterli oynaklık var; pozisyon makul sürede hedefe ulaşabilir.",
      },
      {
        term: "Trend (ADX > 20)",
        def: "Piyasa trendde, range değil. Trend takip stratejisi için zemin sağlam.",
      },
      {
        term: "Macro netlik",
        def: "DXY, S&P, VIX yön açısından uyumlu. Karışık macro işlem güvenini düşürür.",
      },
      {
        term: "Hacim büyümesi",
        def: "Son 4 mumda hacim artıyor. Hareket arkasında alıcı/satıcı taban var.",
      },
      {
        term: "Temiz yol",
        def: "Major S/R seviyelerine > 2 ATR mesafe. Hedefe giderken takılma riski düşük.",
      },
    ],
  },
  {
    id: "no-trade-zone",
    title: "No-Trade Zone Tipleri",
    intro:
      "Sistem bu durumlarda pozisyon önermez. Bazıları bloklayıcı (DUR), bazıları sadece uyarı.",
    entries: [
      {
        term: "Weekend",
        def: "Cuma 22:00 UTC – Pazartesi 02:00 UTC arası. Düşük hacim + boşluk riski. Bloklayıcı.",
      },
      {
        term: "Low liquidity (Asya seansı)",
        def: "00:00–08:00 UTC arası. Hacim düşük, manipülasyon riski yüksek. Uyarı.",
      },
      {
        term: "High volatility",
        def: "BTC son 24h hareketi %8+. Stop'lar daha rahat süpürülür. Pozisyon boyutu otomatik küçültülmeli.",
      },
      {
        term: "Range market",
        def: "ADX < 15 ve yatay konsolidasyon. Trend takip stratejisi çalışmaz.",
      },
      {
        term: "Macro event (CPI, FOMC, NFP)",
        def: "Olay ± 4 saat. Beklenmedik volatilite + spread genişler. Bloklayıcı.",
      },
      {
        term: "Daily limit",
        def: "Günde 5 işlem veya %4 risk aşıldı. 24h reset bekle.",
      },
      {
        term: "Tilt (3 ardışık stop)",
        def: "Son 24h içinde 3 stop. Auto-pause devreye girer, risk %1.0'a düşer (4 saat).",
      },
    ],
  },
  {
    id: "risk",
    title: "Risk Yönetimi",
    entries: [
      {
        term: "R/R (Risk/Reward)",
        def: "Beklenen kazanç / kaybedeceğin risk. R/R = (TP – Entry) / (Entry – Stop). Hedef minimum 1.5, ideal 2.0+.",
      },
      {
        term: "Position size (formül)",
        def: "risk_amount = bakiye × risk_pct; pozisyon_size = risk_amount / (stop_mesafe_pct / 100). Kaldıraç = pozisyon / margin.",
      },
      {
        term: "Volatility-adjusted risk",
        def: "BTC 24h hareketi %5+'da risk %0.7×; %8+'da %0.5×. Yüksek volatilitede pozisyon otomatik küçülür.",
      },
      {
        term: "Funding",
        def: "Her 8 saatte futures pozisyonunun ödediği/aldığı ücret. Long + pozitif funding = gider; long + negatif = gelir.",
      },
      {
        term: "Liquidation price",
        def: "Margin tükendiğinde borsa pozisyonu kapatır. Bu seviyeyi her zaman stop'un ötesinde tut — stop liq fiyatına yakınsa kaldıraç çok yüksek demek.",
      },
      {
        term: "Smart risk reduction",
        def: "2 ardışık kayıp → risk %1.5 (1h). 3 ardışık kayıp → risk %1.0 (4h). 3 ardışık stop → auto-pause.",
      },
      {
        term: "Daily limits",
        def: "Default: max 5 işlem/gün, max %4 toplam risk/gün. Aşılırsa No-Trade Zone aktif.",
      },
    ],
  },
  {
    id: "confluence",
    title: "Confluence İndikatörleri",
    intro:
      "Lokal confluence skoru bu indikatörlerin ağırlıklı toplamından hesaplanır. Ana karar TF: 4H + 1D.",
    entries: [
      {
        term: "EMA (Exponential Moving Average)",
        def: "Son fiyatlara daha çok ağırlık veren ortalama. 50/100/200 yaygın. Üst üste ve fiyatın üstündeyse trend yukarı.",
      },
      {
        term: "SMA (Simple Moving Average)",
        def: "Basit eşit ağırlıklı ortalama. 1D ve üstünde tercih edilir, çünkü uzun vadeli yön gösterir.",
      },
      {
        term: "RSI (Relative Strength Index)",
        def: "Momentum osilatörü 0–100. >70 aşırı alım, <30 aşırı satım. Divergence sinyali güçlüdür.",
      },
      {
        term: "MACD",
        def: "İki EMA farkı + sinyal hattı + histogram. Cross-over yön değişimi, histogram momentum gücü.",
      },
      {
        term: "Stochastic RSI",
        def: "RSI üzerine uygulanan stochastic — daha hızlı dönüş sinyalleri. K ve D çizgileri.",
      },
      {
        term: "Bollinger Bands",
        def: "20 SMA ± 2 standart sapma. Daralma volatilite öncesi, fiyatın üst banda dokunması overbought.",
      },
      {
        term: "ATR (Average True Range)",
        def: "Ortalama gerçek menzil. Volatilite ölçüsü; stop ve TP mesafelerini belirlemede temel.",
      },
      {
        term: "OBV (On-Balance Volume)",
        def: "Yön ile çarpılmış kümülatif hacim. OBV trendi fiyat trendini doğruluyor mu kontrol edilir.",
      },
      {
        term: "VWAP",
        def: "Hacim ağırlıklı ortalama fiyat (günlük reset). Kurumsal alıcının ortalama maliyetini gösterir.",
      },
      {
        term: "Volume Profile (POC/VAH/VAL)",
        def: "Fiyat dağılımında en çok işlem geçen seviye (POC) ve değer alanı sınırları. Güçlü destek/direnç.",
      },
      {
        term: "Ichimoku Cloud",
        def: "Trend + momentum + S/R birarada. Fiyat bulutun üstünde = yukarı yön; bulut kalınlığı = trend gücü.",
      },
      {
        term: "Fibonacci Retracement",
        def: "0.382 / 0.5 / 0.618 / 0.786 oranları. Trendin geri çekilme seviyelerini ölçer.",
      },
      {
        term: "Order Block (SMC)",
        def: "Güçlü bir hareket öncesi son zıt mum. Fiyat geri gelince bu bölge tepki verir.",
      },
      {
        term: "Fair Value Gap (FVG)",
        def: "3 mumda oluşan boşluk — fiyat zamanla bu gap'i doldurmaya gelir.",
      },
      {
        term: "Liquidity Sweep",
        def: "Swing high/low'un kısa süreli kırılışı ve hızlı dönüş — likidite avı.",
      },
      {
        term: "BOS / CHoCH",
        def: "Break of Structure / Change of Character. Market yapısının kırılma veya yön değişim sinyali.",
      },
      {
        term: "Funding rate",
        def: "Perpetual futures'ta long-short denge ücreti. Aşırı pozitif = long kalabalık (squeeze riski).",
      },
      {
        term: "Open Interest (OI)",
        def: "Açık pozisyon toplamı. Fiyat artarken OI artıyor = yeni para giriyor (sağlıklı trend).",
      },
      {
        term: "Long/Short Ratio",
        def: "Trader'ların long/short dağılımı. Aşırı bir tarafa kaymışsa kontrarian sinyal.",
      },
    ],
  },
];

export function Glossary() {
  useDocumentTitle("Sözlük");
  const [query, setQuery] = useState("");

  const normalized = query.trim().toLocaleLowerCase("tr-TR");

  const filtered = useMemo(() => {
    if (!normalized) return SECTIONS;
    return SECTIONS.map((section) => ({
      ...section,
      entries: section.entries.filter((e) => {
        const t = e.term.toLocaleLowerCase("tr-TR");
        const d = e.def.toLocaleLowerCase("tr-TR");
        return t.includes(normalized) || d.includes(normalized);
      }),
    })).filter((section) => section.entries.length > 0);
  }, [normalized]);

  return (
    <div className="mx-auto max-w-4xl space-y-4 pb-12">
      <div>
        <h1 className="text-2xl font-medium text-binance-text-primary">
          Sözlük
        </h1>
        <p className="mt-1 text-sm text-binance-text-secondary">
          MarketLens'te kullanılan terimler — kısa, Türkçe açıklamalar.
        </p>
      </div>

      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-binance-text-muted" />
        <Input
          type="search"
          placeholder="Terim ara (örn. RSI, funding, weekend)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-9"
        />
      </div>

      {filtered.length === 0 && (
        <Card>
          <CardContent className="py-6 text-center text-sm text-binance-text-muted">
            "{query}" için sonuç bulunamadı.
          </CardContent>
        </Card>
      )}

      <div className="space-y-4">
        {filtered.map((section) => (
          <Card key={section.id} id={section.id}>
            <CardHeader>
              <CardTitle className="text-lg">{section.title}</CardTitle>
              {section.intro && (
                <p className="mt-1 text-xs text-binance-text-secondary">
                  {section.intro}
                </p>
              )}
            </CardHeader>
            <CardContent>
              <dl className="space-y-3">
                {section.entries.map((entry) => (
                  <div
                    key={entry.term}
                    className="grid grid-cols-1 gap-1 md:grid-cols-[200px_1fr] md:gap-4"
                  >
                    <dt className="font-mono text-sm font-medium text-binance-text-primary">
                      {entry.term}
                    </dt>
                    <dd className="text-sm leading-relaxed text-binance-text-secondary">
                      {entry.def}
                    </dd>
                  </div>
                ))}
              </dl>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
