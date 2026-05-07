# MarketLens — Geliştirme Rehberi

Bu dokümantasyon, MarketLens'i VS Code + Claude Code ile **adım adım nasıl geliştireceğinizi** anlatır. Build sürecinin tamamı 43 adımdan oluşur ve her adımı ayrı bir Claude Code session'ında geliştireceksiniz.

---

## 1. Ön Hazırlık

### 1.1 Gerekli Araçlar

**1. Mac terminal kontrolü:**
```bash
# Git yüklü mü?
git --version

# Node.js (frontend için, opsiyonel ama önerilir)
node --version  # 18+ olmalı
```

Yoksa: https://brew.sh ile Homebrew kur, sonra:
```bash
brew install git node
```

**2. Docker Desktop:**
- İndir: https://www.docker.com/products/docker-desktop/
- Kur, başlat
- Settings → General → "Use Virtualization framework" ✓
- Settings → General → "Use VirtioFS" ✓ (Mac performansı için kritik)
- Settings → Resources → CPU 4+, Memory 8GB+ önerilir

Test:
```bash
docker --version
docker compose version
docker run hello-world
```

**3. VS Code:**
- İndir: https://code.visualstudio.com
- Kur, başlat

**4. Claude Code:**

```bash
# Claude Code CLI'ı yükle
npm install -g @anthropic-ai/claude-code

# Versiyon kontrol
claude --version

# Login (browser açacak)
claude login
```

VS Code extension olarak da kurabilirsin (Marketplace'te "Claude Code").

### 1.2 GitHub Repo

Projeyi GitHub'a klonla:

```bash
cd ~/Documents     # veya istediğin yere
git clone https://github.com/orhanakkusTR/marketlens.git
cd marketlens
```

VS Code'da aç:
```bash
code .
```

---

## 2. İlk Setup

### 2.1 Environment Dosyası

```bash
cp .env.example .env
```

VS Code'da `.env` dosyasını aç, en azından şunları doldur:

```bash
# Random secret üret:
openssl rand -hex 32
# Çıktıyı JWT_SECRET_KEY'e yapıştır

openssl rand -hex 32
# Çıktıyı ENCRYPTION_KEY'e yapıştır

# Postgres şifresi (kendiniz belirleyin)
POSTGRES_PASSWORD=guvenli_bir_sifre_buraya
```

Diğer API key'leri sonradan ekleyeceğiz (faz geçişlerinde).

### 2.2 Telegram Bot (Faz 1 sonunda)

Faz 1'in sonuna doğru lazım olacak ama şimdiden kuralım:

1. Telegram'da `@BotFather`'a git
2. `/newbot` yaz
3. Bot adı ver (örn. "MarketLens Bot")
4. Username ver (örn. "marketlens_yourname_bot")
5. Aldığın token'ı `.env`'de `TELEGRAM_BOT_TOKEN`'a yapıştır
6. Bot'u kendi hesabınla başlat (bot username'i Telegram'da ara, /start gönder)
7. Bu URL'ye git (TOKEN'ı kendi token'ınla değiştir):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
8. JSON içinde `"chat": {"id": 12345678}` görürsün, bu senin chat_id'in
9. Settings → Profile'da kayıt edeceksin (sonra)

---

## 3. Claude Code Workflow

### 3.1 İlk Çalıştırma — Tanışma Promptu

VS Code'da terminal aç (`Ctrl + `` veya `View → Terminal`).

```bash
claude
```

Claude Code başladığında ilk olarak ona projeyi tanıt:

**İlk prompt'u yapıştır:**

```
Bu proje MarketLens. Profesyonel kişisel kripto + emtia ticaret karar destek terminali.

Lütfen şu sırayla bu dosyaları oku:
1. CLAUDE.md (proje persistent memory)
2. docs/architecture.md (tam mimari)
3. docs/build-steps.md (43 adımlık build sequence)
4. docs/database-schema.md (DB şema)
5. docs/api-endpoints.md (API spec)
6. .env.example
7. README.md

Tüm bunları okuduktan sonra:
- Projeyi anladığını bana 3-4 cümleyle özetle
- Hangi adımdayız (Adım 1 - henüz başlamadık)
- Bir sonraki adımı bana göster

Bu projede:
- Türkçe konuşacağız
- Adım adım gideceğiz, bir adım bitmeden sonrakine geçmeyeceğiz
- Her adım için önce planı sunacaksın, ben onaylayınca kod yazacaksın
- Kod yazdıktan sonra test etmem için talimat vereceksin
- CLAUDE.md kuralları her zaman geçerli

Hazırsan başlayalım.
```

Claude bunu okur, özetler, sıradaki adımı gösterir.

### 3.2 Her Adımın Standart Akışı

**1. Adım promptu kopyala-yapıştır:**

`docs/build-steps.md`'den sıradaki adımın prompt'unu Claude Code'a yapıştır.

**2. Plan onayla:**

Claude önce plan sunar:
- Hangi dosyalar oluşturulacak
- Hangi dosyalar değişecek
- Test stratejisi

Plan iyiyse "devam et" de. Değilse düzelt.

**3. Kod yazılması:**

Claude dosyaları oluşturur/günceller.

**4. Manuel test:**

Claude sana test komutları verir:
```bash
# Örnek
docker compose up -d
docker compose exec backend pytest tests/test_xyz.py
curl http://localhost:8000/api/v1/something
```

Test çalıştır.

**5. Hata varsa:**

Hatayı Claude'a göster, çözer.

**6. Çalışıyorsa commit:**

```bash
git add .
git commit -m "Adım X: özet"
git push
```

**7. Sonraki adım:**

Yeni session açabilirsin (önerilen) veya aynı session'da devam edebilirsin.

### 3.3 Her Yeni Session İçin

Yeni Claude Code session'ında, kısa bağlam ver:

```
Selam Claude. MarketLens projesindeyiz.

CLAUDE.md ve docs/build-steps.md'yi tekrar oku. 
Şu an Adım [X]'deyiz, [bu adımın özeti].
[Önceki adımda yaptıklarımızı kısaca yaz, opsiyonel]

Hazırsan Adım [X]'e başlayalım.
```

CLAUDE.md zaten otomatik okunur ama bağlam için iyi olur.

---

## 4. Docker Yönetimi

### 4.1 Temel Komutlar

```bash
# Servisleri başlat (arka planda)
docker compose up -d

# Logları izle
docker compose logs -f
docker compose logs -f backend     # sadece backend

# Servisleri durdur
docker compose down

# Servisleri durdur + volume'leri sil (DB sıfırla)
docker compose down -v

# Belirli servisi yeniden başlat
docker compose restart backend

# Container'a shell'le bağlan
docker compose exec backend bash
docker compose exec postgres psql -U marketlens -d marketlens
```

### 4.2 Database İşlemleri

```bash
# Migration oluştur (model değişiklikten sonra)
docker compose exec backend alembic revision --autogenerate -m "açıklama"

# Migration uygula
docker compose exec backend alembic upgrade head

# Migration geri al
docker compose exec backend alembic downgrade -1

# Geçmişi gör
docker compose exec backend alembic history
```

### 4.3 Sorun Giderme

**"Docker Desktop is not running" hatası:**
- Docker Desktop uygulamasını başlat (whale icon menubar'da görünmeli)

**Port çakışması (8000, 5173, 5432, 6379):**
```bash
# Portu kim kullanıyor?
lsof -i :8000

# Process'i kapat
kill -9 [PID]
```

**Container build hataları:**
```bash
# Cache'siz rebuild
docker compose build --no-cache

# Tek servisi rebuild
docker compose build --no-cache backend
docker compose up -d
```

**Yavaş Mac performansı:**
- Docker Desktop → Settings → General → "Use VirtioFS" ✓
- Resources → CPU 4+, Memory 8GB+

---

## 5. Git Workflow

### 5.1 Branch Stratejisi

```bash
# Her adım için yeni branch
git checkout -b feature/adim-1-iskelet

# Değişiklikleri commit et
git add .
git commit -m "Adım 1: proje iskeleti ve docker setup"

# Push
git push -u origin feature/adim-1-iskelet

# main'e merge (test sonrası)
git checkout main
git merge feature/adim-1-iskelet
git push
```

İsterseniz tek branch'te de gidebilirsiniz (kişisel proje):

```bash
# Direkt main'de çalış
git add .
git commit -m "Adım 1: proje iskeleti"
git push
```

### 5.2 Faydalı Komutlar

```bash
# Durum
git status

# Geçmiş
git log --oneline --graph --all

# Son commit'i geri al (henüz push edilmediyse)
git reset --soft HEAD~1

# Bir dosyayı geri al
git checkout -- dosya.py
```

---

## 6. VS Code İpuçları

### 6.1 Önerilen Eklentiler

VS Code'da Extensions paneline (Cmd+Shift+X) git:

- **Python** (Microsoft)
- **Pylance** (Microsoft)
- **Ruff** (Astral - Python linter)
- **Tailwind CSS IntelliSense**
- **ESLint**
- **Prettier**
- **Docker** (Microsoft)
- **GitLens**
- **Error Lens**
- **TypeScript Importer**

### 6.2 Faydalı Kısayollar (Mac)

| Kısayol | İşlev |
|---------|-------|
| `Cmd + P` | Hızlı dosya bul |
| `Cmd + Shift + P` | Komut paleti |
| `Cmd + Shift + F` | Tüm projede ara |
| `Cmd + B` | Sidebar göster/gizle |
| `Cmd + J` | Terminal göster/gizle |
| `Cmd + Shift + E` | Explorer'a git |
| `Cmd + K, Z` | Zen mode |
| `Cmd + /` | Yorum satırı |

### 6.3 Multi-cursor

- `Option + tıklama` — birden fazla imleç
- `Cmd + D` — sıradaki eşleşmeyi seç
- `Cmd + Shift + L` — tüm eşleşmeleri seç

---

## 7. Test Stratejisi

### 7.1 Backend Testler

```bash
# Tüm testleri çalıştır
docker compose exec backend pytest

# Belirli dosya
docker compose exec backend pytest tests/test_indicators.py

# Belirli test
docker compose exec backend pytest tests/test_indicators.py::test_rsi

# Verbose
docker compose exec backend pytest -v

# Coverage
docker compose exec backend pytest --cov=app
```

### 7.2 Frontend Testler

```bash
# Vitest çalıştır
docker compose exec frontend npm test

# Watch mode
docker compose exec frontend npm test -- --watch
```

### 7.3 Manuel API Testi

```bash
# Backend swagger UI
open http://localhost:8000/docs

# Curl
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin"}'
```

VS Code'da **REST Client** eklentisi de kurarak `.http` dosyaları oluşturabilirsiniz.

---

## 8. Faz Geçişleri

### 8.1 Faz 1 → Faz 2

Adım 22 bitince:

1. Çalışan sistemi kullan, gerçek pozisyon açma henüz!
2. Sembol tarama sonuçlarını gözle, mantıklı mı?
3. 2-3 hafta paper trading (kâğıt üzerinde takip)
4. Hatalar/eksikler not et
5. Faz 2 öncesi:
   - Coinglass hesap aç ($29/ay)
   - CryptoPanic kayıt ol (ücretsiz)
   - `.env`'de COINGLASS_API_KEY ve CRYPTOPANIC_API_KEY doldur
6. Adım 23'e başla

### 8.2 Faz 2 → Faz 3

Adım 30 bitince:

1. Telegram alertler aktif, Quick Signal'leri 1-2 hafta gözle
2. Faz 3 = Trade Journal'i ciddi kullanmak demek
3. Etherscan API key al (ücretsiz)
4. Adım 31'e başla

### 8.3 Faz 3 → Faz 4

Adım 37 bitince:

1. En az 30-50 gerçek işlem yap, journal dolu olsun
2. Pattern detection insight'larına bak
3. Anthropic Console hesap aç, API key oluştur
4. `.env`'de ANTHROPIC_API_KEY doldur
5. Adım 38'e başla (Backtest)

### 8.4 Production Deploy

Adım 43 sonu:

1. DigitalOcean droplet oluştur ($12/ay yeterli)
2. Domain al (Cloudflare üstünden)
3. SSL setup
4. Production .env (debug=false, gerçek secret'lar)
5. Backup automation kur
6. Sentry account aç, DSN ekle
7. Uptime Kuma kur (monitoring)

---

## 9. Sık Karşılaşılan Sorunlar

### 9.1 "ModuleNotFoundError: No module named 'pandas_ta'"

```bash
docker compose build backend --no-cache
docker compose up -d
```

### 9.2 "asyncpg connection refused"

PostgreSQL hazır olmadan backend başladı. `docker-compose.yml`'de `depends_on` healthcheck olmalı. Yeniden başlat:

```bash
docker compose restart backend
```

### 9.3 "CORS error" frontend'den

`.env`'de `FRONTEND_URL=http://localhost:5173` doğru mu?
Backend yeniden başlat.

### 9.4 Binance "rate limit exceeded"

Cache TTL'leri `.env`'de düşük olabilir. Artır.

### 9.5 lightweight-charts import error

```bash
docker compose exec frontend npm install lightweight-charts@4
```

### 9.6 yfinance veri çekemiyor

Saatlik rate limit (~2000). Cache yetersiz. CACHE_TTL_MACRO artır.

---

## 10. Öğrenme Kaynakları

### 10.1 Genel
- **FastAPI:** https://fastapi.tiangolo.com/
- **SQLAlchemy 2:** https://docs.sqlalchemy.org/en/20/
- **React + TypeScript:** https://react.dev/
- **TanStack Query:** https://tanstack.com/query/latest
- **Tailwind:** https://tailwindcss.com/docs

### 10.2 Trading
- **pandas-ta indicators:** https://github.com/twopirllc/pandas-ta
- **lightweight-charts:** https://tradingview.github.io/lightweight-charts/
- **Smart Money Concepts:** YouTube'da "ICT" araması
- **Wyckoff Method:** Wikipedia + "Wyckoff schematics" araması

### 10.3 Crypto API'ler
- **Binance API:** https://binance-docs.github.io/apidocs/
- **CoinGecko API:** https://www.coingecko.com/en/api/documentation
- **Coinglass API:** https://coinglass.github.io/api-access/
- **CryptoPanic API:** https://cryptopanic.com/developers/api/

---

## 11. İpuçları

**Disiplin:** Bir adım bitmeden sonrakine geçme. Yarım kalmış kod = hata kaynağı.

**Commit sıklığı:** Her küçük başarıdan sonra commit et. Sonra geri dönmek kolay olur.

**Test ciddi al:** Backend için unit testler kritik. Frontend için integration testler.

**CLAUDE.md güncelle:** Yeni bir tasarım kararı veya tuzak öğrendiğinde CLAUDE.md'ye ekle. Sonraki Claude Code session'larında otomatik okunur.

**Yedek al:** Her faz sonunda DB dump al:
```bash
docker compose exec postgres pg_dump -U marketlens marketlens > backup_faz1.sql
```

**Soru sorduğunda:** Claude Code'a karmaşık soruları küçük parçalara böl. Tek mesajda 5 farklı soru sorma.

**Acelesi olma:** Bu sistem **kalite** için yapılıyor. 4 ay sürse de değer.

---

## 12. Sonraki Adım

Şimdi:

1. ✅ Docker Desktop kurulu ve çalışıyor mu?
2. ✅ VS Code projeyi açtı mı?
3. ✅ Claude Code login oldu mu?
4. ✅ `.env` dosyası dolduruldu mu?

Eğer hepsi tamam ise:

```bash
# VS Code terminal'de
claude
```

Ve "İlk prompt"u yapıştır (yukarıdaki bölüm 3.1).

**Adım 1 başladı! 🚀**

---

## 13. Yardım Kanalları

- **Anthropic Docs:** https://docs.claude.com
- **Claude Code Docs:** https://docs.claude.com/en/docs/claude-code/overview
- **Claude Code GitHub:** https://github.com/anthropics/claude-code

Takıldığın yerde Claude Code'a sor — en iyi yardımcın o.

---

**İyi geliştirmeler!** 🎯
