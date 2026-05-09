# MarketLens — Mimari Dokümantasyonu (v2)

## 1. Proje Vizyonu

**MarketLens**, vadeli ve spot kripto + emtia işlemleri için multi-timeframe teknik + temel + on-chain + macro analiz üreten **profesyonel kişisel karar destek terminalidir**. Sinyal botu **değildir** — kullanıcıya yapılandırılmış, kaliteli bilgi ve aksiyon önerisi sunar; kararı kullanıcı verir.

### Felsefe

- **Sinyal değil, karar desteği.** Sistem "%X olasılıkla şu, hedefler şunlar, invalidasyon şu" der. Tetiği kullanıcı çeker.
- **Multi-katman analiz.** Lokal (sembolün kendi indikatörleri) + Macro (piyasa bağlamı) + Korelasyon ayrı ayrı değerlendirilir.
- **Kalite > Miktar.** Az ve A-kalite setup, çok ve karışık sinyalden iyidir.
- **Risk yönetimi öne çıkartılır.** Pozisyon ölçeği, kaldıraç, günlük limitler, no-trade zone, tilt koruması — sistemin core parçası.
- **Şeffaflık + Eğitim.** Her hesaplamanın "neden böyle" cevabı kullanıcıya verilir (tooltip, "Hesabı Göster" modalı, sözlük). Kullanıcı zamanla öğrenir.
- **Geri besleme.** Trade journal ve pattern detection ile kullanıcının kendi performansından öğrenir.
- **Aksiyon Özeti.** Her analizin sonunda tek bakışta "ne yapayım" cevabı.

### KESİN KURAL — Manuel İşlem

**Sistem ASLA borsaya otomatik emir göndermez.** MarketLens sadece bir **karar destek aracıdır** — tüm işlem tetikleri kullanıcının manuel müdahalesiyle gerçekleşir.

- Sistem önerir, kullanıcı Binance'a manuel girip emri verir.
- Trade Journal kayıtları kullanıcı tarafından manuel girilir veya "Pozisyon Detaylarını Kopyala" → Binance → açıldıktan sonra "Journal'a Ekle" butonu ile.
- Position Management uyarıları **bilgilendiricidir**, otomatik aksiyon almaz. "Stop'a yaklaşıyor" mesajı atar, kullanıcı isterse Binance'tan kendisi taşır.
- Binance trading API yetkilendirmesi gerekmez. Sadece public okuma yetkisi yeterlidir.

Bu kural projenin temel güvenlik garantisidir. İleride otomatik trading istense bile **bu proje kapsamında değildir**, ayrı bir proje olarak ele alınmalıdır.

---

## 2. Stack Özeti

### Backend
- **FastAPI** (Python 3.11) — async REST API + WebSocket
- **pandas-ta** — indikatör hesaplama
- **python-binance** — Binance Spot + Futures REST/WebSocket
- **yfinance** — GOLD, DXY, S&P, NASDAQ, VIX, ABD 10Y
- **httpx** — async HTTP (Coinglass, CoinGecko, CryptoPanic, Etherscan, Telegram)
- **pydantic v2** — veri validasyonu
- **SQLAlchemy 2** + **asyncpg** — DB ORM
- **Alembic** — DB migration
- **Celery** + **Redis** — arka plan görevleri
- **APScheduler** — zamanlanmış tarama
- **python-telegram-bot** — Telegram bildirimleri
- **anthropic** — AI Asistan (Claude API, Faz 4)
- **structlog** — yapılandırılmış loglama
- **slowapi** — rate limit
- **tenacity** — retry
- **pybreaker** — circuit breaker

### Frontend
- **React 18** + **Vite** + **TypeScript** (strict)
- **TailwindCSS** + **shadcn/ui**
- **lightweight-charts** v4 (TradingView'ın açık kaynak grafik motoru)
- **recharts** — confluence skor barları, equity curve, heatmap
- **TanStack Query v5** — server state
- **Zustand** — client state
- **react-hook-form** + **zod** — form
- **lucide-react** — ikonlar
- **Sonner** — toast

### Infrastructure
- **PostgreSQL 16** — kalıcı veri
- **Redis 7** — cache + Celery broker + WebSocket pub/sub
- **Docker** + **docker-compose**
- **Nginx** — reverse proxy + SSL
- **DigitalOcean Droplet** — production
- **Cloudflare** — DNS + DDoS
- **Sentry** — error tracking

### Veri Kaynakları
| Kaynak | Veri | Maliyet | Faz |
|--------|------|---------|-----|
| Binance Spot API | OHLCV, fiyat, hacim | Ücretsiz | 1 |
| Binance Futures API | Funding, OI, L/S, likidasyonlar | Ücretsiz | 1 |
| Binance Depth API | Order book derinliği | Ücretsiz | 1 |
| CoinGecko API | TOTAL, TOTAL2, TOTAL3, BTC.D, ETH.D, OTHERS.D | Ücretsiz | 1 |
| yfinance | GOLD, DXY, S&P, NASDAQ, VIX, ABD 10Y | Ücretsiz | 1 |
| Alternative.me | Fear & Greed Index | Ücretsiz | 1 |
| forexfactory (scrape) | Ekonomik takvim | Ücretsiz | 1 |
| Coinglass API (Hobbyist) | Likidasyon heatmap, agg. data, ETF flow | $29/ay | 2 |
| CryptoPanic API | Kripto haberleri | Ücretsiz tier | 2 |
| Etherscan/BSCScan | On-chain transferleri (basit) | Ücretsiz | 3 |
| Anthropic Claude API | AI Asistan | ~$5-20/ay | 4 |

---

## 3. Sistem Mimarisi (Üst Düzey)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React/TS)                           │
│   Dashboard │ Heatmap │ Scanner │ Journal │ Risk │ Backtest │ AI    │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ REST + WebSocket
┌─────────────────────────────▼───────────────────────────────────────┐
│                        FASTAPI BACKEND                               │
│                                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐│
│  │   Data       │ │  Indicator   │ │  Confluence  │ │  Setup       ││
│  │   Ingestion  │ │  Engine      │ │  & Macro     │ │  Quality     ││
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘│
│         │                │                │                │        │
│         └────────────────┴────────────────┴────────────────┘        │
│                                  │                                   │
│  ┌──────────────────┐  ┌─────────▼─────────┐  ┌──────────────────┐  │
│  │  Risk Manager    │◄─►│  Analysis        │◄─►│  Scenario Gen    │  │
│  │  (Position,      │  │  Orchestrator    │  │  + Action Summary│  │
│  │   Limits, NTZ)   │  │                   │  │                  │  │
│  └──────────────────┘  └─────────┬─────────┘  └──────────────────┘  │
│                                  │                                   │
│  ┌──────────────────┐  ┌─────────▼─────────┐  ┌──────────────────┐  │
│  │  Scanner         │  │  Trade Journal   │  │  Alert Manager   │  │
│  │  (Watchlist,     │  │  + Position Mgmt │  │  + Telegram Bot  │  │
│  │   Heatmap)       │  │                   │  │  + Priority Tier │  │
│  └──────────────────┘  └───────────────────┘  └──────────────────┘  │
│                                                                      │
│  ┌──────────────────┐  ┌───────────────────┐  ┌──────────────────┐  │
│  │  Backtest Engine │  │  AI Assistant    │  │  Macro Context   │  │
│  │  (Phase 4)       │  │  (Phase 4)        │  │  + Rotation      │  │
│  └──────────────────┘  └───────────────────┘  └──────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
            │
┌───────────▼─────────────────────────────────────────────────────────┐
│                PostgreSQL  +  Redis  +  Celery Workers               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Modüller (Detaylı)

### 4.1 Data Ingestion Layer

**Görev:** Tüm dış kaynaklardan veriyi tek normalize formata çekmek.

**Bileşenler:**
- `BinanceSpotClient` — OHLCV (1m, 5m, 15m, 1h, 4h, 1d, 1w, 1M)
- `BinanceFuturesClient` — funding, OI, L/S ratio, top trader pozisyonu, son likidasyonlar
- `BinanceDepthClient` — order book (limit=1000)
- `BinanceWebSocketClient` — real-time fiyat akışı
- `CoinGeckoClient` — TOTAL, TOTAL2, TOTAL3, dominans verileri
- `YFinanceClient` — GOLD, DXY, S&P, NASDAQ, VIX, ABD 10Y
- `AlternativeMeClient` — Fear & Greed
- `ForexFactoryClient` — ekonomik takvim (scraping, haftalık cron)
- `CoinglassClient` (Phase 2) — likidasyon heatmap, ETF flow
- `CryptoPanicClient` (Phase 2) — haber akışı
- `EtherscanClient` (Phase 3) — on-chain transferleri
- `AnthropicClient` (Phase 4) — AI asistan

**Cache Stratejisi (Redis):**

| Veri | TTL |
|------|-----|
| 1m mum | 30 sn |
| 5m mum | 2 dk |
| **15m mum** | **1 dk** |
| 1h mum | 10 dk |
| 4h mum | 30 dk |
| 1d mum | 1 saat |
| Funding rate | 1 dk |
| Open Interest | 1 dk |
| Order book | 5 sn |
| Fear & Greed | 1 saat |
| TOTAL/Dominans | 5 dk |
| DXY/SP500/VIX | 5 dk |
| Liquidation heatmap | 30 sn |
| News feed | 5 dk |
| Macro calendar | 12 saat |

**Hata Yönetimi:**
- Her external API için circuit breaker (`pybreaker`)
- Retry policy: exponential backoff, max 3 retry
- Rate limit'e ulaşırsa fallback cache, kullanıcıya "veri eski" uyarısı

---

### 4.2 Indicator Engine

**Görev:** Ham OHLCV verisinden tüm indikatörleri hesaplamak.

#### Hareketli Ortalama (MA) — Dinamik Strateji

Sistem seçili timeframe'e göre **otomatik** uygun MA tipini kullanır:

| TF | MA Tipi | Mantık |
|----|---------|--------|
| **15m, 1H, 4H** | EMA 50, EMA 100, EMA 200 | Hızlı tepki kritik |
| 1D | EMA 50, EMA 100, **SMA 200** | EMA hızlı, SMA 200 kurumsal seviye |
| 1W, 1M | SMA 50, SMA 100, SMA 200 | Uzun vade gürültü süzme |

Settings'te toggle ile manuel override mümkün ("Otomatik MA seçimi: Açık/Kapalı").

#### Trend İndikatörleri

- **EMA / SMA** (yukarıdaki strateji)
- **Ichimoku Cloud** (Tenkan 9, Kijun 26, Senkou A/B, Chikou)
- **Market Structure** (HH/HL/LH/LL otomatik tespit, fractal-based, ZigZag threshold ATR%1)
- **BOS / CHoCH** (Break of Structure / Change of Character — SMC)

#### Momentum İndikatörleri

- **RSI 14**
- **MACD (12, 26, 9)** — line, signal, histogram
- **Stochastic RSI (14, 14, 3, 3)**
- **Divergence Detector** — RSI ve MACD için, son 50 mumda swing high/low karşılaştırma

#### Volatilite İndikatörleri

- **ATR 14**
- **Bollinger Bands (20, 2)**
- **BB Width** (sıkışma tespiti)

#### Hacim İndikatörleri

- **OBV (On-Balance Volume)**
- **VWAP** (günlük reset)
- **Volume Profile** (POC, VAH, VAL — son 100 mum)

#### Fibonacci

- **Auto Fib Retracement** — son major swing high/low ZigZag bazlı, threshold ATR%1
- Seviyeler: 0.236, 0.382, 0.5, 0.618 (golden — vurgulu), 0.786
- **Fib Extension** — 1.272, 1.618 (golden), 2.618

#### Smart Money Concepts (Faz 2)

- **Order Blocks (OB)** — son güçlü hareketten önceki son zıt mum bloğu
  - Bullish OB: yükseliş öncesi son düşüş bloğu
  - Bearish OB: düşüş öncesi son yükseliş bloğu
- **Fair Value Gaps (FVG)** — fiyat boşluğu, 3-mum pattern
  - Mum 1 high < Mum 3 low → bullish FVG
  - Mum 1 low > Mum 3 high → bearish FVG
- **Liquidity Sweep** — önceki swing high/low'un kısa süreli kırılması ve geri dönüş
  - Buy-side liquidity sweep: high üstüne çıkış + altına dönüş = bearish sinyal
  - Sell-side liquidity sweep: low altına iniş + üstüne dönüş = bullish sinyal
- **Premium/Discount Zone** — son swing'in 0.5 üstü = premium, altı = discount

#### Futures-Spesifik

- **Funding Rate** (current + 8h avg + 24h avg)
- **OI değişim %** (1h, 4h, 24h)
- **Long/Short Ratio** (top traders + global)
- **Likidasyon yoğunluğu** (Phase 2 — Coinglass)
- **Liquidation map** (kaldıraç bazlı, Phase 2)

---

### 4.3 Macro Context Module

**Görev:** Lokal sembol analizinin **dışında** piyasa bağlamı sağlamak.

#### Takip Edilen Metrikler

**Kripto Pazar:**
- TOTAL — tüm kripto market cap
- TOTAL2 — TOTAL eksi BTC
- TOTAL3 — TOTAL eksi BTC eksi ETH
- BTC Dominance (BTC.D)
- ETH Dominance (ETH.D)
- OTHERS Dominance
- ETH/BTC oranı

**Geleneksel Finans:**
- DXY (Dolar Endeksi)
- S&P 500
- NASDAQ
- VIX (Korku endeksi)
- ABD 10Y Tahvil

**Sentiment:**
- Fear & Greed Index

**Kripto-spesifik (Phase 2):**
- Halving sayacı (BTC için)
- ETF Net Flow (BTC + ETH)

#### Market Regime Detector

Sistem otomatik olarak şu anki piyasa rejimini tespit eder:

| Rejim | Tetikleyici Koşullar | Etiket |
|-------|---------------------|--------|
| 🟢 ALT_BULL | BTC.D düşüyor (-%1+), TOTAL3 yükseliyor (+%2+), ETH/BTC ↑ | "Altcoin boğa rejimi" |
| 🟡 BTC_BULL | BTC ↑, BTC.D ↑, altlar geride | "BTC boğa, altlar geride" |
| 🔴 RISK_OFF | TOTAL ↓, BTC.D ↑, VIX yükseliyor | "Risk-off, altlar zayıf" |
| 🟢 ALT_SEASON_EARLY | ETH/BTC son 7g +%5+, TOTAL3 ATH yakın | "Erken alt sezonu işareti" |
| 🟡 MIXED | Karışık sinyaller | "Kararsız ortam" |

Rejim Dashboard'un üstünde küçük şerit halinde sürekli görünür.

#### Cross-Asset Rotation Tracker (Faz 2)

Sektörel para akışı tespiti.

**Sektör grupları:**
- **L1:** BTC, ETH, SOL, BNB, AVAX, ADA, DOT, NEAR, APT, SUI, SEI
- **L2:** ARB, OP, MATIC
- **DeFi:** UNI, AAVE, LDO, INJ
- **AI:** (eklenebilir — FET, AGIX, RNDR)
- **Meme:** DOGE, SHIB, PEPE, WIF, BONK
- **Other:** XRP, LINK, ATOM

Her sektör için 1d / 7d / 30d performans hesaplanır, "para nereye akıyor" sıralaması verilir.

**Görsel:** Dashboard'da heatmap tablosu, en güçlü sektör vurgulu.

---

### 4.4 Korelasyon Engine

**Görev:** Sembollerin BTC, TOTAL3, DXY ve birbirleriyle olan korelasyonunu gerçek zamanlı hesaplamak.

**Hesaplama:**
- Pearson korelasyon
- Veri: log returns
- Pencere: son 30 gün
- Granülarite: 4H mumları
- Cache: 1 saat

**Görsel:** Korelasyon Paneli (her sembol detay sayfasında).

```
KORELASYON DURUMU (son 30 gün)
─────────────────────────────
SOL ↔ BTC:    +0.91  (çok yüksek)
SOL ↔ ETH:    +0.84  (yüksek)
SOL ↔ TOTAL3: +0.78  (yüksek)
SOL ↔ DXY:    -0.42  (orta ters)
```

**Uyarı sistemi:** Açık pozisyonların ağırlıklı korelasyonu >0.75 ise → "gerçek riskin nominal'den 1.5x büyük" uyarısı.

---

### 4.5 Confluence Engine (2-Katmanlı)

#### Katman 1: Lokal Confluence

Her TF için **-100 ↔ +100** arası skor:

```
local_confluence = (
    trend_score      * 0.40 +
    momentum_score   * 0.20 +
    volume_score     * 0.15 +
    volatility_score * 0.10 +
    futures_score    * 0.15
)
```

**Trend Skoru bileşenleri:**
- MA dizilimi (50>100>200 bullish, ters bearish): ±30
- Fiyat MA200 üstünde mi: ±20
- Ichimoku Kumo pozisyonu: ±20
- Market structure (HH+HL veya LH+LL): ±30
- **1D bonus:** Hem EMA200 hem SMA200 üstünde mi: +10 / -10
- **SMC bonus (Faz 2):** BOS varsa: ±15

**Momentum Skoru bileşenleri:**
- RSI yön ve seviye: ±25
- MACD durumu: ±25-30
- StochRSI: ±15-25
- Divergence: ±20

**Volume Skoru bileşenleri:**
- OBV trend uyumu: ±25
- Anlık hacim/ortalama: ±25
- VPVR POC pozisyonu: ±20
- VWAP pozisyonu: ±30

**Volatility Skoru bileşenleri:**
- BB Width sıkışmadan çıkış: +30
- ATR normal mi: 0 / -20

**Futures Skoru bileşenleri:**
- Funding aşırı pozitif (>0.05%): -30 (long squeeze riski)
- Funding negatif: +20 (short squeeze potansiyeli)
- OI + fiyat uyumu: ±30
- L/S ratio aşırı: -15

#### Katman 2: Macro Modifier

Lokal skor üstüne **macro etki** uygulanır.

**BTC için:**
```python
macro_modifier = (
    btc_dominance_modifier(BTC.D_trend) +  # ↑ = bullish for BTC
    sp500_modifier(sp500_trend) +
    dxy_modifier(dxy_trend) +              # negatif korelasyon
    vix_modifier(vix_level)                # yüksek VIX = bearish
)
```

**Altcoin için:**
```python
macro_modifier = (
    btc_dominance_modifier(BTC.D_trend) * (-1) +  # ters
    total3_modifier(total3_trend) +
    eth_btc_modifier(eth_btc_ratio_trend) +
    dxy_modifier(dxy_trend) * 0.7 +        # daha az etki
    market_regime_modifier(current_regime)
)
```

**Modifier clamp'i:** -25 ile +25 arasında.

#### Final Confluence

```python
final_confluence = local_confluence + macro_modifier
final_confluence = clamp(final_confluence, -100, 100)
```

#### Multi-Timeframe Alignment

**6 timeframe** (15m, 1H, 4H, 1D, 1W, 1M) skorları üstüne alignment skoru:

```python
alignment_score = (
    final_confluence_15m * 0.05 +    # mikro timing
    final_confluence_1H  * 0.10 +
    final_confluence_4H  * 0.25 +    # ana karar TF
    final_confluence_1D  * 0.30 +    # macro yön
    final_confluence_1W  * 0.20 +
    final_confluence_1M  * 0.10
)
```

**TF Rolleri:**
| TF | Rol | Ağırlık |
|----|-----|---------|
| 15m | Timing + erken uyarı (giriş/çıkış mikro) | 0.05 |
| 1H | Kısa vade momentum | 0.10 |
| 4H | **Ana karar TF** | 0.25 |
| 1D | **Macro yön (trend bağlamı)** | 0.30 |
| 1W | Uzun vade context | 0.20 |
| 1M | Çok uzun vade (info amaçlı) | 0.10 |

**Önemli:** 15m **karar TF değildir**. Sadece **timing aracıdır**. Tek başına pozisyon açma sebebi olmamalı. Kullanım:
- 4H/1D bullish + 15m'de bullish reversal → mükemmel giriş
- 4H bullish + 15m parabolik yukarı → giriş için bekle (pullback)
- 4H bullish + 15m'de BOS down → erken uyarı, dikkatli

Label: "Strong" (>70 absolute), "Aligned" (>40), "Conflicted" (mixed signs).

---

### 4.6 Setup Quality Engine (A/B/C/D)

**Kriterler:**

| Kriter | Puan |
|--------|------|
| Multi-TF alignment "Strong" | +20 |
| 4H + 1D aynı yöne (kritik 2 TF) | +20 |
| Market structure temiz | +10 |
| R:R ≥ 3 | +10 |
| ATR normal | +10 |
| Funding ekstrem değil | +5 |
| Yakın major event yok | +5 |
| Macro modifier destekleyici (>0) | +10 |
| Korelasyon riski düşük | +5 |
| **Time-of-day uygun** (faz 1) | +5 |

| Toplam | Kalite |
|--------|--------|
| 90-100 | A |
| 70-89 | B |
| 50-69 | C |
| <50 | D |

**Macro etkisi:** Macro modifier >+15 → kalite +1 not yükselir. <-15 → -1 not düşer.

**Sentiment Conflict (Faz 2):** Funding ekstrem + L/S aşırı + sistem aynı yön → otomatik 1 not düşürme.

**Kullanım:** Sadece A ve B setup'ları öne çıkar. C uyarı ile, D filtrelenir.

---

### 4.6.1 Confidence Engine (MVP — KRİTİK)

**Görev:** Sistemin **kendi tahminlerine** ne kadar güvenmesi gerektiğini ölçmek.

**Sorun:** Setup quality A diyor → "%82 olasılık" çıkıyor. Ama bu rakam **kanıt seviyesi** olmadan **tehlikeli**. Çünkü sistem ilk kullanımda sadece **literatür bilgisine** dayanıyor, **gerçek performansa** değil.

**Çözüm:** Olasılık (probability) ve Confidence ayrı ayrı gösterilir.

```python
class ConfidenceEngine:
    
    def compute_confidence(self, setup_signature, user_id) → ConfidenceLevel
        """
        Bu setup tipinde kaç işlem yapılmış? Win rate ne?
        Trade journal'dan tarihsel veri al.
        """
        similar_trades = trade_journal.find_similar(
            setup_signature,
            user_id,
            lookback_days=180
        )
        
        n = len(similar_trades)
        
        if n < 5:
            return {
                "level": "VERY_LOW",
                "label": "⚠️ Kanıt yok, deneme aşaması",
                "trade_count": n,
                "advice": "İlk 5-10 işlem küçük pozisyonla deneyim toplayın"
            }
        elif n < 15:
            return {
                "level": "LOW",
                "label": "⚠️ Az veri, dikkatli",
                "trade_count": n,
                "advice": "Pozisyon boyutunu %50 küçültün"
            }
        elif n < 30:
            actual_win_rate = sum(t.is_win for t in similar_trades) / n
            return {
                "level": "MEDIUM",
                "label": "🟡 Orta kanıt",
                "trade_count": n,
                "actual_win_rate": actual_win_rate,
                "advice": "Normal pozisyon, izlemeye devam"
            }
        elif n < 60:
            return {
                "level": "HIGH",
                "label": "🟢 Güçlü kanıt",
                ...
            }
        else:
            return {
                "level": "VERY_HIGH",
                "label": "🟢 Çok güçlü kanıt",
                ...
            }
```

**Setup signature** (benzerlik tespiti):
- Setup quality (A/B/C)
- Macro regime (ALT_BULL, BTC_BULL, etc.)
- Time of day (US, EU, Asia session)
- Direction (long/short)
- Symbol category (L1, L2, etc.)

Aksiyon Özeti'nde **olasılık + confidence** birlikte gösterilir:

```
Olasılık (sistem hesabı): %82
Confidence: LOW ⚠️
   ↳ Bu setup tipinde 3 işlem var (gerçek win rate: 1/3)
   ↳ 30+ işlem için tam güven gerekir
   ↳ Bu setup'a girersen: pozisyon boyutunu %50 küçült öner.
```

**Önemli:** İlk haftalarda confidence sürekli LOW olacak. Bu **normal**. Trade Journal doldukça yükselir.

---

### 4.6.2 Counter-Trend Detector (MVP — KRİTİK)

**Görev:** Sistemin kendi sinyalini **sorgulaması**. Bazı "kusursuz" görünen setup'lar **tuzaktır**.

**Profesyonel sezgi:** Çok güzel görünen setup'larda **dikkat et**. Çünkü:
- Çoğu kişi aynı şeyi gördüyse → kalabalık → squeeze riski
- Parabolik hareket sonrası → exhaustion → reversal yakın
- Hacim azalan trend → momentum bitiyor

**Algoritma:**

```python
class CounterTrendDetector:
    
    def detect(self, market_data) → list[CounterTrendWarning]
        warnings = []
        
        # 1. Parabolik hareket (son 2h içinde aşırı yukarı/aşağı)
        price_change_2h = market_data.price_change_pct(hours=2)
        if abs(price_change_2h) > 3.0:
            warnings.append({
                "type": "parabolic_move",
                "severity": "high",
                "message": f"2h içinde %{price_change_2h:.1f} hareket — exhaustion riski",
                "advice": "Pullback bekle, FOMO'ya kapılma"
            })
        
        # 2. Funding ekstrem (>%0.08 absolute)
        if abs(market_data.funding_rate) > 0.0008:
            direction = "long aşırı" if market_data.funding_rate > 0 else "short aşırı"
            warnings.append({
                "type": "extreme_funding",
                "severity": "high",
                "message": f"Funding {market_data.funding_rate*100:.3f}% — {direction} kalabalık, squeeze riski",
                "advice": "Sistem aynı yöne sinyal veriyorsa karşıt yön de düşün"
            })
        
        # 3. L/S Ratio aşırı
        if market_data.ls_ratio > 3.0:
            warnings.append({
                "type": "extreme_ls",
                "severity": "high",
                "message": f"L/S {market_data.ls_ratio:.1f} — long aşırı sıkışmış",
                "advice": "Long pozisyon riski yüksek"
            })
        elif market_data.ls_ratio < 0.33:
            warnings.append({
                "type": "extreme_ls",
                "severity": "high",
                "message": f"L/S {market_data.ls_ratio:.1f} — short aşırı sıkışmış",
                "advice": "Short pozisyon riski yüksek"
            })
        
        # 4. Volume exhaustion (yükselişte hacim azalan)
        if (market_data.trend_direction == "up" and 
            market_data.volume_decreasing_count >= 3):
            warnings.append({
                "type": "volume_exhaustion",
                "severity": "medium",
                "message": "Yükselişte hacim son 3 mum azalıyor — momentum bitiyor",
                "advice": "Reversal yakın olabilir"
            })
        
        # 5. RSI extreme + price stalling
        if market_data.rsi_4h > 75 and abs(market_data.price_change_4h) < 0.5:
            warnings.append({
                "type": "rsi_divergence_setup",
                "severity": "medium",
                "message": "RSI aşırı alım + fiyat duruyor — bearish divergence kuruluyor",
                "advice": "4H/1D divergence kontrol et"
            })
        
        return warnings
```

**Aksiyon:**
- 0 warning → normal
- 1 warning → Aksiyon Özeti'nde göster, dikkat çek
- 2+ warning → setup quality 1 not düşürülür, "🚨 KARŞIT SİNYAL UYARISI" bölümü
- 3+ warning → "Bu setup'tan kaçınılması öneriliyor" mesajı

**Aksiyon Özeti'nde gösterim:**

```
🚨 KARŞIT SİNYAL UYARISI:
   Sistem long öneriyor AMA:
   ✗ Funding %0.082 (long aşırı kalabalık)
   ✗ L/S 3.4 (sıkışmış long pozisyonlar)
   ✗ 2h içinde %3.4 yükseliş (parabolik)
   
   PROFESYONEL YORUM:
   Bu pattern çoğu zaman "trap" olur. Reversal riski yüksek.
   
   ÖNERİ:
   - Bu setup'tan kaçın, sonrasını bekle, VEYA
   - Pozisyon boyutunu %50 küçült + sıkı stop
```

---

### 4.6.3 Trade Quality Filter (MVP — KRİTİK)

**Görev:** Confluence skoru yüksek olsa bile **vasat setup'ları ayıklar**.

**Sorun:** Bazı setup'lar matematik olarak iyi görünür ama gerçek hayatta **edge yoktur**:
- Range piyasada long açmak (TP'ye ulaşamaz)
- Düşük volatilitede pozisyon (funding kâr potansiyelini yer)
- S/R çok yakın (sıkışık piyasa, hareket alanı yok)

**Algoritma:**

```python
class TradeQualityFilter:
    
    def evaluate(self, market_data) → TradeQualityResult
        score = 0
        factors = []
        
        # 1. Volatilite yeterli (ATR > %0.8)
        atr_pct = market_data.atr / market_data.price * 100
        if atr_pct > 0.8:
            score += 1
            factors.append({
                "name": "volatility",
                "passed": True,
                "value": f"ATR %{atr_pct:.2f}",
                "note": "Volatilite yeterli, hareket bekleniyor"
            })
        else:
            factors.append({
                "name": "volatility",
                "passed": False,
                "value": f"ATR %{atr_pct:.2f}",
                "note": "Düşük volatilite, hareket yavaş olur, funding kâr yer"
            })
        
        # 2. Range vs trend (ADX > 20 = trend)
        if market_data.adx > 20:
            score += 1
            factors.append({
                "name": "trend_strength",
                "passed": True,
                "value": f"ADX {market_data.adx:.0f}",
                "note": "Trend piyasası, momentum devam edebilir"
            })
        else:
            factors.append({
                "name": "trend_strength",
                "passed": False,
                "value": f"ADX {market_data.adx:.0f}",
                "note": "Range piyasası, trend pozisyonu zayıf kazanır"
            })
        
        # 3. Macro netlik
        if self._is_macro_aligned(market_data):
            score += 1
            factors.append({
                "name": "macro_clarity",
                "passed": True,
                "note": "Macro sinyalleri uyumlu, net yön var"
            })
        else:
            factors.append({
                "name": "macro_clarity",
                "passed": False,
                "note": "Macro karışık (DXY/SP500 ters yönde), kafası karışık"
            })
        
        # 4. Hacim yükseliyor (son 4 mum)
        if market_data.volume_increasing_4candles:
            score += 1
            factors.append({
                "name": "volume_growth",
                "passed": True,
                "note": "Hacim son 4 mumda yükseliyor — momentum güçlü"
            })
        else:
            factors.append({
                "name": "volume_growth",
                "passed": False,
                "note": "Hacim yatay, momentum zayıf"
            })
        
        # 5. Major S/R arası >2 ATR mesafe
        nearest_sr_distance = market_data.nearest_major_sr_distance
        if nearest_sr_distance > 2 * market_data.atr:
            score += 1
            factors.append({
                "name": "clear_path",
                "passed": True,
                "value": f"{nearest_sr_distance/market_data.atr:.1f} ATR",
                "note": "Yakın S/R yok, hareket alanı temiz"
            })
        else:
            factors.append({
                "name": "clear_path",
                "passed": False,
                "value": f"{nearest_sr_distance/market_data.atr:.1f} ATR",
                "note": "S/R çok yakın, sıkışık ortam"
            })
        
        # Verdict
        if score >= 4:
            verdict = "EXCELLENT"
            quality_modifier = +1  # setup quality +1 not
        elif score >= 3:
            verdict = "GOOD"
            quality_modifier = 0
        elif score >= 2:
            verdict = "WEAK"
            quality_modifier = -1  # setup quality -1 not, küçük pozisyon
        else:
            verdict = "AVOID"
            quality_modifier = -2  # setup quality -2 not, açma önerme
        
    def _is_macro_aligned(self, market_data):
        """DXY ve SP500 uyumlu mu? (kripto için)"""
        # DXY düşüyor + SP500 yükseliyor = bullish kripto için
        # DXY yükseliyor + SP500 düşüyor = bearish kripto için
        # Ters yönde hareket = kafa karışık
        dxy_dir = market_data.dxy_change_24h
        spx_dir = market_data.sp500_change_24h
        return (dxy_dir < 0 and spx_dir > 0) or (dxy_dir > 0 and spx_dir < 0)
```

**Aksiyon:**
- AVOID (0-1 puan) → Aksiyon Özeti'nde "🚫 BU SETUP'TAN KAÇIN" gösterilir, pozisyon **önerilmez**
- WEAK (2 puan) → Setup quality 1 not düşer, küçük pozisyon önerisi
- GOOD (3 puan) → Normal aksiyon
- EXCELLENT (4-5 puan) → Setup quality 1 not yükselebilir

**Aksiyon Özeti'nde gösterim:**

```
TRADE QUALITY: GOOD (3/5)
   ✓ Volatilite yeterli (ATR %1.2)
   ✓ Trend piyasası (ADX 28)
   ✓ Macro net (DXY ↓ + SP500 ↑)
   ✗ Hacim yatay (son 4 mum)
   ✗ S/R yakın (1.4 ATR)
   
   Aksiyon: Normal pozisyon ama hacmin yükselmesini bekleyebilirsin.
```

---

### 4.7 Scenario Generator

Her sembol için **2 senaryo** üretilir: Long ve Short.

#### Hedef Tespit Algoritması

Tüm potansiyel seviyeler toplanır:
- Fib retracement (0.382, 0.5, 0.618)
- Fib extension (1.272, 1.618, 2.618)
- EMA / SMA seviyeleri (mevcut TF + üst TF)
- Volume Profile POC, VAH, VAL
- VWAP
- Önceki swing high/low (ZigZag)
- Likidasyon kümeleri (Phase 2)
- Order block seviyeleri (Phase 2)
- FVG seviyeleri (Phase 2)
- Order book büyük duvarlar (Phase 1, gerçek zamanlı)

Her seviye için **confluence count** hesaplanır (kaç indikatörün buluştuğu). Yöne göre filtrelenir, **en güçlü 3 confluence**'a sahip seviyeler hedef olarak seçilir.

**Golden seviyeler** (★) = 3+ confluence count.

#### Long Senaryosu

- **Entry:** mevcut fiyat ± 0.3 ATR (VWAP, EMA50, FVG, OB ile yakınlık skoruna göre ayarlanır)
- **Target 1, 2, 3:** yukarıdaki algoritmadan
- **Stop:** en yakın significant low - 0.5 ATR (market structure invalidation)
- **R:R:** (T1 - entry) / (entry - stop)
- **Olasılık:** final_confluence skorundan sigmoid normalize, macro_modifier ve quality bonus dahil

**Short senaryosu:** Aynı mantık tersi.

#### Position Allocation (Çıkış stratejisi)

Sistem hedeflere %dağılım önerir:
- TP1: pozisyonun %40'ı kapatılır
- TP2: %35'i
- TP3: %25'i
- Stop ulaşılmadan TP1 yakalanırsa → stop **break-even**'a çekilir (otomatik öneri)

---

### 4.8 Action Summary Module

**Görev:** Tüm yukarıdaki analizlerin **net çıktısını** kullanıcıya tek kart halinde sunmak.

**İçerik:**

1. **Tek cümle tavsiye:** Renk kodlu (🟢 LONG / 🔴 SHORT / ⚠️ DİKKAT / 🚫 NO-TRADE)
2. **Pozisyon detayları (kopyala-yapıştır hazır):**
   - Giriş aralığı
   - TP1, TP2, TP3 (her birinin pozisyon yüzdesi ile)
   - Stop loss
   - Pozisyon boyutu, kaldıraç, margin, gerçek risk USDT
   - R:R
3. **Destek/Direnç tablosu:**
   - Yukarı dirençler (en yakın 3-4)
   - Mevcut fiyat (vurgulu)
   - Aşağı destekler (en yakın 3-4)
   - Her seviyenin nedeni (Fib, EMA, swing, liquidasyon, vs.)
   - Golden seviyeler ★ ile işaretli
4. **Dikkat edilecekler:** Sistem fark ettiği uyarılar
5. **Görüş değişir eğer:** İnvalidasyon kriterleri
6. **Aksiyon butonları:**
   - 📋 Pozisyon Detaylarını Kopyala
   - 📒 Journal'a Ekle
   - 🔔 Alarm Kur
   - 🔍 Hesabı Göster (modal)

**"Hesabı Göster" Modal:** Her hedef ve stop için **arkadaki tüm indikatör confluence'ı** gösterilir:

```
TP1: 184.50 — neden bu seviye?
  ✓ Fib 0.382 retracement: 184.30
  ✓ EMA 50 günlük: 184.80
  ✓ Önceki swing high: 185.00
  ✓ Volume Profile POC üstü: 184.20
  → 4 confluence (güçlü hedef)
```

---

### 4.9 Risk Management Module

#### 4.9.1 Position Sizer (Volatility-Adjusted)

**Standart hesap:**
```python
risk_amount = balance * (risk_pct / 100)
stop_distance_pct = abs(entry - stop) / entry * 100
position_size = risk_amount / (stop_distance_pct / 100)
required_leverage = position_size / margin_available
```

**Volatility Adjustment (Faz 1):**
```python
volatility_factor = 1.0
if btc_24h_change_abs > 8.0:
    volatility_factor = 0.5    # kaotik → yarıya
elif btc_24h_change_abs > 5.0:
    volatility_factor = 0.7
elif atr_zscore > 2.0:
    volatility_factor = 0.7    # ATR aşırı yüksek

adjusted_risk_pct = base_risk_pct * volatility_factor
```

#### 4.9.2 Daily Risk Tracker

**Default limitler:**
- Risk per trade: %2
- Max kaldıraç: 10x
- Daily max trades: 5
- Daily max risk: %4
- Auto-pause after losses: 3

**Akıllı Risk Azaltma:**
- 2 üst üste kayıp → risk_pct otomatik %1.5 (1 saat)
- 3 üst üste kayıp → risk_pct otomatik %1.0 (4 saat)
- 24h içinde toplam %4 risk yenildi → "soft block"

**Tilt Koruması:**
- 1 saat içinde 2 stop → "soğuma süresi" önerisi
- Stop büyütme/averaging down uyarısı

#### 4.9.3 Funding Cost Calculator

```python
estimated_funding_cost = position_size * avg_funding_rate * (hours / 8)
```

Funding kâr potansiyelinin >%10'u ise → uyarı.

#### 4.9.4 Portfolio Manager (Faz 3)

**Toplam portföy riski:**
- Toplam açık risk = Σ (her pozisyonun risk_amount'u)
- Limit: bakiyenin %15'i max
- Korelasyon-ağırlıklı efektif risk

**Sektör Exposure:**
- L1, L2, DeFi, Meme dağılımı
- Aşırı yoğunluk uyarısı (örn. %60+ Meme)

**Yeni pozisyon kontrolü:**
- Açık pozisyonlarla korelasyon
- Sektörel yoğunluk
- Aynı yöne çoklu pozisyon ("4 alt long = 4x BTC long" uyarısı)

---

### 4.10 No-Trade Zone Detector

#### Macro Event Filter
- US CPI / Core CPI / PPI
- FOMC meeting + minutes + Powell konuşmaları
- US NFP, GDP, Retail Sales, ISM
- ECB rate decision
- Olay öncesi 4 saat ve sonrası 1 saat → "no-trade"

#### Time-of-Day Filter (Faz 1)
- **Asya seansı (00-08 UTC):** "low_volatility" rejim → küçük pozisyon önerisi
- **Avrupa seansı (07-16 UTC):** "normal"
- **ABD seansı (13-22 UTC):** "high_volatility" → tam pozisyon
- **Asya açılışı 30 dk öncesi:** "Asya yakın, dikkat"
- **Hafta sonları:** düşük likidite uyarısı

#### Teknik Filtreler
- Haftalık kapanışa <4 saat (Pazar UTC 22-Pazartesi 02)
- Aylık kapanış günü
- BTC volatilitesi 24h %8+ → "kaotik ortam"

#### Kişisel Filtreler
- Daily limit aşıldı
- Ardışık 3 stop son 24h
- Manuel pause

**Çıktı:** Dashboard üstünde kırmızı bant + Telegram bildirim.

---

### 4.11 Sentiment Conflict Detector

**Crowd Filter:**
- L/S ratio >2.5 + sistem long sinyali → "kalabalık aynı tarafta"
- Funding >0.05% + sistem long sinyali → "potansiyel long squeeze"
- Fear & Greed >75 + sistem long sinyali → "extreme greed bölgesi"

Bu durumlarda setup quality otomatik 1 not düşürülür.

---

### 4.12 Heatmap Dashboard

**Görev:** Tüm 25 sembolün anlık durumunu tek görselde göstermek.

**Sütunlar:**
- Sembol (logo + isim)
- Anlık fiyat
- 24h % değişim
- 1H confluence (renkli kutu)
- 4H confluence (renkli kutu)
- 1D confluence (renkli kutu)
- Setup kalitesi (A/B/C/D harfi)
- Sektör

**Renk kodu:** Final confluence skoruna göre yeşil-sarı-kırmızı gradient.

**Sıralama/Filtre:**
- Confluence skoruna göre (default)
- Setup kalitesine göre
- 24h % değişime göre
- Sektöre göre
- Filtre: "Sadece A+B"
- Filtre: "Sadece favoriler ⭐"

**Konum:** Sidebar nav'da ayrı sayfa "/heatmap".

---

### 4.13 Scanner

Watchlist'teki sembolleri belirli aralıklarla tarar.

**Tarama parametreleri:**
- Aralık: 15 dk (kullanıcı ayarlanabilir)
- Min kalite: A veya B
- Min alignment: Strong
- Max paralel: 3 (rate limit koruması)

**Çıktı:**
- Setup bulunca: dashboard'a düşer + Telegram bildirim
- Heatmap güncellenir

#### Volatility Alert (Faz 1)

Anlık fiyat hareket bildirimleri:
- 5dk içinde mutlak %2+ → "FLASH MOVE" bildirimi
- 1h içinde mutlak %4+ → "BIG MOVE"
- 4h içinde mutlak %7+ → "MAJOR MOVE"

Hareket geldiğinde sistem otomatik anlık analiz çalıştırır, sonucu bildirimle birlikte gönderir.

#### Quick Signal (Faz 1)

1H ve 4H'de A veya B kalite setup oluştuğunda anında Telegram bildirim:

```
🟢 LONG SİNYAL — BTCUSDT 1H | A kalite

LOKAL: +65 | MACRO: +18 | FINAL: +83
🟢 Rejim: ALT_BULL

Entry: 67,200-67,400
TP1: 67,800 (+%0.6) [%40]
TP2: 68,200 (+%1.2) [%35]
TP3: 68,900 (+%2.5) [%25]
SL: 66,800 (-%0.6) | R:R 1:4.2

Pozisyon (3000$/%2): 3,000 USDT @ 5x
Margin: 600 USDT | Risk: 60 USDT

DESTEKLER: 67,000★ / 66,800 / 66,400
DİRENÇLER: 67,800 / 68,200 / 68,900

⚠️ L/S kalabalık | CPI 18h sonra
✗ İPTAL: 4H < 66,800
Geçerlilik: 4 saat

[Detay] [Journal'a ekle] [Alarm kur]
```

---

### 4.14 Trade Journal & Performance

#### 4.14.1 İşlem Kayıt
Pozisyon açıldığında:
- Sembol, yön, giriş, stop, hedefler, kaldıraç, boyut
- Setup tipi (auto-detect)
- Sistem snapshot'ı (tüm analiz o anki)
- Kullanıcı notu

#### 4.14.2 Position Monitoring
Açık pozisyonlar için (Faz 3):
- Stop'a %X mesafe → uyarı
- Hedef yaklaşma → "kısmi al" önerisi
- Trend invalidasyonu → "stop yukarı çek (BE)" önerisi
- Funding maliyeti güncel
- Trailing stop önerisi (TP1 sonrası)

#### 4.14.3 Pozisyon Kapatma
Kapatınca gerçek çıxış fiyatı + nedeni girilir. Sistem otomatik:
- P/L hesaplar (gerçek + R-multiple)
- Setup tipini kategorize eder
- Pattern'e ekler

#### 4.14.4 Performance Stats

**Genel:**
- Win rate, profit factor, max DD, Sharpe, Sortino, Calmar

**Kategori bazlı:**
- TF'e göre
- Setup kalitesine göre (A/B/C)
- Sektöre göre
- Yöne göre
- Saat dilimine göre (Asya/EU/US seansları)
- **Setup tipine göre (Faz 3)** — örn. "EMA50+RSI bullish divergence"
- **Macro durumuna göre** — macro destekleyici vs çelişkili

**Pattern Detection:**
- Otomatik insight'lar (min 5 örneklem)
- Örnek: "StochRSI aşırı alımda short açtığında %72 kayıp (n=11)"

---

### 4.15 Wyckoff Schematics (Faz 4)

**Görev:** Akümülasyon ve distribüsyon evrelerini otomatik tespit.

**Phase tespiti:**
- **Phase A** (downtrend bitiyor): PS, SC, AR, ST seviyeleri
- **Phase B** (range içi sıkışma): yatay konsolidasyon, hacim azalması
- **Phase C** (Spring): son sahte kırılış + likidasyon avı + geri dönüş
- **Phase D** (yükseliş): LPS, SOS, BU
- **Phase E** (trend devam): markup başladı

**Algoritma:**
- Range tespit (Bollinger Band + ATR + ADX düşük)
- Volume divergence
- Spring tespiti (likidasyon sweep + bullish engulfing kombinasyonu)
- Climax volume detection

**Çıktı:** Dashboard'da "Wyckoff Phase" badge'i: "Phase B - Akümülasyon" veya "Phase D - Markup".

---

### 4.16 News Feed (Faz 2)

**Kaynak:** CryptoPanic API (ücretsiz tier).

**Filtreleme:**
- Sadece yüksek-impact haberler (votes >X)
- İzlenen sembollerle ilgili haberler
- Genel kripto haberleri (BTC, ETH, regülasyon, ETF, vb.)

**Görsel:** Dashboard sağ sidebar veya alt widget. Saat damgalı liste.

**Sentiment etiketleme:** Pozitif / Negatif / Nötr (CryptoPanic API'si veriyor).

**Önemli haber tespit:**
- "Bitcoin ETF onaylandı" gibi → kritik bildirim (Telegram)
- Filtre: 2+ saat geçmişten daha eski haberler düşük öncelikli

---

### 4.17 On-Chain Module (Faz 3)

Basit Etherscan/BSCScan ücretsiz API ile.

**Özellikler:**
- **Borsa netflow** (BTC, ETH, USDT) — büyük transferleri izle
- **Whale transfer alarmları** ($1M+ üstü)
- **Stablecoin rezervleri** trend (Tether, USDC)

**Sınırlamalar:** Glassnode/Nansen seviyesi değil. Ücretsiz alternatifin tavanı.

---

### 4.18 AI Assistant (Faz 4)

**Görev:** Anthropic Claude API ile entegre, kullanıcının sorularına bağlamsal cevap.

**Yetenekler:**
- Sembol analizi yorumlama: "BTC bugün niye düştü?"
- Pozisyon kararı yardımı: "SOL pozisyonumu kapatayım mı?"
- Eğitim: "Liquidity sweep nedir, nasıl tespit edilir?"
- Backtest yorumu: "Bu sonuçlara göre stratejimi nasıl iyileştireyim?"

**Bağlam:** Asistana her soru için sistem otomatik şunları context olarak verir:
- Mevcut sembolün analizi
- Açık pozisyonlar
- Son 24h önemli eventler
- Genel piyasa durumu

**Maliyet:** Aylık ~$5-20 kullanıma göre (Sonnet model).

---

### 4.19 Backtest Module (Faz 4)

Geçmiş 3 yıllık veride sistem sinyallerini simüle eder.

**Parametreler:**
- Sembol, başlangıç-bitiş tarihi
- Min kalite (A, A+B, A+B+C)
- Pozisyon boyutu (sabit % veya Kelly kriteri)
- Komisyon (default %0.04) ve funding dahil
- Slippage (default 0.05%)

**Sonuçlar:**
- Equity curve grafiği
- Tüm işlemler tablosu
- Win rate, profit factor, max DD, Sharpe, Sortino, Calmar
- Ay bazlı performans
- Setup tipi bazlı performans
- Macro rejim bazlı performans
- Karşılaştırma: "Sistem vs Buy & Hold"

---

### 4.20 Alert Manager + Smart Priority

**Alert Tipleri:**

**Kritik (Telegram + Sesli alarm yok, sadece push):**
- A-setup macro destekli
- No-trade zone başlangıç
- Açık pozisyonun stop'a %1 yakınlaşması

**Yüksek (Telegram bildirimi):**
- B-setup
- Volatility alert
- Major news (CryptoPanic high impact)
- Funding ekstrem (>0.1%)
- Açık pozisyonun TP1'e yakınlaşması

**Orta (in-app notification):**
- C-setup
- Eğitim insight'ları
- Sektör rotasyon değişimi

**Düşük (sessiz log):**
- Rutin durum güncellemeleri
- Setup expire bildirimleri

**Rate Limit:**
- Aynı sembol için aynı tip alert: 30 dk içinde 1 kez
- Toplam dakikada max 10 (spam koruması)

---

### 4.21 Manual Alert System (MVP — KRİTİK)

**Görev:** Kullanıcının elle fiyat alarmları yaratmasını sağlar. 3 aşamalı yaklaşma uyarıları + pozisyon yardımcısı.

**Tablo:** `user_alerts` (database-schema.md'de detay)

#### Alarm Tipleri

| Tip | Açıklama | Örnek |
|-----|----------|-------|
| `price_above` | Fiyat seviye üstüne çıkarsa | "BTC 70,000 üstüne çıkarsa" |
| `price_below` | Fiyat seviye altına inerse | "BTC 65,000 altına inerse" |
| `approach` | 3 aşamalı yaklaşma + ulaşma | "SOL 200'e yaklaşırsa" |

#### 3 Aşamalı Yaklaşma Uyarısı

`approach` tipinde sistem ATR'ye göre **otomatik mesafeler** hesaplar:

```python
class ApproachAlertEngine:
    
    def compute_distances(self, symbol, target_price) -> dict:
        atr_4h = get_atr(symbol, "4H")
        return {
            "approaching_distance": atr_4h * 1.0,    # 1 ATR uzakta
            "close_distance": atr_4h * 0.5,          # 0.5 ATR uzakta
            "target_distance": 0                      # ulaştı
        }
    
    def check_alert(self, alert, current_price) -> StageEvent | None:
        distance = abs(current_price - alert.target_price)
        distances = self.compute_distances(alert.symbol, alert.target_price)
        
        # 1. Aşama: Yaklaşıyor (1 ATR uzakta)
        if (distance <= distances["approaching_distance"] 
            and not alert.approaching_triggered):
            return StageEvent("approaching", priority="low")
        
        # 2. Aşama: Çok yakın (0.5 ATR uzakta)
        if (distance <= distances["close_distance"] 
            and not alert.close_triggered):
            return StageEvent("close", priority="medium")
        
        # 3. Aşama: Ulaştı (target geçildi/dokunuldu)
        if self._target_reached(alert, current_price) and not alert.target_triggered:
            return StageEvent("target_reached", priority="critical")
        
        return None
```

**Bildirim örnekleri:**

```
🟡 YAKLAŞIYOR — BTCUSDT
Hedef: 70,000 (1 ATR uzakta)
Şu an: 69,180 | Mesafe: 820 USDT
Trade hazırlığını yapabilirsin.
─────────────
[Sessiz bildirim, sadece banner]
```

```
🟠 ÇOK YAKIN — BTCUSDT
Hedef: 70,000 (0.5 ATR uzakta)
Şu an: 69,580 | Mesafe: 420 USDT
Aksiyona hazırlan!
─────────────
[Titreşimli bildirim]
```

```
🔴 HEDEFE ULAŞTI — BTCUSDT
Hedef: 70,000 ✓
Şu an: 70,012
Aksiyon zamanı!
─────────────
[Sesli + titreşimli bildirim — KRİTİK]
```

#### Pozisyon Yardımcısı (Otomatik Alarm Yaratma)

**Tetikleyici:** Aksiyon Özeti'nde "📒 Journal'a Ekle" butonuna basıldığında.

**Akış:**

```
1. Kullanıcı pozisyon detaylarını gözden geçirir
2. "Journal'a Ekle" butonu basılır
3. Modal açılır:
   "Bu pozisyon için otomatik alarmları yaratmak ister misin?"
   
   ✓ TP1 (3 aşamalı yaklaşma)
   ✓ TP2 (3 aşamalı yaklaşma)
   ✓ TP3 (3 aşamalı yaklaşma)
   ✓ SL (3 aşamalı yaklaşma)
   
   [Evet, hepsini yarat] [Sadece TP'ler] [Hayır]

4. Sistem 4 user_alerts kaydı yaratır:
   - related_trade_id = trade_id (otomatik bağlantı)
   - auto_generated = true
   - target_role = "tp1" / "tp2" / "tp3" / "sl"
   - alert_type = "approach"

5. Pozisyon kapatıldığında (trade.status = 'closed'),
   ilgili alarmlar otomatik 'cancelled' olur
```

**Otomatik alarm önceliği:**
- TP yaklaşma uyarıları: TP'ye 0.5 ATR yaklaşınca → kritik (sesli)
- SL yaklaşma uyarısı: SL'ye 0.5 ATR yaklaşınca → kritik (sesli)
- "Yaklaşıyor" aşamaları: orta öncelik (titreşim)

#### Worker (Arka Plan İşçisi)

```python
@celery_app.task
def check_user_alerts():
    """
    Her 30 saniyede çalışır.
    Tüm aktif user_alerts kayıtlarını döner ve fiyatlarla karşılaştırır.
    Tetiklenen alarmlar için bildirim atar.
    """
    active_alerts = db.query(user_alerts).filter(status="active").all()
    
    # Sembolleri grupla, tek API call'da tüm fiyatları çek
    symbols = set(a.symbol_id for a in active_alerts)
    current_prices = batch_get_prices(symbols)
    
    for alert in active_alerts:
        current_price = current_prices[alert.symbol_id]
        
        if alert.alert_type == "approach":
            event = approach_engine.check_alert(alert, current_price)
            if event:
                send_notification(alert, event)
                update_alert_stage(alert, event.stage)
        
        elif alert.alert_type == "price_above":
            if current_price >= alert.target_price:
                send_notification(alert, "target_reached")
                mark_alert_triggered(alert)
        
        elif alert.alert_type == "price_below":
            if current_price <= alert.target_price:
                send_notification(alert, "target_reached")
                mark_alert_triggered(alert)
```

#### Endpoint'ler

```
GET    /api/v1/user-alerts                      # Aktif alarmları listele
GET    /api/v1/user-alerts/{id}                 # Tek alarm detayı
POST   /api/v1/user-alerts                      # Yeni alarm yarat
PATCH  /api/v1/user-alerts/{id}                 # Düzenle
DELETE /api/v1/user-alerts/{id}                 # Sil
POST   /api/v1/user-alerts/from-trade/{trade_id}  # Pozisyondan otomatik 4 alarm
```

---

## 5. Frontend Yapısı

### 5.1 Sayfalar

**1. Dashboard** (`/`) — ana analiz ekranı (detay aşağıda)

**2. Heatmap** (`/heatmap`) — 25 sembolün matrix görünümü

**3. Scanner** (`/scanner`) — watchlist + aktif setup'lar

**4. Journal** (`/journal`) — açık + kapatılmış pozisyonlar + stats

**5. Risk** (`/risk`) — pozisyon hesaplayıcı + günlük durum

**6. Alerts** (`/alerts`) — manuel fiyat alarmları (yarat, düzenle, takip et) — **MVP**

**7. Backtest** (`/backtest`) — Faz 4

**8. AI Assistant** (`/ai`) — Faz 4, chat arayüzü

**9. Settings** (`/settings`) — tüm ayarlar

**10. Glossary** (`/glossary`) — terimler sözlüğü

### 5.2 Dashboard Layout

```
┌─────────────────────────────────────────────────┐
│ Top Bar (logo, nav, profile, bağlantı)          │
├─────────────────────────────────────────────────┤
│ Market Regime: 🟢 ALT_BULL | NTZ: yok           │
├──────┬──────────────────────────────────────────┤
│      │ Macro Context                            │
│ Sol  │ TOTAL ↑ | TOTAL3 ↑↑ | BTC.D ↓            │
│ Sym  │ DXY → | SP500 ↑ | VIX ↓                  │
│ List │                                          │
│ (25  ├──────────────────────────────────────────┤
│ adet)│ SOL/USDT • 4H                            │
│      │ Fiyat: 178.50  +%3.42                    │
│ BTC● │ LOKAL +65 | MACRO +18 | FINAL +83        │
│ ETH  │ Setup: A | Olasılık: %78                 │
│ SOL  ├──────────────────────────────────────────┤
│ BNB  │ Selection: TF + Modüller                 │
│ XRP  ├──────────────────────────────────────────┤
│ ...  │ ┌──────────────────────────────────────┐ │
│      │ │  GRAFİK                              │ │
│      │ │  EMA + VWAP + Fib + Hedef/Stop +     │ │
│      │ │  Likidasyon + Order Book + OB/FVG    │ │
│      │ └──────────────────────────────────────┘ │
│      │ [Trend] [Momentum] [Hacim]               │
│      │ [Volatilite] [Futures] [Macro]           │
│      │                                          │
│      │ Korelasyon paneli                        │
│      │                                          │
│      │ [Long Senaryosu] [Short Senaryosu]       │
│      │                                          │
│      │ ╔════════════════════════════════════╗  │
│      │ ║  AKSİYON ÖZETİ                     ║  │
│      │ ║  🟢 LONG ÖNERİLİYOR                ║  │
│      │ ║  Giriş / TP1/2/3 / SL              ║  │
│      │ ║  Pozisyon (kopyala-yapıştır hazır) ║  │
│      │ ║  Destek-Direnç tablosu             ║  │
│      │ ║  Dikkat / İptal kriterleri         ║  │
│      │ ║  [Kopyala] [Journal] [🔔] [Hesap]  ║  │
│      │ ╚════════════════════════════════════╝  │
│      │                                          │
│      │ News Feed widget (Faz 2)                 │
│      │ Wyckoff Phase badge (Faz 4)              │
└──────┴──────────────────────────────────────────┘
```

### 5.3 Sol Sembol Paneli

**Genişlik:** 200px (collapse edilebilir 60px'e)

**Her satır:**
- Sembol logo + adı
- Anlık fiyat (monospace)
- 24h % (renkli)
- Setup kalitesi badge (A/B/C)
- Confluence renk noktası
- Anlık hareket ikonu (⚡ — son 5dk büyük hareket)

**Üst kontroller:**
- Arama çubuğu
- Filtre butonları: Tümü / A+B / ⭐Favoriler
- Sıralama dropdown: Conf / 24h% / Hacim / Alfabetik

### 5.4 Tooltip + Sözlük Sistemi

**Tooltip:** Tüm metric isimlerinin yanında ⓘ ikonu. Hover ile küçük balon, kısa açıklama.

**Sözlük sayfası:** `/glossary` — tüm terimler kategorili, arama desteği:
- Skorlar (Confluence, Setup Quality, Multi-TF Alignment, R:R, Olasılık)
- İndikatörler (EMA, SMA, RSI, MACD, vs.)
- SMC (Order Block, FVG, Liquidity Sweep, BOS, CHoCH)
- Futures (Funding, OI, L/S, Liquidation)
- Macro (TOTAL, BTC.D, DXY, VIX)
- Risk (Position Size, Stop Loss, Trailing, BE)
- Wyckoff (Phase A-E, Spring, SOS, vs.)

### 5.5 Tasarım Sistemi

**Renkler (Binance dark):**
- Background: `#0B0E11`
- Surface: `#1E2329`
- Border: `#2B3139`
- Long/Bullish: `#0ECB81`
- Short/Bearish: `#F6465D`
- Nötr: `#848E9C`
- Accent: `#F0B90B`

**Tipografi:**
- UI: Inter
- Sayılar: JetBrains Mono (her zaman monospace)

**Spacing:** 4/8/12/16/24 px

**Bileşenler:** shadcn/ui base, custom theme override

---

## 6. Database Schema

Detaylı şema: `database-schema.md`

**Ana tablolar:**
- `users` — kullanıcı (single-user)
- `symbols` — 25 sembol + sektör
- `analyses` — her analiz snapshot'ı + macro modifier
- `confluence_scores` — TF bazlı skorlar (lokal + macro + final)
- `scenarios` — long/short senaryoları
- `setups` — Scanner çıktıları
- `trades` — kullanıcı pozisyonları (journal)
- `trade_snapshots` — pozisyon açıldığındaki sistem durumu
- `alerts` — alarm kayıtları + öncelik
- `user_settings` — risk limitleri, tercihler
- `watchlists` — kullanıcı listeleri
- `daily_risk_tracker` — günlük tilt + risk takibi
- `price_cache` — OHLCV + makro cache
- `correlations` — gerçek zamanlı korelasyon matrisi
- `macro_metrics` — TOTAL, dominans, DXY, vb. tarihsel
- `news_items` — CryptoPanic feed (Faz 2)
- `economic_events` — ekonomik takvim
- `backtest_runs` (Faz 4)
- `ai_conversations` (Faz 4)

---

## 7. API Endpoints

Detaylı: `api-endpoints.md`

**Ana gruplar:**
- `/api/v1/auth/*`
- `/api/v1/symbols/*`
- `/api/v1/analysis/*`
- `/api/v1/heatmap` — Faz 1
- `/api/v1/macro/*` — TOTAL, dominans, korelasyon
- `/api/v1/scanner/*`
- `/api/v1/trades/*`
- `/api/v1/risk/*`
- `/api/v1/portfolio/*` — Faz 3
- `/api/v1/alerts/*`
- `/api/v1/settings/*`
- `/api/v1/news/*` — Faz 2
- `/api/v1/onchain/*` — Faz 3
- `/api/v1/backtest/*` — Faz 4
- `/api/v1/ai/*` — Faz 4
- `/ws` — WebSocket

---

## 8. Faz Özeti

### 🎯 MVP Yaklaşımı

**Aktif Build Kapsamı = Adım 1-26 (yaklaşık 3 ay).**

Bu kapsam dışında kalan tüm özellikler **Future Roadmap**'tedir ve **6 ay canlı kullanım sonrası gerçek ihtiyaca göre** seçici eklenecek. **"Hepsini build et" yaklaşımı reddedildi.** "Iterate and validate" felsefesi benimsendi.

---

### Faz 1 — Temel (4-5 hafta) — MVP DAHIL ✅
**Adım 1-22**
- Backend + Frontend iskelet
- Data ingestion (Binance, CoinGecko, yfinance)
- Indicator engine + dinamik MA + tüm klasik indikatörler
- Confluence + Macro modifier + Setup quality
- Senaryo üretici + Aksiyon Özeti
- Risk yönetimi (volatility-adjusted)
- No-trade zone (macro events + time-of-day)
- Heatmap dashboard + Order book heatmap
- Smart bildirim önceliklendirmesi
- Volatility Alert + Quick Signal
- Sol sembol paneli + tooltip + sözlük

### Faz 2 — Profesyonel İlk Yarısı (2-3 hafta) — MVP DAHIL ✅
**Adım 23-26**
- Coinglass entegrasyonu (likidasyon heatmap)
- Smart Money Concepts (OB, FVG, Liquidity Sweep, BOS/CHoCH)
- News feed (CryptoPanic)
- Cross-Asset Rotation Tracker

### 🛑 ADIM 26 SONUNDA DUR — 3 AY CANLI KULLAN

---

### 🔮 Future Roadmap — 6 Ay Sonra Değerlendir

⚠️ Aşağıdaki özellikler **şimdi build edilmiyor**. Her birinin kendi **validasyon kriteri** var (build-steps.md'de detay). 6 ay canlı kullanım sonrası **gerçekten ihtiyaç duyduğun** olanları seçici ekle.

#### Future — Faz 2 Kalanı (Adım 27-30)
- Halving sayacı + ETF flow
- Otomatik ekonomik takvim (forexfactory scrape)
- Scanner + Watchlist tam yönetimi
- Telegram bot ileri komutlar (/btc, /scan, vb.)

#### Future — Faz 3 (Adım 31-37)
- **Trade Journal Full + Pattern Detection** — büyük ihtimal eklenir, 50+ işlem sonra
- Position Monitoring + Management (trailing, partial close, BE)
- Portfolio Manager (toplam risk, sektör exposure)
- Korelasyon + Sentiment Conflict tam
- Win Rate by Setup Type detaylı
- Basit On-Chain (Etherscan free)

#### Future — Faz 4 (Adım 38-43)
- Backtest motoru (3 yıl) — **dikkat: overfitting riski**
- **Wyckoff Schematics — OPSİYONEL** (manuel daha doğru olabilir)
- AI Assistant (Claude API) — gerçekten lazım mı?
- Mobil PWA optimizasyon
- Setup type detaylı stats
- Final polish + Production deploy

---

### Build Süreci

| Faz | Süre | Durum |
|-----|------|-------|
| MVP Build (Adım 1-26) | ~3 ay | **Aktif geliştirme** |
| Canlı kullanım + paper trade | 3 ay | Gerçek veri toplama |
| Future Roadmap değerlendirme | 1 hafta | Hangi özellikler gerçekten lazım? |
| Future Roadmap selektif geliştirme | 1-3 ay | Sadece validate edilmiş özellikler |

**Toplam tahmini timeline:** 8-12 ay (full sistem). MVP hazır olduğunda **kullanıma alınır**, sonrası kademeli.

---

## 9. Performans Hedefleri

- Anlık analiz cevabı: <2 saniye
- Heatmap güncelleme: <3 saniye (25 sembol)
- Tarama 1 sembol: <500 ms
- Dashboard ilk yükleme: <1 saniye
- Real-time fiyat WebSocket gecikme: <500 ms
- Database query p95: <100 ms

---

## 10. Bilinmesi Gerekenler

### Sistem ne yapamaz
- Geleceği tahmin edemez. Olasılık ve senaryo verir.
- "Kesin kâr" garantisi yok.
- Black swan olaylarını öngöremez.
- Backtest %75 win rate canlıda %50-58'e düşer (bu normaldir).

### Kullanıcı sorumlulukları
- Risk limitlerini ciddiye al
- C ve D setup'larına büyük pozisyon açma
- No-trade zone'larda durmayı bil
- Stop'ları manuel olarak borsada koy (sistem otomatik koymuyor)
- İlk 3 ay küçük pozisyon (öğrenme dönemi)
- Sistem ile çalışmak için sistemin sözünü dinlemeli

### Kritik kabuller
- Binance public API rate limit (1200/dk) yeterli olacak
- Coinglass Hobbyist (30/dk) yeterli, caching ile
- Tek kullanıcı (kişisel)
- Tek borsa (Binance)
