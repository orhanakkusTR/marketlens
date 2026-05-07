# MarketLens

**Profesyonel kişisel kripto + emtia ticaret karar destek terminali.**

> Bu bir sinyal botu **değildir**. MarketLens, kullanıcıya yapılandırılmış, kaliteli analiz ve aksiyon önerisi sunan bir karar destek sistemidir. Tetiği kullanıcı çeker.

---

## Genel Bakış

MarketLens, 25 sembol (BTC, ETH, SOL, BNB, ve major + Tier 1-4 altcoinler + GOLD) üzerinde multi-timeframe (1H, 4H, 1D, 1W, 1M) teknik + macro + on-chain + Smart Money Concepts analiz yapar.

Her analiz şu çıktıları üretir:
- **2-katmanlı Confluence skoru** (lokal + macro)
- **A/B/C/D Setup kalitesi**
- **Long ve Short senaryoları** (giriş, hedefler, stop)
- **Risk yönetimi planı** (pozisyon boyutu, kaldıraç, margin)
- **Aksiyon Özeti** (kopyala-yapıştır pozisyon detayları + destek/direnç tablosu + uyarılar)

---

## Temel Özellikler

### Faz 1 — Temel
- 5 timeframe paralel analiz
- 25+ teknik indikatör (EMA/SMA dinamik, Ichimoku, RSI, MACD, BB, OBV, VWAP, Volume Profile, Auto Fibonacci)
- Macro entegrasyonu (TOTAL, dominanslar, DXY, S&P, NASDAQ, VIX)
- Korelasyon Engine (gerçek zamanlı, 30 gün, 4H bazında)
- Akıllı risk yönetimi (volatility-adjusted, no-trade zone, tilt koruması)
- Heatmap Dashboard (25 sembol tek görünümde)
- Volatility Alert + Quick Signal
- Sol Sembol Paneli (filtre/sıralama)
- Tooltip + Sözlük + "Hesabı Göster" modal

### Faz 2 — Profesyonel
- Coinglass entegrasyonu (likidasyon heatmap, ETF flow)
- Smart Money Concepts (Order Block, FVG, Liquidity Sweep, BOS/CHoCH)
- News Feed (CryptoPanic)
- Cross-Asset Rotation Tracker (sektörel para akışı)
- Halving Sayacı
- Otomatik Ekonomik Takvim
- Telegram Bot (smart priority)

### Faz 3 — Akıllı
- Trade Journal (otomatik snapshot)
- Position Management (trailing, partial close, BE)
- Portfolio Manager (toplam risk, sektör exposure, korelasyon kontrolü)
- Pattern Detection (otomatik öğrenme)
- Sentiment Conflict Detector
- Win Rate by Setup Type
- Basit On-Chain (Etherscan free)

### Faz 4 — İleri
- Backtest Motoru (3 yıl)
- Wyckoff Schematics (otomatik phase tespit)
- AI Asistan (Claude API)
- Mobile PWA
- Strategy Insights

---

## Stack

| Katman | Teknoloji |
|--------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, asyncpg, Alembic, pandas-ta, Celery + Redis |
| Frontend | React 18, Vite, TypeScript, Tailwind, shadcn/ui, lightweight-charts, TanStack Query, Zustand |
| Database | PostgreSQL 16 |
| Cache/Queue | Redis 7 |
| Infra | Docker Compose, Nginx, DigitalOcean, Cloudflare |
| Observability | structlog, Sentry |

---

## Hızlı Başlangıç

### Gereksinimler

- **Mac veya Linux** (Windows için WSL2)
- **Docker Desktop** ([indir](https://www.docker.com/products/docker-desktop/))
- **Node.js 18+** (sadece local frontend dev için, opsiyonel)
- **Git**
- **VS Code + Claude Code** (geliştirme için önerilen)

### Kurulum

```bash
# 1. Repoyu klonla
git clone https://github.com/orhanakkusTR/marketlens.git
cd marketlens

# 2. Environment dosyasını kopyala
cp .env.example .env

# 3. .env içinde kritik değerleri doldur:
#    - JWT_SECRET_KEY (openssl rand -hex 32)
#    - ENCRYPTION_KEY (openssl rand -hex 32)
#    - POSTGRES_PASSWORD
#    - TELEGRAM_BOT_TOKEN (Faz 1 sonu için)

# 4. Servisleri başlat
docker compose up -d

# 5. Database migrate
docker compose exec backend alembic upgrade head

# 6. Sembolleri seed et
docker compose exec backend python scripts/seed.py

# 7. Admin kullanıcı oluştur
docker compose exec backend python scripts/create_user.py
```

### Erişim

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs
- **PostgreSQL:** localhost:5432
- **Redis:** localhost:6379

### Logları İzle

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

### Servisleri Durdur

```bash
docker compose down
```

---

## Geliştirme Workflow

MarketLens, **Claude Code** ile entegre çalışacak şekilde tasarlandı. Geliştirme süreci:

1. `docs/build-steps.md` dosyasından sıradaki adımı bul
2. Adımın prompt'unu Claude Code'a ver
3. Plan onayla → kod yazılsın
4. Docker üstünde test et
5. Çalıştığında commit, sonraki adıma geç

Detaylı rehber: [`docs/getting-started.md`](docs/getting-started.md)

---

## Dokümantasyon

| Dosya | İçerik |
|-------|--------|
| [`CLAUDE.md`](CLAUDE.md) | Claude Code persistent memory |
| [`docs/architecture.md`](docs/architecture.md) | Tam mimari ve modüller |
| [`docs/build-steps.md`](docs/build-steps.md) | 43 adımlık build prompt sequence |
| [`docs/database-schema.md`](docs/database-schema.md) | PostgreSQL şema detayı |
| [`docs/api-endpoints.md`](docs/api-endpoints.md) | REST + WebSocket spec |
| [`docs/getting-started.md`](docs/getting-started.md) | VS Code + Claude Code workflow |

---

## Proje Felsefesi

1. **Sinyal değil, karar desteği.** Sistem "%X olasılıkla şu" der; tetiği sen çekersin.
2. **Multi-katman analiz.** Lokal + Macro + Korelasyon ayrı ayrı.
3. **Kalite > Miktar.** A/B önerilir, C uyarılı, D filtre.
4. **Risk yönetimi öne çıkartılır.** Sermaye koruma her şeyden önce.
5. **Şeffaflık + Eğitim.** Her hesap "neden böyle" cevabı verir.
6. **Aksiyon Özeti.** Her sayfanın altında net karar planı.
7. **Geri besleme.** Trade journal + pattern detection ile sistem öğrenir.

---

## Tahmini Maliyet (Aylık)

| Faz | Maliyet | Açıklama |
|-----|---------|----------|
| Faz 1 | $0 | Tüm kaynaklar ücretsiz |
| Faz 2 | $29 | Coinglass Hobbyist |
| Faz 3 | $29 | Aynı, Etherscan ücretsiz |
| Faz 4 | $35-45 | + Claude API (~$10 tipik) |
| Production deploy | +$15 | DigitalOcean droplet |
| **Toplam (full)** | **~$50-60** | |

---

## Lisans

Kişisel kullanım amaçlıdır. Dağıtım veya yeniden satış yasak.

---

## Sorumluluk Reddi

MarketLens **finansal tavsiye vermez**. Ürettiği analiz ve öneriler eğitim ve karar destek amaçlıdır. Kripto kaldıraçlı işlemler **yüksek risklidir**, sermayenizin tamamını kaybedebilirsiniz. Tüm işlem kararlarınızdan ve bunların sonuçlarından **siz sorumlusunuz**.

Backtest sonuçları geçmiş performansı gösterir, gelecek performansın garantisi değildir. Backtest'te %75 win rate gösteren strateji canlı ortamda %50-58'e düşebilir (slippage, funding, psikoloji nedeniyle).

İlk 3 ay küçük pozisyonlarla öğrenme dönemi olarak kullanın. Sistemi tanıdıkça risk seviyesini kademeli artırabilirsiniz.

---

## Geliştirici

orhanakkusTR ([GitHub](https://github.com/orhanakkusTR))

Claude (Anthropic) ile birlikte tasarlandı ve geliştirildi.
