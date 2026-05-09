# MarketLens — Claude Code Persistent Context (v2)

> Bu dosya VS Code'da Claude Code başlatıldığında otomatik okunur.

---

## Proje Tanımı

**MarketLens**, kişisel kullanım için profesyonel bir kripto + emtia karar destek terminalidir. 27 sembol (26 kripto + GOLD: BTC, ETH, SOL, BNB ve majors + Tier 1-4 altcoinler) üzerinde multi-timeframe (15m, 1H, 4H, 1D, 1W, 1M) teknik + macro + on-chain + SMC analiz yapar, **2-katmanlı confluence** (lokal + macro) skoru üretir, **A/B/C/D setup kalitesi** belirler, long/short senaryoları üretir, akıllı **risk yönetimi** yapar ve her analizde **Aksiyon Özeti** verir.

**Kullanıcı:** Johnson (kullanıcı adı: orhanakkusTR) — Türk, kaldıraçlı işlem yapıyor (Binance Futures), Mac kullanıcısı, daha önce FastAPI + React + PostgreSQL projeler yaptı.

---

## Kritik Felsefe (her zaman uy)

1. **Sinyal botu DEĞİL, karar destek sistemi.**
2. **2-katmanlı analiz:** Lokal indikatörler + Macro bağlam (TOTAL/dominans/korelasyon).
3. **Risk yönetimi = analiz kadar önemli.**
4. **Kalite > Miktar.** A/B önerilir, C uyarılı, D filtre.
5. **Şeffaflık + Eğitim.** Tooltip, sözlük, "Hesabı Göster" modalı, AI asistan.
6. **Aksiyon Özeti** her sayfanın altında — kopyala-yapıştır pozisyon planı.
7. **Geri besleme.** Trade journal + pattern detection.

## KESİN KURAL — Manuel İşlem (HARD RULE)

**Sistem ASLA borsaya otomatik emir göndermez.**

- ❌ Otomatik pozisyon açma kodu yazılmaz
- ❌ Otomatik stop-loss/TP yerleştirme kodu yazılmaz
- ❌ Otomatik pozisyon kapatma kodu yazılmaz
- ❌ Binance trading API kullanımı yasak (sadece okuma izni var)
- ❌ Webhook ile başka bir bot tetiklemek yok
- ✅ Sistem analiz verir, kullanıcı **kendi elleriyle** Binance'a girer ve pozisyon açar
- ✅ Trade Journal pozisyon **kaydını tutar** (manuel girilir veya kopyala-yapıştır ile eklenir)
- ✅ Position Management modülü **uyarı verir**, otomatik aksiyon almaz ("Stop'a yaklaşıyor" diye Telegram mesajı atar, ama stop'u kendisi taşımaz)

Bu kural değişmez. İleriki sürümlerde otomatik trading istense bile **bu projede yok**, ayrı bir proje olur.

Eğer bir özellik eklerken bu kuralı bozma riski varsa **ekleme yapılmadan kullanıcıya bildir.**

---

## Stack (kesin)

### Backend
- Python 3.12, FastAPI (async)
- SQLAlchemy 2 + asyncpg + Alembic
- pandas-ta (TA-Lib KULLANMA)
- python-binance, yfinance, httpx
- pydantic v2
- Celery + Redis
- python-telegram-bot
- anthropic (Faz 4)
- structlog, slowapi, tenacity, pybreaker

### Frontend
- React 18 + Vite + TypeScript (strict)
- TailwindCSS + shadcn/ui
- lightweight-charts v4
- recharts
- TanStack Query v5, Zustand
- react-hook-form + zod
- lucide-react, Sonner

### Infrastructure
- PostgreSQL 16, Redis 7
- Docker + docker-compose
- Nginx, DigitalOcean, Cloudflare
- Sentry

---

## Veri Kaynakları

| Kaynak | Veri | Maliyet | Faz |
|--------|------|---------|-----|
| Binance Spot | OHLCV | Ücretsiz | 1 |
| Binance Futures | Funding, OI, L/S, likidasyonlar | Ücretsiz | 1 |
| Binance Depth | Order book | Ücretsiz | 1 |
| CoinGecko | TOTAL, TOTAL2, TOTAL3, BTC.D, ETH.D | Ücretsiz | 1 |
| yfinance | GOLD, DXY, S&P, NASDAQ, VIX, US10Y | Ücretsiz | 1 |
| Alternative.me | Fear & Greed | Ücretsiz | 1 |
| forexfactory | Ekonomik takvim (scrape) | Ücretsiz | 1 |
| Coinglass | Likidasyon heatmap, ETF flow | $29/ay | 2 |
| CryptoPanic | Haberler | Ücretsiz tier | 2 |
| Etherscan | On-chain transferler | Ücretsiz | 3 |
| Anthropic | AI Asistan | ~$10/ay | 4 |

---

## Sembol Listesi (27: 26 kripto + GOLD)

**Tier 1 — Major:** BTC, ETH, SOL, BNB, XRP, AVAX, ADA, DOGE, POL, DOT
**Tier 2 — Popüler:** LINK, ATOM, NEAR, APT, ARB, OP
**Tier 3 — Trend/Meme:** SHIB, PEPE, WIF, BONK
**Tier 4 — DeFi/sektör:** UNI, AAVE, LDO, INJ, SUI, SEI
**Emtia:** GOLD (XAUUSD)

Sektör etiketleri:
- L1: BTC, ETH, SOL, BNB, AVAX, ADA, DOT, NEAR, APT, SUI, SEI
- L2: ARB, OP, POL
- DeFi: UNI, AAVE, LDO, INJ
- Meme: DOGE, SHIB, PEPE, WIF, BONK
- Other: XRP, LINK, ATOM
- Commodity: GOLD

---

## Tasarım Sistemi (Frontend)

### Renkler (Tailwind config)
```js
binance: {
  bg:      '#0B0E11',
  surface: '#1E2329',
  border:  '#2B3139',
  long:    '#0ECB81',
  short:   '#F6465D',
  neutral: '#848E9C',
  accent:  '#F0B90B',
  text: {
    primary:   '#EAECEF',
    secondary: '#B7BDC6',
    muted:     '#848E9C',
  }
}
```

### Tipografi
- UI: Inter
- Sayılar: JetBrains Mono (her zaman)

### Bileşen Kuralları
- Border-radius: rounded-md (kart için rounded-lg)
- Sol vurgu border 2px (yön rengi)
- Sentence case her zaman
- Font-weight: 400 normal, 500 bold (daha ağır kullanma)
- Hiçbir gradyan, drop-shadow, neon
- Letter-spacing 1px sadece uppercase küçük başlıklarda

### Sayı Formatı
- Fiyat: 2-8 ondalık (sembole göre)
- Yüzde: 2 ondalık (`+1.88%`)
- USDT: `$67,432.50`
- Büyük: `$612M`, `$1.2B`

---

## Backend Mimari Kuralları

### Klasör Yapısı (kesin)
```
backend/app/
├── core/         # config, security, logging, exceptions, middleware
├── api/v1/       # endpoint'ler
├── services/     # iş mantığı
│   ├── indicators/   # trend, momentum, volume, volatility, fibonacci, smc
│   ├── confluence/   # local, macro, alignment
│   ├── risk/         # position_sizer, daily_tracker, no_trade_zone
│   └── analysis/     # orchestrator, scenario, action_summary
├── data/         # external API clients
├── models/       # SQLAlchemy
├── schemas/      # Pydantic
├── workers/      # Celery tasks
├── db/           # session, base
└── main.py
```

### Async İlk Tercih
- DB işlemleri async (asyncpg + AsyncSession)
- External API async (httpx)
- Senkron sadece CPU-bound (indikatör hesaplama)

### Cache Stratejisi
- Redis cache decorator
- Tag-based invalidation (Phase 3+)
- Cache key: `marketlens:{namespace}:{key}`
- TTL'ler architecture.md'de

### Hata Yönetimi
- Custom exception sınıfları (`MarketLensError` base)
- Global exception handler standart format
- Circuit breaker external API'ler için
- Exponential backoff retry, max 3

### Loglama
- structlog + JSON output
- Her record: timestamp, level, request_id, user_id, message
- Sensitive data maskeli

---

## Frontend Mimari Kuralları

### Klasör Yapısı
```
frontend/src/
├── components/
│   ├── ui/             # shadcn/ui base
│   ├── dashboard/
│   │   ├── cards/      # modül kartları
│   │   ├── ActionSummary.tsx  # KRİTİK
│   │   ├── ScenarioCard.tsx
│   │   └── ...
│   ├── chart/          # lightweight-charts
│   ├── heatmap/
│   ├── sidebar/        # sol sembol paneli
│   └── shared/
├── pages/              # her route
├── hooks/
├── lib/
├── stores/             # Zustand
├── types/
└── App.tsx
```

### State Management
- Server state: TanStack Query
- Client state: Zustand
- Form: react-hook-form
- URL: react-router-dom

### TypeScript
- strict: true
- any yasak
- Backend pydantic'ten otomatik tipler (Phase 3+: openapi-typescript)

---

## Confluence Skoru (KRİTİK Formüller)

### 2-Katmanlı Yapı

**Katman 1 — Lokal:**
```python
local_confluence = (
    trend_score      * 0.40 +
    momentum_score   * 0.20 +
    volume_score     * 0.15 +
    volatility_score * 0.10 +
    futures_score    * 0.15
)
```

**Katman 2 — Macro Modifier:**
- BTC için: BTC.D ↑ pozitif, DXY ↓ pozitif, VIX ↓ pozitif
- Altcoin için: BTC.D ↓ pozitif, TOTAL3 ↑ pozitif, ETH/BTC ↑ pozitif
- Clamp: -25 ↔ +25

**Final:**
```python
final_confluence = clamp(local_confluence + macro_modifier, -100, 100)
```

### Multi-TF Alignment
```python
alignment = (
    final_15m * 0.05 +    # mikro timing
    final_1H  * 0.10 +
    final_4H  * 0.25 +    # ana karar TF
    final_1D  * 0.30 +    # macro yön
    final_1W  * 0.20 +
    final_1M  * 0.10
)
```

**Önemli:** 15dk **karar TF değildir**, sadece **timing aracı**. Bu yüzden ağırlığı düşük (0.05). 4H + 1D ana karar verme TF'leridir.

Label: Strong (>70), Aligned (>40), Conflicted (mixed signs).

---

## Setup Quality (A/B/C/D)

| Toplam | Kalite | Aksiyon |
|--------|--------|---------|
| 90-100 | A | Büyük pozisyon ok |
| 70-89 | B | Normal pozisyon |
| 50-69 | C | Küçük pozisyon, dikkat |
| <50 | D | Açma |

**Macro etkisi:** Modifier > +15 → kalite +1 not. < -15 → -1 not.

---

## 🆕 Confidence Seviyesi (KRİTİK MVP)

Olasılık (probability) ≠ Confidence. Bunlar **iki farklı şey**:

- **Olasılık:** Sistemin matematiksel hesabı ("%82 olasılıkla başarılı")
- **Confidence:** Bu rakamın **kanıt seviyesi** ("daha 3 işlem yapıldı, kanıt zayıf")

```python
def compute_confidence(setup_type, similar_trades_count) → ConfidenceLevel
    if similar_trades_count < 5:
        return "VERY_LOW"      # ⚠️ "Kanıt yok, deneme aşaması"
    elif similar_trades_count < 15:
        return "LOW"            # ⚠️ "Az veri, dikkatli"
    elif similar_trades_count < 30:
        return "MEDIUM"         # 🟡 "Orta kanıt"
    elif similar_trades_count < 60:
        return "HIGH"           # 🟢 "Güçlü kanıt"
    else:
        return "VERY_HIGH"      # 🟢 "Çok güçlü kanıt"
```

**Aksiyon Özeti'nde göster:**
```
Olasılık (sistem): %82
Confidence: LOW ⚠️
   ↳ Bu setup tipinde 3 işlem var
   ↳ 30+ işlem için tam güven gerekir
```

Trade Journal doldukça **confidence yükselir**. Bu sayede kullanıcı sistemin **kendine güvenini ölçer**, körü körüne inanmaz.

---

## 🆕 Counter-Trend Detector (KRİTİK MVP)

Sistem kendi sinyalini **sorgulamalı**. Bazı "kusursuz" görünen setup'lar aslında **tuzak** olabilir.

```python
def detect_counter_trend_signals(symbol, market_data) → list[Warning]
    warnings = []
    
    # Parabolik hareket (exhaustion)
    if abs(price_change_2h) > 3.0:
        warnings.append({
            "type": "parabolic_move",
            "message": "2h içinde %3+ hareket — exhaustion riski"
        })
    
    # Funding ekstrem
    if abs(funding_rate) > 0.0008:  # 0.08%
        warnings.append({
            "type": "extreme_funding",
            "message": f"Funding {funding_rate*100:.2f}% — squeeze riski"
        })
    
    # L/S aşırı
    if ls_ratio > 3.0 or ls_ratio < 0.33:
        warnings.append({
            "type": "extreme_ls",
            "message": f"L/S {ls_ratio:.1f} — aşırı kalabalık"
        })
    
    # Hacim yükselişte azalma (bearish/bullish exhaustion)
    if trend_up and volume_decreasing_3candles:
        warnings.append({
            "type": "volume_exhaustion",
            "message": "Yükselişte hacim azalıyor — exhaustion"
        })
    
    return warnings
```

**Eğer 2+ counter-trend warning varsa:**
- Setup quality 1 not düşürülür
- Aksiyon Özeti'nde "🚨 KARŞIT SİNYAL UYARISI" bölümü gösterilir
- Pozisyon boyutu otomatik %50 küçültme önerisi verilir

---

## 🆕 Trade Quality Filter (KRİTİK MVP)

Confluence skoru yüksek olsa bile bazı setup'lar **vasattır**. Bu filtre vasatları ayıklar.

```python
def compute_trade_quality(market_data) → TradeQualityResult
    score = 0
    factors = []
    
    # 1. Volatilite yeterli (ATR > %0.8)
    if atr_pct > 0.8:
        score += 1
        factors.append(("volatility_ok", True))
    else:
        factors.append(("volatility_low", False, "Düşük volatilite, hareket yavaş olur"))
    
    # 2. Range vs trend (ADX > 20 = trend)
    if adx > 20:
        score += 1
        factors.append(("trending_market", True))
    else:
        factors.append(("range_market", False, "ADX düşük, range piyasa"))
    
    # 3. Macro netlik (DXY/SP500 uyumlu)
    if macro_signals_aligned():
        score += 1
        factors.append(("macro_clear", True))
    else:
        factors.append(("macro_mixed", False, "Macro karışık sinyaller veriyor"))
    
    # 4. Hacim yükseliyor
    if volume_increasing_4candles:
        score += 1
        factors.append(("volume_growing", True))
    else:
        factors.append(("volume_flat", False, "Hacim yatay"))
    
    # 5. Major S/R arası >2 ATR mesafe
    if distance_to_major_sr > 2 * atr:
        score += 1
        factors.append(("clear_path", True))
    else:
        factors.append(("crowded_levels", False, "S/R çok yakın, sıkışık"))
    
    # Skor değerlendirmesi
    if score >= 4:
        verdict = "EXCELLENT"  # ✅
    elif score >= 3:
        verdict = "GOOD"        # 🟢
    elif score >= 2:
        verdict = "WEAK"        # ⚠️
    else:
        verdict = "AVOID"       # 🚫
    
    return {score, verdict, factors}
```

**Aksiyon:**
- AVOID (0-1) → Aksiyon Özeti "🚫 BU SETUP'TAN KAÇIN" gösterir, pozisyon önermez
- WEAK (2) → Setup quality 1 not düşürülür, küçük pozisyon önerisi
- GOOD (3) → Normal aksiyon
- EXCELLENT (4-5) → Setup quality 1 not yükseltilebilir

---

## Risk Yönetimi (KRİTİK)

### Default Limitler
- Risk per trade: %2
- Max kaldıraç: 10x
- Daily max trades: 5
- Daily max risk: %4
- Auto-pause: 3 ardışık kayıp
- Default bakiye: 3,000 USDT

### Akıllı Risk Azaltma
- 2 ardışık kayıp → %1.5 (1 saat)
- 3 ardışık kayıp → %1.0 (4 saat)

### Volatility-Adjusted Position Sizing (Faz 1)
```python
volatility_factor = 1.0
if btc_24h_change_abs > 8: volatility_factor = 0.5
elif btc_24h_change_abs > 5: volatility_factor = 0.7
elif atr_zscore > 2: volatility_factor = 0.7
adjusted_risk = base_risk * volatility_factor
```

### Position Sizing Formülü
```python
risk_amount = balance * (adjusted_risk / 100)
stop_distance_pct = abs(entry - stop) / entry * 100
position_size = risk_amount / (stop_distance_pct / 100)
required_leverage = position_size / margin_available
```

---

## No-Trade Zone Triggerlar

1. Macro events (CPI, FOMC, NFP) ± 4 saat
2. Weekly close (Pazar 22:00 - Pazartesi 02:00 UTC)
3. High volatility (BTC 24h %8+)
4. **Time-of-day filter:** Asya seansı (00-08 UTC) düşük volatilite
5. Daily limit aşıldı
6. 3 ardışık stop son 24h
7. Manuel pause

---

## Aksiyon Özeti (KRİTİK Component)

Her dashboard'un altında. İçerik:
1. Tek cümle tavsiye (renk kodlu)
2. Pozisyon detayları (kopyala-yapıştır hazır)
   - Giriş aralığı
   - TP1/TP2/TP3 + pozisyon yüzdesi
   - SL
   - Pozisyon, kaldıraç, margin, risk USDT, R:R
3. Destek/Direnç tablosu (sıralı, golden ★ işaretli)
4. Dikkat edilecekler (uyarılar)
5. Görüş değişir eğer (invalidasyon)
6. Aksiyon butonları: 📋 Kopyala / 📒 Journal / 🔔 Alarm / 🔍 Hesabı Göster

---

## Smart Money Concepts (Faz 2)

- **Order Blocks (OB):** son güçlü hareketten önceki son zıt mum
- **Fair Value Gaps (FVG):** 3-mum boşluk pattern
- **Liquidity Sweep:** swing high/low kısa kırılış + dönüş
- **BOS / CHoCH:** market structure değişimi
- **Premium/Discount:** son swing'in 0.5 üstü/altı

---

## Indikatör Listesi (Tam)

### Trend
- **15m, 1H, 4H** için: EMA 50, 100, 200
- **1D** için: EMA 50, 100 + SMA 200
- **1W, 1M** için: SMA 50, 100, 200
- Ichimoku Cloud
- Market Structure (HH/HL/LH/LL)
- BOS / CHoCH (Faz 2)

### Momentum
- RSI 14
- MACD (12, 26, 9)
- Stochastic RSI (14, 14, 3, 3)
- Divergence (RSI + MACD)

### Volatilite
- ATR 14
- Bollinger Bands (20, 2)
- BB Width

### Hacim
- OBV
- VWAP (günlük reset)
- Volume Profile (POC, VAH, VAL — son 100 mum)

### Fibonacci
- Auto Fib Retracement (ZigZag)
- Fib Extension

### SMC (Faz 2)
- Order Blocks
- Fair Value Gaps
- Liquidity Sweep
- Premium/Discount Zone

### Futures
- Funding (current + 8h + 24h avg)
- OI değişim (1h, 4h, 24h)
- L/S Ratio
- Likidasyon yoğunluğu (Faz 2)

---

## Dashboard Sayfa Yapısı

```
1. Top Bar (logo, nav, profile)
2. Market Regime Banner (🟢 ALT_BULL gibi)
3. Sol Sembol Paneli (200px, collapse mümkün)
   - Arama, filtre (Tümü/A+B/⭐), sıralama
4. Macro Context kartı (üstte)
   - TOTAL, TOTAL2, TOTAL3, BTC.D, ETH.D, DXY, SP500, VIX
5. Sembol Header (fiyat + lokal/macro/final conf + setup quality)
6. Selection Bar (TF + modüller)
7. GRAFİK
   - Mum + EMA/SMA + VWAP + Bollinger
   - Fib seviyeleri + Hedef/Stop
   - Likidasyon bantları (Faz 2)
   - Order book heatmap (Faz 1)
   - OB / FVG (Faz 2)
   - RSI/MACD alt panelleri
8. Modül Kartları (seçilenler)
9. Korelasyon Paneli
10. Senaryo Kartları (Long/Short yan yana)
11. AKSİYON ÖZETİ ← son ve en kritik
12. News Feed Widget (Faz 2)
13. Wyckoff Phase Badge (Faz 4)
```

---

## Sayfalar (Routing)

- `/` Dashboard
- `/heatmap` Heatmap (27 sembol matrix) — Faz 1
- `/scanner` Scanner + Watchlist
- `/journal` Trade Journal
- `/risk` Risk hesaplayıcı
- `/alerts` Manuel Alarm Sistemi — **MVP**
- `/backtest` (Faz 4)
- `/ai` AI Assistant (Faz 4)
- `/settings` Ayarlar
- `/glossary` Terimler sözlüğü

---

## 🆕 Manual Alert System (MVP)

Kullanıcı manuel fiyat alarmları kurar. Sistem `alerts` tablosundan ayrı, `user_alerts` tablosunda saklanır.

**Alarm tipleri:**
- `price_above` — fiyat üstüne çıkarsa
- `price_below` — fiyat altına inerse
- `approach` — 3 aşamalı yaklaşma (yaklaşıyor → çok yakın → ulaştı)

**3 aşamalı yaklaşma uyarısı:**
- **Aşama 1 (Yaklaşıyor):** 1 ATR (4H) uzakta → 🟡 düşük öncelik (sessiz)
- **Aşama 2 (Çok yakın):** 0.5 ATR uzakta → 🟠 orta öncelik (titreşim)
- **Aşama 3 (Ulaştı):** target geçildi → 🔴 kritik (sesli + titreşim)

**Pozisyon yardımcısı:**
Aksiyon Özeti'nde "📒 Journal'a Ekle" basıldığında:
- Sistem sorar: "Bu pozisyon için 4 otomatik alarm yaratılsın mı?"
- TP1, TP2, TP3, SL için 3 aşamalı approach alarmları yaratılır
- Pozisyon kapatılınca alarmlar otomatik iptal olur

**Worker:** Celery beat, her 30 saniyede `check_user_alerts` çalıştırır.

**Endpoint'ler:**
- `GET /api/v1/user-alerts` — liste
- `POST /api/v1/user-alerts` — yarat
- `PATCH /api/v1/user-alerts/{id}` — düzenle
- `DELETE /api/v1/user-alerts/{id}` — sil
- `POST /api/v1/user-alerts/from-trade/{trade_id}` — pozisyondan otomatik 4 alarm

---

## Bildirim Önceliklendirmesi

| Öncelik | Telegram | Push | Sound | Örnek |
|---------|----------|------|-------|-------|
| Kritik | ✓ | ✓ | ✓ | A-setup macro destekli, NTZ başlangıç, **manuel alarm hedefe ulaştı** |
| Yüksek | ✓ | ✓ | - | B-setup, vol alert, major news, **manuel alarm "çok yakın" aşaması** |
| Orta | - | ✓ | - | C-setup, eğitim insight, **manuel alarm "yaklaşıyor" aşaması** |
| Düşük | - | - | - | Rutin log |

Rate limit: aynı sembol+tip 30 dk'da 1, toplam dakikada 10.

---

## Geliştirme Workflow

### Yeni adım
1. `docs/build-steps.md`'den prompt al
2. Claude Code'a ver
3. Plan onayla → kod yazılsın
4. `docker compose up -d` ile test
5. Hata varsa Claude'a anlat
6. Çalıştığında commit
7. Sonraki adım

### Database değişikliği
1. Model güncelle
2. `alembic revision --autogenerate -m "..."`
3. Migration dosyasını incele
4. `alembic upgrade head`
5. Test

### Yeni indikatör
1. `services/indicators/`'a ekle
2. Unit test (synthetic OHLCV)
3. `indicator_engine.py`'da expose
4. Confluence formülüne entegre
5. Frontend kart'a ekle
6. Sözlük sayfasına terim ekle

### Yeni endpoint
1. Schema (request/response)
2. Service (business logic)
3. Endpoint
4. `docs/api-endpoints.md`'ye dokumentasyon
5. Frontend API hook
6. Component'te kullan

---

## Lokal Geliştirme

### İlk Kurulum
```bash
git clone https://github.com/orhanakkusTR/marketlens
cd marketlens
cp .env.example .env
# .env'i editle
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed.py
docker compose exec backend python scripts/create_user.py
```

### Çalıştırma
```bash
docker compose up
# Backend: http://localhost:8000
# Backend docs: http://localhost:8000/docs
# Frontend: http://localhost:5173
```

### Test
```bash
docker compose exec backend pytest
docker compose exec frontend npm test
```

---

## Bilinen Tuzaklar

1. **TA-Lib KURMAYIN** — pandas-ta yeterli.
2. **yfinance rate limiti** — saatte ~2000, cache şart.
3. **Binance WebSocket reconnect** — 24h sonra disconnect, otomatik reconnect şart.
4. **Coinglass CORS** — backend proxy zorunlu.
5. **lightweight-charts v4 TS types** — bazı method'lar `as any` kabul.
6. **PostgreSQL UUID** — `CREATE EXTENSION IF NOT EXISTS pgcrypto`.
7. **Celery on Mac** — Docker üstünde sorun yok.
8. **pandas-ta NaN** — ilk N mum NaN, dropna() veya fillna().
9. **Mum kapanış UTC** — Binance 4H mumları UTC 00:00, 04:00... başlar.
10. **forexfactory scrape** — robots.txt'ye saygı, haftalık cron yeterli.
11. **CoinGecko rate limit** — dakikada 30, cache 5 dk.
12. **macOS Docker performance** — VirtioFS açık olmalı (Docker Desktop Settings → General).

---

## Phase Ilerleme — MVP Yaklaşımı

### 🎯 Aktif Build Kapsamı (3 ay, MVP)

- [ ] Phase 1 — Temel (Adım 1-22)
- [ ] Phase 2 — Profesyonel İlk Yarı (Adım 23-26)

### 🛑 ADIM 26 SONUNDA DUR

Bu noktada sistem tam fonksiyonel:
- Multi-TF Confluence + Setup Quality + Macro
- SMC (OB, FVG, Liquidity Sweep, BOS/CHoCH)
- News Feed + Sektörel Rotasyon
- Aksiyon Özeti + Heatmap + Risk yönetimi

**Şimdi ne yapılır:** 3 ay canlı kullanım + paper trade + küçük gerçek pozisyon. Trade Journal'ı manuel doldur. Notlar tut.

### 🔮 Future Roadmap (6 ay sonra değerlendir)

- [ ] Adım 27-30 (Future Faz 2 kalanı)
- [ ] Adım 31-37 (Future Faz 3) — pattern detection büyük ihtimal eklenir
- [ ] Adım 38-43 (Future Faz 4) — bazıları muhtemelen hiç eklenmez

**6 ay sonra her özellik için sor:** "Bu özelliği gerçekten kullanır mıydım? Verilerim ne diyor?" Her birinin **validasyon kriteri** build-steps.md'de yazılı.

### 🚦 Geliştirme Kuralı

1. Adım 1'den başla, **sırayla** git
2. Her adım sonu **test et**, çalışınca commit
3. **Adım 26'ya geldiğinde DUR**
4. 3 ay canlı kullanım sonrası tekrar değerlendir
5. **Hepsini build etme** felsefesi — sadece kanıtlı ihtiyaçları ekle

---

## Kullanıcı Tercihleri

- **Türkçe iletişim**
- Kısa ve net cevaplar
- Yapılandırılmış adım adım yaklaşım
- CLAUDE.md persistent memory mantığı
- Mac kullanıcısı (Windows komutları gerekmez)
- GitHub: orhanakkusTR/marketlens
- **MVP felsefesi:** önce çalışan ve sade, sonra **kanıtlı** ihtiyaçlara göre genişletme

---

## Son Söz

Bu proje **kalite > hız** projesidir. Kullanıcı "süre uzasın sorun değil, güzel ve kullanışlı bir sistem olsun" dedi. Buna uy. Trade off varsa "doğru" tarafına yatır.

**Sistem çoklu katmanlı:** Lokal indikatörler + Macro bağlam + Korelasyon + Risk yönetimi + SMC + Aksiyon Özeti. Her katman bağımsız çalışır ve test edilebilir olmalı.

**Aksiyon Özeti** sistemin yüzü. Her şey buna varır. Buna en çok özen göster.

**MVP cut-off Adım 26.** Bu sınırı aşmak için **kullanıcının açık onayı** gerekir. Aksi halde "şu özelliği de ekleyelim" denmesin — Future Roadmap'e referans verilsin.
