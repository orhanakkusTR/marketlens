# MarketLens — Build Steps (v3)

Bu dosya yapılandırılmış prompt sequence'idir. Her adım Claude Code'a ayrı bir prompt olarak verilir.

## 🎯 MVP Yaklaşımı — Aktif Build Kapsamı

**Adım 1-26'ya odaklan.** Bu, yaklaşık **3 aylık** bir build süresi ve şunları içerir:
- **Faz 1 (Adım 1-22):** Tam temel sistem
- **Faz 2 — Önemli Yarısı (Adım 23-26):** Coinglass, SMC, News Feed, Sentiment Conflict

**Adım 26 = canlı kullanım başlangıcı.** Bu noktada sistem tam fonksiyonel:
- Tüm indikatörler + 2-katmanlı confluence
- Macro entegrasyonu + korelasyon
- SMC (Order Block, FVG, Liquidity Sweep, BOS/CHoCH)
- Aksiyon Özeti + Heatmap + Aksiyon önerisi
- Risk yönetimi + No-trade zone
- Telegram bildirimleri + Trade Journal temel
- News Feed + Sentiment Conflict Detector
- Coinglass likidasyon haritası

**Adım 27+ "Future Roadmap"** olarak işaretlendi. **Şimdi build edilmeyecek.** 6 ay canlı kullanım sonrası, gerçek ihtiyaçlar belli olduğunda **seçici olarak** eklenecek.

### 🚦 Kuralı

1. Adım 1'den başla, sırayla git.
2. Her adım sonu test et, çalışınca commit.
3. Adım 26'ya geldiğinde **DURVR**.
4. 3 ay canlı kullan (paper trade + küçük gerçek pozisyon).
5. Hangi özelliklerin gerçekten lazım olduğunu **veriden** gör.
6. 6 ay sonra Future Roadmap'i **gerçek ihtiyaca göre** önceliklendir.

---

## FAZ 1 — TEMEL (4-5 hafta) — Adım 1-22

### Adım 1: Proje İskeleti ve Docker Setup

```
MarketLens projesinin temel iskeletini oluştur.

Yapı:
marketlens/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── api/v1/
│   │   ├── services/
│   │   │   ├── indicators/
│   │   │   ├── confluence/
│   │   │   ├── risk/
│   │   │   └── analysis/
│   │   ├── data/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── workers/
│   │   ├── db/
│   │   └── main.py
│   ├── tests/
│   ├── alembic/
│   ├── scripts/
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── lib/
│   │   ├── hooks/
│   │   ├── stores/
│   │   └── types/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
├── nginx/
├── .env.example
└── README.md

Backend: Python 3.12, FastAPI, async.
Frontend: React 18 + Vite + TypeScript + TailwindCSS + shadcn/ui + lightweight-charts.
docker-compose.yml: postgres, redis, backend, frontend (4 servis, health check, depends_on).
.env.example: tüm değişkenler placeholder'la (CLAUDE.md'deki listeye göre).

CLAUDE.md proje root'unda, otomatik okunacak. Tüm tercihlere uy.
```

---

### Adım 2: Database Schema ve Migrations

```
docs/database-schema.md'deki tüm tabloları SQLAlchemy 2.0 modeli olarak oluştur.

backend/app/models/:
- user.py
- symbol.py (sektör etiketleri dahil)
- analysis.py (analyses, confluence_scores: lokal+macro+final, scenarios)
- setup.py
- trade.py
- alert.py (priority alanı dahil)
- settings.py (volatility-adjusted risk, akıllı azaltma)
- watchlist.py
- price_cache.py
- correlation.py
- macro_metric.py (TOTAL, dominans, DXY, vb.)
- economic_event.py

Async SQLAlchemy 2.0, asyncpg, UUID primary key.
Alembic init, async env.py.

Sembol seed: Tier 1+2+3+4 + GOLD = 25 + 1 sembol (CLAUDE.md'deki tam liste).
Sektör etiketleri otomatik atansın.

Test: `alembic upgrade head` sorunsuz çalışmalı.
```

---

### Adım 3: Core Config ve Logging

```
backend/app/core/:

config.py:
- Pydantic Settings
- Tüm env değişkenleri tipli ekspoze
- Cache TTL'ler config'de

logging.py:
- structlog JSON output
- Request ID injection middleware

security.py:
- JWT encode/decode
- Password hashing (bcrypt)
- get_current_user dependency

exceptions.py:
- MarketLensError base + custom sınıflar
- Global exception handler
- Standart error response format

middleware.py:
- Request ID, logging, rate limit (slowapi)

main.py:
- FastAPI app, middleware, CORS, lifespan
- Healthcheck /health
```

---

### Adım 4: Auth System

```
backend/app/api/v1/auth.py:
- POST /auth/login
- POST /auth/refresh
- GET /auth/me

scripts/create_user.py — admin user oluşturucu.

pytest auth flow + protected endpoint testi.
```

---

### Adım 5: Binance + CoinGecko + yfinance Data Clients

```
backend/app/data/:
- base.py: AbstractDataClient
- binance_spot.py: BinanceSpotClient (OHLCV — 15m, 1H, 4H, 1D, 1W, 1M)
- binance_futures.py: BinanceFuturesClient (funding, OI, L/S, liquidations)
- binance_depth.py: BinanceDepthClient (order book)
- binance_ws.py: BinanceWebSocketClient (real-time)
- coingecko.py: CoinGeckoClient (TOTAL, TOTAL2, TOTAL3, BTC.D, ETH.D, OTHERS.D)
- yfinance_client.py: YFinanceClient (GOLD, DXY, S&P, NASDAQ, VIX, US10Y)
- fear_greed.py: AlternativeMeClient

Her client:
- Async (httpx)
- Built-in retry (tenacity)
- Circuit breaker (pybreaker)
- Redis cache decorator
- Rate limit aware

Cache TTL'ler (15m için yeni ekleme):
- 15m mum: 60 sn
- 1H mum: 10 dk
- 4H mum: 30 dk
- 1D mum: 1 saat
- (diğerleri architecture.md'de)

backend/app/services/data_service.py:
- Unified facade
- get_klines, get_funding, get_oi, get_orderbook
- get_total, get_dominance
- get_dxy, get_sp500, get_vix
- get_fear_greed

Test: integration tests (gerçek API'ler), pytest -m integration flag.
```

---

### Adım 6: Indicator Engine — Trend & Momentum

```
backend/app/services/indicators/:

ma_strategy.py:
- compute_ma_set(df, timeframe) → dict
- 1H/4H: EMA 50/100/200
- 1D: EMA 50/100 + SMA 200
- 1W/1M: SMA 50/100/200
- Manuel override için tip parametresi

trend.py:
- ichimoku(df) → tenkan, kijun, senkou_a/b, chikou
- market_structure(df) → HH/HL/LH/LL detection (ZigZag fractal)

momentum.py:
- rsi_14(df)
- macd(df) → line, signal, histogram, state
- stoch_rsi(df)
- divergence(df, indicator) → bullish/bearish/none

Unit test her modül için (synthetic OHLCV).
```

---

### Adım 7: Indicator Engine — Volume, Volatility, Fibonacci

```
backend/app/services/indicators/:

volatility.py:
- atr(df, period=14)
- bollinger(df, period=20, std=2)
- bb_width(df) → squeeze detection

volume.py:
- obv(df)
- vwap(df, reset_daily=True)
- volume_profile(df, lookback=100) → poc, vah, val

fibonacci.py:
- detect_swings(df, threshold_atr_pct=1.0) → swing_high, swing_low
- fib_retracement(swing_high, swing_low) → 0.236, 0.382, 0.5, 0.618, 0.786
- fib_extension(swing_high, swing_low) → 1.272, 1.618, 2.618

Test: synthetic OHLCV ile beklenen seviyeler.
```

---

### Adım 8: Indicator Engine Orchestrator

```
backend/app/services/indicator_engine.py:

class IndicatorEngine:
    async def compute_all(symbol, timeframe, modules) → dict
        # 1. OHLCV çek
        # 2. MA strategy (TF'e göre uygun)
        # 3. Tüm indikatörleri hesapla (sadece istenen modüller)
        # 4. Cache key: hash(symbol, tf, son mum timestamp)
        # 5. Return structured dict

Modül tipleri: trend, momentum, volume, volatility, fibonacci, futures.

backend/app/services/futures_metrics.py:
- get_funding_analysis(symbol) → current, 8h_avg, 24h_avg
- get_oi_change(symbol) → 1h, 4h, 24h yüzdeleri
- get_long_short_anomaly(symbol) → ratio + extreme tespit

Test: golden tests (sentetik veriler için beklenen çıktılar).
```

---

### Adım 9: Confluence Engine — Lokal Skor

```
backend/app/services/confluence/local.py:

def compute_trend_score(indicators, timeframe) → float
    # MA dizilimi: ±30
    # Fiyat MA200 üstü: ±20
    # Ichimoku: ±20
    # Market structure: ±30
    # 1D bonus (hem EMA200 hem SMA200 üstü): +10/-10

def compute_momentum_score(indicators) → float
    # RSI yön+seviye: ±25
    # MACD: ±25-30
    # StochRSI: ±15-25
    # Divergence: ±20

def compute_volume_score(indicators) → float
    # OBV uyumu: ±25
    # Hacim/ortalama: ±25
    # POC pozisyonu: ±20
    # VWAP pozisyonu: ±30

def compute_volatility_score(indicators) → float
    # BB squeeze çıkışı: +30
    # ATR normal: 0/-20

def compute_futures_score(indicators) → float
    # Funding aşırı: -30
    # OI+fiyat uyumu: ±30
    # L/S ratio aşırı: -15

def compute_local_confluence(scores, weights) → float
    # Ağırlıklar: trend 0.40, momentum 0.20, volume 0.15, vol 0.10, futures 0.15

Golden tests: çeşitli senaryolar için beklenen skorlar.
```

---

### Adım 10: Macro Module — Veri Toplama

```
backend/app/services/macro/:

context.py:
- get_macro_snapshot() → tüm metrikleri tek call'da çek
  - TOTAL, TOTAL2, TOTAL3 (CoinGecko)
  - BTC.D, ETH.D, OTHERS.D (CoinGecko)
  - DXY, SP500, NASDAQ, VIX, US10Y (yfinance)
  - Fear & Greed (Alternative.me)
- compute_trends() → her metrik için 24h, 7d trend yönü ve %değişim
- get_eth_btc_ratio() → güncel + 7d değişim

Cache: 5 dk Redis.

backend/app/services/macro/regime.py:
- detect_market_regime() → ALT_BULL, BTC_BULL, RISK_OFF, ALT_SEASON_EARLY, MIXED
- Tetikleyici koşullar architecture.md'deki tabloya göre.

Endpoint:
GET /api/v1/macro/snapshot
GET /api/v1/macro/regime

Frontend: MacroContextCard component (dashboard üstü).
```

---

### Adım 11: Macro Modifier + Final Confluence

```
backend/app/services/confluence/macro.py:

def compute_macro_modifier(symbol, macro_data) → float
    # BTC için:
    if symbol_type == "btc":
        modifier = (
            btc_dominance_modifier(BTC.D_trend) +  # ↑ pozitif
            sp500_modifier(sp500_trend) +
            dxy_modifier(dxy_trend) +              # negatif korelasyon
            vix_modifier(vix_level)
        )
    # Altcoin için:
    else:
        modifier = (
            -btc_dominance_modifier(BTC.D_trend) +  # ters
            total3_modifier(total3_trend) +
            eth_btc_modifier(eth_btc_change_7d) +
            dxy_modifier(dxy_trend) * 0.7 +
            market_regime_modifier(current_regime)
        )
    return clamp(modifier, -25, 25)

backend/app/services/confluence/__init__.py:

def compute_final_confluence(local_score, macro_modifier) → float
    return clamp(local_score + macro_modifier, -100, 100)

backend/app/services/confluence/alignment.py:

def compute_multi_tf_alignment(scores_by_tf) → dict
    # Ağırlıklar: 15m 0.05, 1H 0.10, 4H 0.25, 1D 0.30, 1W 0.20, 1M 0.10
    # 15m sadece timing, ana karar 4H + 1D
    # Label: Strong/Aligned/Conflicted
```

---

### Adım 12: Korelasyon Engine

```
backend/app/services/correlation.py:

class CorrelationEngine:
    async def compute_correlation_matrix(symbols, period_days=30, tf="4H")
        # Pearson correlation
        # Log returns
        # Cache 1 saat
        # Return: pandas DataFrame'i dict'e çevrilmiş

    async def get_correlations_for_symbol(symbol)
        # symbol vs BTC, ETH, TOTAL3, DXY, SP500
        # Return ordered dict

    async def detect_correlation_risk(open_positions)
        # Açık pozisyonların ağırlıklı korelasyonu
        # >0.75 ise warning

Endpoint: GET /api/v1/macro/correlations?symbol=SOL

Cron job: her saat full matrix güncelle.
```

---

### Adım 13: Setup Quality Engine + 3 Kritik Modül (Confidence, Counter-Trend, Trade Quality)

Bu adım **dört modülü birden** içerir. Hepsi Setup Quality skoruna birlikte etki eder.

```
backend/app/services/setup_quality.py:

def compute_setup_quality(analysis) → dict
    score = 0
    factors = {}
    
    # Multi-TF alignment Strong: +20
    # 4H + 1D aynı yöne: +20
    # Market structure temiz: +10
    # R:R ≥ 3: +10
    # ATR normal: +10
    # Funding ekstrem değil: +5
    # Yakın major event yok: +5
    # Macro modifier > 0: +10
    # Korelasyon riski düşük: +5
    # Time-of-day uygun: +5
    
    # Toplam → grade: A (90+), B (70+), C (50+), D (<50)
    
    # Macro etkisi:
    if macro_modifier > 15: grade += 1  # not yükselt
    if macro_modifier < -15: grade -= 1
    
    # Counter-trend etkisi (aşağıda detaylı):
    if counter_trend_warnings_count >= 2: grade -= 1
    
    # Trade quality etkisi:
    if trade_quality.verdict == "EXCELLENT": grade += 1
    elif trade_quality.verdict == "WEAK": grade -= 1
    elif trade_quality.verdict == "AVOID": grade = "D"  # ne olursa olsun açma
    
    return {score, grade, factors, confidence, counter_trend_warnings, trade_quality}

backend/app/services/confidence_engine.py:

class ConfidenceEngine:
    """
    Sistemin TAHMİNİNE ne kadar güvenmesi gerektiğini ölçer.
    Bu, olasılık (probability) değil, kanıt seviyesidir.
    
    Trade journal verisinden hesaplanır.
    """
    
    def compute_confidence(self, setup_signature, user_id) -> dict:
        # setup_signature: macro_regime + setup_quality + direction + 
        #                  symbol_category + market_session
        
        similar_trades = trade_journal.find_similar(
            setup_signature, user_id, lookback_days=180
        )
        
        n = len(similar_trades)
        
        if n < 5:
            level = "VERY_LOW"
            label = "⚠️ Kanıt yok, deneme aşaması"
            advice = "İlk 5-10 işlem küçük pozisyonla deneyim toplayın"
        elif n < 15:
            level = "LOW"
            label = "⚠️ Az veri, dikkatli"
            advice = "Pozisyon boyutunu %50 küçültün"
        elif n < 30:
            level = "MEDIUM"
            label = "🟡 Orta kanıt"
            advice = "Normal pozisyon, izlemeye devam"
        elif n < 60:
            level = "HIGH"
            label = "🟢 Güçlü kanıt"
            advice = "Tam pozisyon önerilir"
        else:
            level = "VERY_HIGH"
            label = "🟢 Çok güçlü kanıt"
            advice = "Bu setup tipinde sistem güvenilir"
        
        actual_win_rate = (
            sum(t.is_win for t in similar_trades) / n if n > 0 else None
        )
        
        return {
            "level": level,
            "label": label,
            "trade_count": n,
            "actual_win_rate": actual_win_rate,
            "advice": advice
        }

backend/app/services/counter_trend.py:

class CounterTrendDetector:
    """
    Sistem kendi sinyalini SORGULAR.
    "Kusursuz" görünen setup'lar tuzak olabilir.
    """
    
    def detect(self, market_data, signal_direction) -> list[Warning]:
        warnings = []
        
        # 1. Parabolik hareket (2h içinde >%3)
        if abs(market_data.price_change_2h) > 3.0:
            warnings.append({
                "type": "parabolic_move",
                "severity": "high",
                "message": f"2h içinde %{market_data.price_change_2h:.1f} hareket",
                "advice": "Pullback bekle, FOMO'ya kapılma"
            })
        
        # 2. Funding ekstrem
        if abs(market_data.funding_rate) > 0.0008:
            warnings.append({
                "type": "extreme_funding",
                "severity": "high",
                "message": f"Funding {market_data.funding_rate*100:.3f}%",
                "advice": "Aşırı kalabalık, squeeze riski"
            })
        
        # 3. L/S aşırı (sistem long öneriyor + L/S çok yüksek)
        if signal_direction == "long" and market_data.ls_ratio > 3.0:
            warnings.append({
                "type": "extreme_ls_long",
                "severity": "high",
                "message": f"L/S {market_data.ls_ratio:.1f} — long sıkışmış"
            })
        if signal_direction == "short" and market_data.ls_ratio < 0.33:
            warnings.append({
                "type": "extreme_ls_short",
                "severity": "high",
                "message": f"L/S {market_data.ls_ratio:.1f} — short sıkışmış"
            })
        
        # 4. Volume exhaustion
        if signal_direction == "long" and market_data.volume_decreasing_count >= 3:
            warnings.append({
                "type": "volume_exhaustion",
                "severity": "medium",
                "message": "Yükselişte hacim azalıyor"
            })
        
        # 5. RSI extreme + price stalling
        if (market_data.rsi_4h > 75 and abs(market_data.price_change_4h) < 0.5):
            warnings.append({
                "type": "rsi_stall",
                "severity": "medium",
                "message": "RSI aşırı + fiyat duruyor — bearish divergence kuruluyor"
            })
        
        return warnings

backend/app/services/trade_quality_filter.py:

class TradeQualityFilter:
    """
    Confluence yüksek olsa bile VASAT setup'ları ayıklar.
    Edge'i olmayan setup'ları işaretler.
    """
    
    def evaluate(self, market_data) -> dict:
        score = 0
        factors = []
        
        # 1. Volatilite yeterli (ATR > %0.8)
        atr_pct = market_data.atr / market_data.price * 100
        passed = atr_pct > 0.8
        if passed: score += 1
        factors.append({
            "name": "volatility",
            "passed": passed,
            "value": f"ATR %{atr_pct:.2f}",
            "note": ("Volatilite yeterli" if passed 
                     else "Düşük volatilite, hareket yavaş, funding kâr yer")
        })
        
        # 2. Trend strength (ADX > 20)
        passed = market_data.adx > 20
        if passed: score += 1
        factors.append({
            "name": "trend_strength",
            "passed": passed,
            "value": f"ADX {market_data.adx:.0f}",
            "note": ("Trend piyasası" if passed 
                     else "Range piyasası, trend pozisyonu zayıf")
        })
        
        # 3. Macro netlik (DXY/SP500 uyumlu)
        macro_aligned = self._is_macro_aligned(market_data)
        if macro_aligned: score += 1
        factors.append({
            "name": "macro_clarity",
            "passed": macro_aligned,
            "note": ("Macro net" if macro_aligned 
                     else "Macro karışık (DXY/SP500 ters yönde)")
        })
        
        # 4. Volume büyüyor (son 4 mum)
        passed = market_data.volume_increasing_4candles
        if passed: score += 1
        factors.append({
            "name": "volume_growth",
            "passed": passed,
            "note": ("Hacim yükseliyor" if passed else "Hacim yatay, momentum zayıf")
        })
        
        # 5. Major S/R uzakta (>2 ATR)
        sr_distance_atr = market_data.nearest_major_sr_distance / market_data.atr
        passed = sr_distance_atr > 2.0
        if passed: score += 1
        factors.append({
            "name": "clear_path",
            "passed": passed,
            "value": f"{sr_distance_atr:.1f} ATR",
            "note": ("Yakın S/R yok, hareket alanı temiz" if passed 
                     else "S/R yakın, sıkışık")
        })
        
        # Verdict
        if score >= 4:
            verdict = "EXCELLENT"
            quality_modifier = +1
        elif score >= 3:
            verdict = "GOOD"
            quality_modifier = 0
        elif score >= 2:
            verdict = "WEAK"
            quality_modifier = -1
        else:
            verdict = "AVOID"
            quality_modifier = -2
        
        return {
            "score": score,
            "verdict": verdict,
            "quality_modifier": quality_modifier,
            "factors": factors
        }
    
    def _is_macro_aligned(self, market_data):
        # DXY ↓ + SP500 ↑ = bullish kripto
        # DXY ↑ + SP500 ↓ = bearish kripto
        dxy_dir = market_data.dxy_change_24h
        spx_dir = market_data.sp500_change_24h
        return (dxy_dir < 0 and spx_dir > 0) or (dxy_dir > 0 and spx_dir < 0)


# Aksiyon Özeti payload'ı:
{
    "setup_quality": {
        "grade": "A",
        "score": 92,
        "factors": [...]
    },
    "confidence": {
        "level": "LOW",
        "label": "⚠️ Az veri, dikkatli",
        "trade_count": 8,
        "actual_win_rate": 0.625,
        "advice": "Pozisyon boyutunu %50 küçültün"
    },
    "counter_trend_warnings": [
        {"type": "extreme_funding", "severity": "high", ...},
        ...
    ],
    "trade_quality": {
        "score": 4,
        "verdict": "EXCELLENT",
        "factors": [...]
    }
}

Test: 
- Çeşitli market koşulları için fixture'lar
- Confidence engine: synthetic trade history ile test
- Counter-trend: bilinen "trap" senaryoları için
- Trade quality: range/trend/exhaustion senaryoları için
```

---

### Adım 14: Time-of-Day & No-Trade Zone

```
backend/app/services/risk/no_trade_zone.py:

def detect_no_trade_zone(user_id, symbol) → NoTradeResult
    # 1. Macro events check (CPI, FOMC, NFP) ± 4h
    # 2. Time-of-day:
    #    - 00-08 UTC: low_volatility (uyarı)
    #    - 13-22 UTC: high_volatility (normal)
    # 3. Weekly close (Pazar 22-Pazartesi 02 UTC)
    # 4. High volatility (BTC 24h %8+)
    # 5. Daily limit aşımı
    # 6. Tilt (3 ardışık stop son 24h)
    # 7. Manuel pause

Macro calendar ilk versiyon manuel JSON dosyası (major_events.json).
Faz 2'de forexfactory scrape ekleyeceğiz.

Endpoint: GET /api/v1/risk/no-trade-status

Frontend: dashboard üstünde kırmızı bant + Telegram bildirim.
```

---

### Adım 15: Risk Management Module — Volatility-Adjusted

```
backend/app/services/risk/position_sizer.py:

def calculate_volatility_factor(market_data) → float
    btc_24h_change_abs = abs(market_data.btc_24h_change)
    if btc_24h_change_abs > 8: return 0.5
    if btc_24h_change_abs > 5: return 0.7
    if atr_zscore > 2: return 0.7
    return 1.0

def calculate_position(account_balance, base_risk_pct, entry, stop, max_leverage, market_data)
    volatility_factor = calculate_volatility_factor(market_data)
    adjusted_risk_pct = base_risk_pct * volatility_factor
    
    risk_amount = account_balance * (adjusted_risk_pct / 100)
    stop_distance_pct = abs(entry - stop) / entry * 100
    position_size = risk_amount / (stop_distance_pct / 100)
    required_leverage = max(1, ceil(position_size / margin_available))
    actual_leverage = min(required_leverage, max_leverage)
    
    return {
        position_size_usd, leverage, margin_used,
        liquidation_price_at_5x, liquidation_price_at_10x,
        funding_cost_24h, funding_cost_72h, funding_cost_1w,
        risk_amount_usd, base_risk_pct, adjusted_risk_pct,
        volatility_factor, warnings
    }

backend/app/services/risk/daily_tracker.py:

class DailyRiskTracker:
    def can_open_new_trade(user_id) → (bool, reason)
    def get_current_risk_pct(user_id) → float (akıllı azaltma sonrası)
    def record_trade_opened(user_id, risk_used)
    def record_trade_closed(user_id, was_loss)
    def check_consecutive_losses(user_id) → int

Akıllı azaltma:
- 2 ardışık → %1.5 (1 saat)
- 3 ardışık → %1.0 (4 saat)

Endpoint:
- POST /api/v1/risk/calculate-position
- GET /api/v1/risk/daily-status
- POST /api/v1/risk/pause
```

---

### Adım 16: Senaryo Üretici + Aksiyon Özeti

```
backend/app/services/analysis/scenario_generator.py:

def collect_all_levels(indicators, current_price, atr, market_data) → list
    levels = []
    # Fib retracement seviyeleri
    # Fib extension seviyeleri
    # EMA / SMA seviyeleri (mevcut TF + üst TF)
    # Volume Profile POC, VAH, VAL
    # VWAP
    # Önceki swing high/low
    # Order book büyük duvarlar
    # Likidasyon kümeleri (Faz 2'de eklenecek)
    
    # Her level için confluence_count hesapla
    return levels

def generate_long_scenario(symbol, current_price, indicators, atr) → Scenario
    entry_low = current_price - 0.3 * atr
    entry_high = current_price + 0.3 * atr
    
    # Hedefler: yukarıdaki seviyelerden, en güçlü 3 confluence
    targets = pick_top_targets(levels, direction="long", current_price)
    
    # Stop: en yakın significant low - 0.5 * atr
    stop = nearest_significant_low - 0.5 * atr
    
    rr = (targets[0].price - entry_mid) / (entry_mid - stop)
    probability = sigmoid(final_confluence) * quality_bonus
    
    return Scenario(...)

backend/app/services/analysis/action_summary.py:

def generate_action_summary(analysis_result) → ActionSummary
    # 1. Tek cümle tavsiye (renk kodlu)
    # 2. Pozisyon detayları (kopyala-yapıştır format)
    #    - Giriş aralığı
    #    - TP1/TP2/TP3 + pozisyon yüzdesi (40/35/25)
    #    - SL
    #    - Pozisyon, kaldıraç, margin, R:R
    # 3. Destek/direnç tablosu (sıralı, golden ★)
    # 4. Dikkat edilecekler (uyarılar listesi)
    # 5. Görüş değişir eğer (invalidasyon kriterleri)
    # 6. Özet metin (2-3 cümle Türkçe)

Test: end-to-end BTC için.
```

---

### Adım 17: Analysis Orchestrator

```
backend/app/services/analysis/orchestrator.py:

async def run_analysis(user_id, symbol_code, timeframes, modules) → AnalysisResult
    # 1. Paralel data fetch (asyncio.gather)
    #    - OHLCV her TF için
    #    - Futures data
    #    - Macro snapshot
    #    - Korelasyonlar
    # 2. Her TF için:
    #    - indicator_engine.compute_all()
    #    - confluence local
    # 3. Macro modifier hesapla
    # 4. Final confluence + alignment
    # 5. Setup quality
    # 6. Senaryo üretici (long + short)
    # 7. Action Summary
    # 8. No-trade zone check
    # 9. DB'ye kaydet (analyses, confluence_scores, scenarios)
    # 10. Return full structured result

Endpoint:
- POST /api/v1/analysis/run
- GET /api/v1/analysis/{id}
- GET /api/v1/analysis/history

Performans hedefi: <2 saniye. asyncio.gather + aggressive cache.
```

---

### Adım 18: Frontend — Layout, Routing, Auth

```
Frontend temeli:

src/lib/api.ts — TanStack Query + axios + auth interceptor
src/lib/auth.ts — token storage
src/stores/useAuth.ts, useSelections.ts

shadcn/ui kurulumu (button, select, card, dialog, tooltip, badge, table, tabs).

Pages:
- /login
- / (Dashboard)
- /heatmap
- /scanner
- /journal
- /risk
- /settings
- /glossary

Layout: app shell
- Sol sidebar (nav)
- Üst bar
- Ana içerik

Tema: Binance dark (CLAUDE.md'deki renkler).
Inter + JetBrains Mono fontları.

Login sayfası tam çalışsın.
Protected routes wrapper.
```

---

### Adım 19: Sol Sembol Paneli

**⚡ Multi-symbol WebSocket stream BURADA tam yapılacak.** Adım 5'te tek-symbol skeleton'u vardı, şimdi:
- 27 sembol için aynı anda fiyat akışı
- Auto-reconnect + heartbeat
- Callback dispatcher: yeni fiyat → (a) sol panel UI güncelle, (b) **alarm worker'a push** (Adım 21B kullanır)
- Latency hedefi: <500ms (Binance'tan UI'ya)

```
src/components/sidebar/SymbolPanel.tsx

Genişlik 200px, collapse mümkün (60px ikon-only).

Üst kısım:
- Arama input
- Filtre buttonları: Tümü / A+B / ⭐ Favori
- Sıralama dropdown: Confluence / 24h% / Hacim / Alfabetik

Her satır:
- Sembol logo + isim
- Anlık fiyat (monospace)
- 24h % (renkli)
- Setup quality badge (A/B/C)
- Confluence renk noktası (yeşil/sarı/kırmızı)
- ⚡ ikonu (son 5dk büyük hareket)
- Hover'da background koyulaşır
- Aktif sembol için sol border accent

State: useSelections store.

WebSocket: real-time fiyat güncelle.
```

---

### Adım 20: Dashboard — Ana Yapı

```
src/pages/Dashboard.tsx

Layout:
1. Market Regime Banner (üstte)
2. Macro Context Card (TOTAL/dominans/DXY/SP500/VIX)
3. Sembol Header (fiyat + lokal/macro/final conf + setup quality)
4. Selection Bar (TF + modüller)
5. Chart placeholder (Adım 21'de)
6. Modul Cards (seçili modüller)
7. Korelasyon Paneli
8. Senaryo Kartları (Long/Short yan yana)
9. Aksiyon Özeti
10. (Faz 2-4'te) News, Wyckoff badge

Bileşenler ayrı dosyada:
- src/components/dashboard/MarketRegimeBanner.tsx
- src/components/dashboard/MacroContextCard.tsx
- src/components/dashboard/SymbolHeader.tsx
- src/components/dashboard/SelectionBar.tsx
- src/components/dashboard/cards/TrendCard.tsx
- src/components/dashboard/cards/MomentumCard.tsx
- src/components/dashboard/cards/VolumeCard.tsx
- src/components/dashboard/cards/VolatilityCard.tsx
- src/components/dashboard/cards/FuturesCard.tsx
- src/components/dashboard/cards/MacroCard.tsx
- src/components/dashboard/CorrelationPanel.tsx
- src/components/dashboard/ScenarioCard.tsx

Dynamic rendering: kullanıcı seçimine göre kartlar render.

State: useSelections store (sembol, TF, modüller).
Analiz: useQuery → POST /api/v1/analysis/run.
```

---

### Adım 21: Aksiyon Özeti + Hesabı Göster Modal + Pozisyon Yardımcısı

> **NOT (Adım 16'dan):** Backend tarafında `action_summary` modülü ayrı bir adım
> olarak yazılmıyor. Aksiyon Özeti'nin tüm verisi mevcut modüllerden gelir:
> `scenario` (entry/stop/TP'ler), `setup_quality` (grade + factors + confidence +
> counter-trend + trade-quality + no-trade-zones), `risk` (position size + leverage).
> Bu adımda frontend bu üç response'u kompoze eder ve kullanıcı dostu Türkçe metni
> burada üretir (kopyala-yapıştır pozisyon planı dahil). Tek source of truth: backend
> structured response; presentation layer frontend'de.

```
src/components/dashboard/ActionSummary.tsx

KRİTİK BILEŞEN. CLAUDE.md ve architecture.md'deki spec'e tam uyum.

İçerik:
1. Üst başlık (renk kodlu): 🟢 LONG ÖNERİLİYOR / 🔴 SHORT / ⚠️ DİKKAT / 🚫 NO-TRADE
   - Setup Quality (A/B/C/D) badge
   - **Olasılık + Confidence** (yan yana, ikisi de görünmeli):
     "Olasılık: %82 | Confidence: LOW ⚠️"
   
2. Pozisyon detayları (monospace, kopyala-yapıştır hazır)
   - Confidence LOW ise: "⚠️ Bu setup tipinde 8 işlem var, pozisyon boyutu %50 küçültüldü"
   - Trade Quality WEAK ise: "⚠️ Trade Quality 2/5, küçük pozisyon önerildi"
   
3. **🚨 Karşıt Sinyal Uyarısı kartı** (eğer counter-trend warnings varsa)
   - Hangi uyarılar tetiklendi listesi
   - "Bu pattern çoğu zaman trap olur" mesajı
   - Sistem önerisi (kaçın / küçük pozisyon)

4. **Trade Quality kartı**
   - 5 faktörden kaç tanesi geçti
   - Her faktör için ✓/✗ ve açıklama
   - Verdict: EXCELLENT / GOOD / WEAK / AVOID
   
5. Destek/Direnç tablosu (yukarı dirençler → mevcut → aşağı destekler, golden ★)

6. Dikkat edilecekler kartı

7. Görüş değişir eğer kartı

8. Aksiyon butonları:
   - 📋 Pozisyon Detaylarını Kopyala (clipboard'a)
   - 📒 Journal'a Ekle (modal açar — POZİSYON YARDIMCISI tetiklenir)
   - 🔔 Alarm Kur (custom alarm modal'ı açar)
   - 🔍 Hesabı Göster

src/components/dashboard/JournalAddModal.tsx (POZISYON YARDIMCISI):

Pozisyon detaylarını gösterir + ALT KISIM:

"🔔 Bu pozisyon için otomatik alarmlar yaratmak ister misin?"

Checkbox listesi (default tüm seçili):
☑ TP1 (3 aşamalı yaklaşma uyarısı)
☑ TP2 (3 aşamalı yaklaşma uyarısı)
☑ TP3 (3 aşamalı yaklaşma uyarısı)
☑ SL (3 aşamalı yaklaşma uyarısı)

"4 alarm otomatik yaratılacak."

[Kaydet (4 alarmla)] [Sadece TP'ler (3 alarm)] [Alarmsız kaydet]

Submit:
- POST /api/v1/trades — pozisyon kaydedilir
- POST /api/v1/user-alerts/from-trade/{trade_id} — auto alarmlar yaratılır
- Toast: "Pozisyon kaydedildi, 4 alarm aktif"

src/components/dashboard/CalculationModal.tsx:
- Her hedef ve stop için arkadaki tüm confluence detayı
- "TP1: 184.50 - neden?" açıklaması, indikatör listesi
- **Confidence detayı:** Bu setup signature'ında geçmiş işlemler listesi
- **Counter-trend detayı:** Hangi metrikler tetiklendi
- **Trade quality detayı:** 5 faktör için ayrıntılı değerlendirme

Tüm metrikler için ⓘ tooltip:
- "Olasılık nedir?"
- "Confidence nedir? Olasılıktan farkı?"
- "Counter-trend ne demek?"
- "Trade Quality nasıl hesaplanır?"
```

---

### Adım 21B: Manual Alert System + /alerts Sayfası

**⚡ KRİTİK: Alarm tetikleme mekanizması WebSocket-bazlı olmalı (polling değil).**

Latency hedefi: **<2 saniye** (fiyat değişiminden Telegram bildirimine).

Mimari:
- Adım 19'da yazılan multi-symbol WS stream → fiyat değişiminde callback
- Alarm worker bu callback'i dinler, in-memory `active_alerts` cache'inden sembol için aktif alarmları kontrol eder
- Tetiklenirse anında bildirim gönderir (Telegram + DB güncelleme)
- Polling (30 saniyede bir) sadece **fallback** olarak kalır (WS down olursa)

**Sebep:** Polling 30sn ile A-setup oluşumu kabul edilebilir gecikme ama **manuel alarm hedefe ulaşma** anlık olmalı. Kullanıcı bildirim alır almaz Binance'a girip emir verecek.

Bu adım, MVP'nin önemli bir parçası: kullanıcının elle yarattığı fiyat alarmları.

```
backend/app/services/alert_engine.py:

class ApproachAlertEngine:
    """3 aşamalı yaklaşma uyarısı motoru."""
    
    def compute_distances(self, symbol, target_price) -> dict:
        atr_4h = get_atr(symbol, "4H")
        return {
            "approaching": atr_4h * 1.0,   # 1 ATR uzakta
            "close": atr_4h * 0.5,         # 0.5 ATR uzakta
            "target": 0
        }
    
    def check_alert(self, alert, current_price) -> StageEvent | None:
        # Stage 1: approaching (1 ATR)
        # Stage 2: close (0.5 ATR)
        # Stage 3: target_reached
        ...

backend/app/workers/alert_monitor.py (Celery):

@celery_app.task
def check_user_alerts():
    """Her 30 saniyede çalışır."""
    active = db.query(user_alerts).filter(status="active").all()
    
    # Toplu fiyat çek
    symbols = set(a.symbol_id for a in active)
    prices = batch_get_prices(symbols)
    
    for alert in active:
        check_and_notify(alert, prices[alert.symbol_id])

backend/app/api/v1/user_alerts.py:

GET    /api/v1/user-alerts                       # liste
GET    /api/v1/user-alerts/{id}                  # detay
POST   /api/v1/user-alerts                       # yarat
PATCH  /api/v1/user-alerts/{id}                  # düzenle
DELETE /api/v1/user-alerts/{id}                  # sil
POST   /api/v1/user-alerts/from-trade/{trade_id} # pozisyondan otomatik 4 alarm

src/pages/Alerts.tsx (yeni sayfa):

Layout:
- Üstte: "Yeni Alarm" butonu (CreateAlertModal)
- Filtre: Aktif / Tetiklenmiş / İptal
- Tablo:
  - Sembol (logo + isim)
  - Tip (price_above / price_below / approach)
  - Hedef fiyat
  - Şu an fiyat (real-time)
  - Mesafe (% ve ATR cinsinden)
  - Durum (aktif / aşama 1 / aşama 2 / tetiklendi)
  - Pozisyon bağlantısı (varsa)
  - Aksiyonlar (düzenle / sil)
- Filtre: sembol, tip, durum

src/components/alerts/CreateAlertModal.tsx:

Form:
- Sembol (dropdown, ana semboller)
- Hedef fiyat (sayı input — şu anki fiyatın üstü/altı önemli değil, sistem yön belirler)
- Tip:
  ◯ Sadece fiyat (basit, tek bildirim)
  ◉ Yaklaşma uyarısı (3 aşamalı — önerilen)
- Not (opsiyonel, "kırılırsa long açacağım" gibi)
- Bildirim ayarları:
  ☑ Telegram
  ☑ Sesli (target ulaşınca)
  ☑ Titreşimli (target ulaşınca)
- "Yarat" butonu

src/components/dashboard/QuickAlertButton.tsx:

Dashboard'da Aksiyon Özeti içinde "🔔" butonu.
Tıklandığında modal açar ama mevcut sembolü ön-doldurulmuş gelir.
Kullanıcı sadece fiyat girer, "Yarat".
5 saniyelik akış.

Frontend:
- Real-time fiyat güncellemesi (WebSocket)
- Mesafe hesabı: (target - current) / atr_4h
- "Aşama 2 (0.3 ATR uzakta)" gibi gösterim
- Tetiklenmiş alarmlar farklı renk

Test:
- Approach engine: 3 aşama doğru tetikleniyor mu
- Worker: çakışan alarmlar doğru sıralanıyor mu
- Frontend: real-time fiyat akışı, modal akışı
```


#### Auto-Watch S/R Modülü (alt-modül)

Manuel alarm sistemine paralel çalışan otomatik destek/direnç alarm sistemi. Kullanıcı önemli sembollerin (BTC, ETH, GOLD vb.) kritik seviyelerini elle takip etmek zorunda kalmaz — sistem kendi tespit edip alarm kurar.

**Default semboller:** BTC, ETH, GOLD
**Default timeframes:** 4H + 1D (sadece bunlardan tespit)
**Bildirim sıklığı:** Tüm tespit edilen önemli seviyeler (min confluence 1+)

```
backend/app/services/auto_watch.py:

class AutoWatchService:
    """
    Önemli S/R seviyelerine otomatik alarm yaratır.
    """
    
    DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "GOLD"]
    DEFAULT_TIMEFRAMES = ["4H", "1D"]
    
    async def refresh_alerts_for_symbol(self, user_id, symbol, timeframes):
        """
        Bir sembol için S/R seviyelerini yeniden hesapla, alarmları güncelle.
        - Adım 7'deki indicator_engine.compute_levels() kullanılır
        - 4H ve 1D ayrı ayrı tespit edilir
        - Eski auto-generated alarmlar (henüz tetiklenmemiş) silinir
        - Yeni seviyeler için 'approach' alarmları yaratılır
        - related_trade_id=NULL, auto_generated=True, target_role='auto_sr_4h' veya 'auto_sr_1d'
        - Min confluence kontrolü (kullanıcı ayarına göre)
        """
    
    async def daily_digest(self, user_id):
        """
        Sabah 09:00'da Telegram'a günlük özet at.
        Format:
        '☀️ Günaydın! Bugünkü kritik seviyeler:
         BTC: yukarı $82,400★★★ | aşağı $79,800★★★ ...
         ETH: yukarı $3,720★★★ | aşağı $3,250★★ ...
         GOLD: yukarı $4,800★★★ | aşağı $4,580★★ ...'
        """

backend/app/workers/auto_watch_worker.py (Celery):

@celery_app.task
def refresh_auto_watch_alerts():
    """
    Her 6 saatte: 06:00, 12:00, 18:00, 00:00 UTC
    Tüm aktif kullanıcılar için:
        - Auto-Watch açıksa
        - Auto-Watch sembollerinin S/R alarmlarını yenile
    """

@celery_app.task
def send_daily_digest():
    """
    Sabah 09:00 (kullanıcı timezone'una göre)
    Daily digest açıksa Telegram'a günlük özet
    """

backend/app/api/v1/auto_watch.py:

GET    /api/v1/auto-watch/settings          # Mevcut ayar
PATCH  /api/v1/auto-watch/settings          # Ayar güncelle
POST   /api/v1/auto-watch/refresh-now       # Manuel tetikle (test)

src/pages/Settings.tsx (Auto-Watch sekmesi):

Layout:
- Master switch: Auto-Watch ON/OFF
- Sembol listesi:
  - Default: BTC, ETH, GOLD (her zaman görünür, kapatabilirsin)
  - "Sembol Ekle" butonu → 27 sembolden seç
  - Her sembol yanında çıkar (X) butonu
- Timeframe: ☑ 4H ☑ 1D (toggle)
- Min confluence: dropdown (1, 2, 3) — default 1
- Günlük özet ON/OFF
- "Şimdi yenile" butonu (manuel tetikle, test için)
- "Aktif alarmlar" küçük özet (kaç tane auto-watch alarm aktif)

Auto-Watch ayarları DB'de:
ALTER TABLE user_settings ADD COLUMN auto_watch_enabled BOOLEAN DEFAULT true;
ALTER TABLE user_settings ADD COLUMN auto_watch_symbols TEXT[] DEFAULT ARRAY['BTCUSDT','ETHUSDT','GOLD'];
ALTER TABLE user_settings ADD COLUMN auto_watch_timeframes TEXT[] DEFAULT ARRAY['4H','1D'];
ALTER TABLE user_settings ADD COLUMN auto_watch_min_confluence INTEGER DEFAULT 1;
ALTER TABLE user_settings ADD COLUMN auto_watch_daily_digest BOOLEAN DEFAULT true;

Test:
- Synthetic S/R levels → alarm yaratıldı doğrulaması
- Worker idempotency (aynı saniyede 2 kez çağırma → çakışma yok)
- Sembol kaldırılınca alarmları silinir
- Auto-Watch kapatılınca tüm auto_generated alarmlar pasifleşir
- Min confluence filtresi doğru çalışıyor
- Daily digest formatlama testi

Önemli notlar:
- Auto-Watch alarmları 'auto_sr_4h' veya 'auto_sr_1d' role'leri ile işaretlenir
- Manual alarm sistemiyle aynı user_alerts tablosunu kullanır
- Aynı 3 aşamalı yaklaşma uyarısı (1 ATR / 0.5 ATR / hedef)
- Tetiklenen Auto-Watch alarmları 7 gün cooldown (aynı seviye sürekli tetiklenmesin)
```

---

---

### Adım 22: Heatmap Sayfası + Grafik

```
src/pages/Heatmap.tsx

Tablo:
- 27 sembol satır
- Sütunlar: sembol, fiyat, 24h%, 1H conf, 4H conf, 1D conf, setup quality, sektör
- Renk kodu: confluence skoruna göre yeşil-sarı-kırmızı
- Sıralama: tüm sütunlardan
- Filtre: Tümü / A+B / Sektörlere göre

Endpoint: GET /api/v1/heatmap → tüm semboller için özet analiz

Cron: her 5 dk arka planda heatmap data güncelle.

src/components/chart/PriceChart.tsx (Faz 1 versiyonu):

lightweight-charts v4 entegrasyon.
- Candlestick series
- EMA/SMA çizgileri (TF'e göre uygun set)
- Bollinger Bands (toggle)
- Yatay çizgiler: hedefler (yeşil dashed), stop (kırmızı), Fib (turuncu), VWAP
- Volume histogram alt panel

Order book heatmap component:
- src/components/chart/OrderBookHeatmap.tsx
- Sağ kenar bid/ask yoğunluğu

Real-time: WebSocket /ws price subscribe.

Interactive:
- Mouse hover crosshair
- Zoom/pan
- TF değiştirme

Faz 2'de likidasyon, OB, FVG eklenecek.

Faz 1 polish:
- Loading states (skeleton)
- Error handling (Sonner toast)
- Empty states
- Responsive
- Production deploy hazırlığı
```

---

## FAZ 2 — PROFESYONEL ÖZELLİKLER (3-4 hafta) — Adım 23-26

**Bu fazın ilk yarısı MVP içinde** (Adım 23-26). Adım 27+ Future Roadmap.

### Adım 23: Coinglass Entegrasyonu

```
backend/app/data/coinglass.py: Hobbyist plan ($29/ay).

Endpoints:
- get_liquidation_heatmap(symbol, timeframe="24h", model=2)
- get_liquidation_aggregated_heatmap()
- get_liquidation_orders(symbol, limit=100)
- get_funding_overview()
- get_etf_flows() (BTC + ETH)

Cache 30 sn (heatmap), 5 dk (ETF).

backend/app/services/liquidation.py:
- analyze_clusters(heatmap_data, current_price)
- find_nearest_magnet(clusters, current_price)
- compute_magnet_pull_strength(cluster)

Endpoint: GET /api/v1/liquidation/heatmap
Endpoint: GET /api/v1/macro/etf-flows

Frontend:
- src/components/dashboard/cards/LiquidationCard.tsx
- Chart'a likidasyon bantları eklenecek
```

---

### Adım 24: Smart Money Concepts

```
backend/app/services/indicators/smc.py:

def detect_order_blocks(df, lookback=50) → list[OrderBlock]
    # Bullish OB: yükseliş öncesi son düşüş bloğu
    # Bearish OB: düşüş öncesi son yükseliş bloğu

def detect_fvg(df) → list[FairValueGap]
    # 3-mum boşluk pattern
    # Mum 1 high < Mum 3 low → bullish FVG
    # Mum 1 low > Mum 3 high → bearish FVG

def detect_liquidity_sweep(df, lookback=20) → list[LiquiditySweep]
    # Önceki swing high/low kısa kırılış + dönüş
    # Buy-side sweep + bullish engulfing → spring
    # Sell-side sweep + bearish engulfing → trap

def detect_bos_choch(df, structure_history) → BOSChoCHResult
    # BOS: trend yönünde structure kırılması
    # CHoCH: trend dönüşü structure kırılması

def compute_premium_discount_zone(swing_high, swing_low) → dict
    # 0.5 üstü = premium
    # 0.5 altı = discount

Indicator engine'e entegre.
Confluence trend skoruna SMC bonus +15 ekle.
Chart'ta görselleştir (OB rectangle, FVG soluk dikdörtgen, sweep işareti).
```

---

### Adım 25: News Feed (CryptoPanic)

```
backend/app/data/cryptopanic.py:
- get_news(filter="hot", currencies=None, limit=20)
- Cache 5 dk

backend/app/services/news.py:
- categorize_news(items) → high_impact, medium, low
- match_to_symbols(news_items, watchlist)
- detect_critical_news(items) → ["BTC ETF approved", "FED rate cut"...]

Endpoint:
- GET /api/v1/news/feed
- GET /api/v1/news/critical (son 24h)

Frontend:
- src/components/dashboard/NewsWidget.tsx (sağ sidebar veya alt)
- Saat damgalı liste, sentiment badge

Critical news → Telegram bildirim (high priority).
```

---

### Adım 26: Cross-Asset Rotation Tracker

```
backend/app/services/rotation.py:

SECTOR_MAPPING = {
    "L1": [...],
    "L2": [...],
    "DeFi": [...],
    "Meme": [...],
    "Other": [...]
}

def compute_sector_performance(period_days) → dict
    # Her sektör için: 1d, 7d, 30d ortalama performans
    # Best performing, worst performing

def detect_rotation(history) → RotationEvent
    # Para hangi sektörden hangisine kaydı

Endpoint: GET /api/v1/macro/rotation

Frontend:
- src/components/dashboard/RotationHeatmap.tsx
- Her sektörün renkli kutusu, performans gösterimi
- Trend ok yönü
```

---

# 🛑 MVP CUT-OFF — ADIM 26 SONU

**BURAYA KADAR BUILD ET. 3 AY CANLI KULLAN.**

Adım 26 sonunda sistem **tam fonksiyonel**:
- Multi-TF analiz (**15m**, 1H, 4H, 1D, 1W, 1M) — 6 timeframe
- 2-katmanlı Confluence + Setup Quality A/B/C/D
- **Confidence Engine** (kanıt seviyesi göstergesi)
- **Counter-Trend Detector** (aldatıcı setup uyarısı)
- **Trade Quality Filter** (vasat setup'ları otomatik ayıkla)
- Macro entegrasyon + Korelasyon paneli
- SMC (Order Block, FVG, Liquidity Sweep, BOS/CHoCH)
- Aksiyon Özeti + "Hesabı Göster" modal
- **Manual Alert System** (3 aşamalı yaklaşma + pozisyon yardımcısı)
- Heatmap Dashboard + Sol Sembol Paneli
- Risk yönetimi + No-trade zone + Tilt protection
- News Feed (CryptoPanic)
- Cross-Asset Rotation Tracker
- Trade Journal temel + Telegram bildirimleri (basit)

**Bu adımdan sonra ne yapılır:**

1. **3 ay paper trade** — sistemin önerilerini takip et, kâğıda yaz
2. **Hafta 4-12 küçük gerçek pozisyon** — risk %0.5-1
3. **Hafta 12+ normal pozisyon** — risk %2 (default)
4. **Trade Journal'ı manuel doldur** — pattern detection için
5. **Notlar tut:** Hangi özelliği kullanmadın? Hangisi eksik geldi?
6. **6 ay sonra** Future Roadmap'i değerlendir

**6 ay sonra şu sorulara cevap ver:**
- "Backtest motoru gerçekten lazım mı yoksa journal verisi yeterli mi?"
- "Wyckoff phase tespitine ihtiyacım oldu mu?"
- "AI asistan kullanır mıydım?"
- "On-chain modülünü neden eklemedim?"
- "Position management uyarıları işe yaradı mı?"

Cevaplara göre **seçici** olarak ekle. **Hepsini ekleme**.

---

# 🔮 FUTURE ROADMAP — 6 AY SONRA DEĞERLENDİR

⚠️ **Aşağıdaki adımlar şimdi build edilmeyecek.** 6 ay canlı kullanım sonrası **gerçek ihtiyaca göre** seçici olarak eklenecek.

Her özellik için **ön-validasyon kriterleri** ekledim — eğer bu kriterler sağlanmıyorsa o özellik **eklenmemeli**.

---

## Future — Faz 2'nin Kalanı

### Adım 27 (Future): Halving Sayacı + ETF Flow

**Validasyon kriteri:** Macro Context Card'da bu metrikleri **manuel** takip ediyor musun? Düzenli kullanıyorsan ekle.

```
backend/app/services/macro/halving.py:
- BTC halving tarihleri sabit listesi (2024 nisan oldu, sonraki 2028 nisan)
- compute_days_to_next_halving()

backend/app/services/macro/etf.py:
- get_btc_etf_flows() (Coinglass)
- get_eth_etf_flows() (Coinglass)
- detect_anomaly(flows) → büyük net inflow/outflow

Frontend:
- Macro Context Card'a ekle: Halving sayacı
- ETF Flow widget (günlük net)
```

---

### Adım 28 (Future): Otomatik Ekonomik Takvim

**Validasyon kriteri:** Manuel girilen `major_events.json` dosyasını **güncel tutmaktan yoruldun mu?** Yoksa manuel yeterli.

```
backend/app/services/macro/calendar.py:

class ForexFactoryClient:
    async def fetch_weekly_calendar() → list[Event]
    # forexfactory.com scrape (BeautifulSoup)
    # Events filter: high impact, USD/EUR

backend/app/workers/calendar_sync.py (Celery):
@celery_app.task
def sync_economic_calendar():
    # Pazartesi 06:00 UTC
    # forexfactory'den 7 gün al
    # DB'ye yaz (economic_events)

Frontend:
- Settings → "Yaklaşan Olaylar" listesi
- Dashboard'da yakın olay (24h içinde) banner
```

---

### Adım 29 (Future): Scanner Tam + Watchlist Yönetimi

**Validasyon kriteri:** Heatmap zaten 27 sembolü gösteriyor. Ekstra watchlist yönetimine gerçekten ihtiyacın var mı? Kullanmıyorsan **atla**.

```
backend/app/services/scanner.py:
async def scan_watchlist(watchlist_id, min_quality, timeframes)

backend/app/workers/scanner_tasks.py (Celery):
- @celery_app.task scheduled_scan(user_id)

Endpoints:
- GET /api/v1/scanner/active-setups
- POST /api/v1/scanner/run-now
- /api/v1/watchlists/* CRUD
```

---

### Adım 30 (Future): Telegram Bot İleri Komutlar

**Validasyon kriteri:** Adım 25-26'da basit Telegram bildirim var. İleri komut (/btc, /scan, /pause) gerçekten kullanılıyor mu?

```
Bot komutları:
- /status (açık pozisyon + günlük durum)
- /scan (manuel tarama)
- /pause / /resume
- /btc, /eth, /sol vs (anlık özet)
- /help

Smart priority:
- Critical / High / Medium / Low alert tipleri
- Rate limit: aynı sembol+tip 30dk'da 1 kez
```

---

## Future — Faz 3 — Akıllı Öğrenme

### Adım 31 (Future): Trade Journal Full + Pattern Detection

**Validasyon kriteri:** **EN ÖNEMLİ ADIM.** Trade Journal'ı 50+ işlemle doldurduktan sonra eklenmeli. **Mutlaka eklenecek**, sadece zamanı doğru olsun.

```
src/pages/Journal.tsx

3 tab:
1. Açık Pozisyonlar (real-time P/L)
2. Geçmiş (filtreli, sıralı, kategori bazlı)
3. İstatistikler (KPI'lar, equity curve, by quality/TF/symbol/direction/setup_type)

Yeni pozisyon form: 
- Tüm alanlar
- Setup'tan açıldıysa pre-fill (analysis_id + setup_id bağlantı)

Backend:
backend/app/services/journal_service.py:
- create_trade()
- close_trade(exit_price, exit_reason)
- compute_stats(user_id, period) → full stats
- detect_patterns(user_id) → insights

Pattern detection:
- Group by feature combo
- Min 5 örneklem
- Win rate >70% veya <30% → insight

Endpoints: /api/v1/trades/* (CLAUDE.md'deki spec)
```

---

### Adım 32 (Future): Position Monitoring + Management

```
backend/app/workers/trade_monitor.py (Celery):

@celery_app.task
def monitor_open_trades():
    # Her 1 dk
    # Stop'a %1 yakın → uyarı
    # Hedef'e %1 yakın → "kısmi al" önerisi
    # Trend invalidasyonu → "BE çek" önerisi
    # Funding güncel maliyet
    # Trailing stop önerisi (TP1 sonrası)

backend/app/services/position_management.py:
- check_stop_proximity(trade, current_price)
- check_target_proximity(trade, current_price)
- suggest_trailing_stop(trade, current_price, atr)
- suggest_breakeven(trade, current_price)
- suggest_partial_close(trade, target_hit)

Frontend:
- Açık pozisyon kartlarında uyarı badge'leri
- Real-time P/L (WebSocket)
- Aksiyonlar: trailing aktif et, BE çek, partial close
```

---

### Adım 33 (Future): Portfolio Manager

```
backend/app/services/portfolio.py:

def analyze_portfolio(user_id) → PortfolioState
    # Toplam açık risk
    # Sektör exposure (%)
    # Korelasyon-ağırlıklı efektif risk
    # Aynı yöne pozisyon uyarısı
    # Max risk limit kontrolü

def can_open_new_position(user_id, new_position) → (bool, warnings)
    # Toplam risk %15 limit
    # Sektör %50 max
    # Korelasyon kontrolü

Endpoint:
- GET /api/v1/portfolio/state
- POST /api/v1/portfolio/check-new-position

Frontend:
- src/pages/Portfolio.tsx (veya Risk page'in tab'ı)
- Donut chart: sektör dağılımı
- Açık pozisyonlar listesi
- Risk limitleri görsel
```

---

### Adım 34 (Future): Korelasyon + Sentiment Conflict Tam

```
Adım 12'deki korelasyon engine'i derinleştir:

backend/app/services/correlation.py:
- analyze_open_positions_correlation(user_id) → CorrelationRisk
- compute_effective_risk(positions, correlation_matrix)

backend/app/services/sentiment_conflict.py:
- detect_crowd_conflict(direction, futures_data, fear_greed)
- L/S ratio aşırı + sistem aynı yön → "kalabalık"
- Funding aşırı + sistem aynı yön → "squeeze riski"
- F&G ekstrem + sistem aynı yön → "extreme zone"

Setup quality engine'e entegre (otomatik 1 not düşürme).

Yeni pozisyon açarken kontrol → uyarı.
```

---

### Adım 35 (Future): Win Rate by Setup Type Detaylı

```
backend/app/services/journal_service.py'a eklemeler:

def categorize_setup(trade_snapshot) → SetupType
    # Hangi indikatörler bullish/bearish'di?
    # Macro durumu nasıldı?
    # Hangi TF'de açıldı?
    # SMC pattern var mıydı?
    # Sonuç: "EMA50_RSI_bullish_div_4H" gibi tag

def compute_stats_by_setup_type(user_id) → dict
    # Her setup type için win rate
    # Min 5 örneklem
    # Ranking

Frontend:
- Journal stats'a yeni tab
- En iyi setup'lar / en kötü setup'lar
- Otomatik insight'lar
```

---

### Adım 36 (Future): Basit On-Chain (Etherscan)

```
backend/app/data/etherscan.py:
- get_token_transfers(address, contract, since)
- Free API key (kayıt gerekli, ücretsiz)

backend/app/services/onchain.py:
- track_exchange_netflow(symbol="BTC|ETH|USDT")
  # Major exchange wallet'larına in/out
- detect_whale_transfer(threshold_usd=1_000_000)
- get_stablecoin_reserves_trend()

Cron: her 30 dk on-chain data güncelle.

Endpoint: GET /api/v1/onchain/netflow
Endpoint: GET /api/v1/onchain/whale-alerts

Frontend:
- Macro Context Card'a netflow ekle
- "Whale Alert" widget (son 24h büyük transferler)
- Alert: $5M+ transfer için Telegram
```

---

### Adım 37 (Future): Faz 3 Polish + Deploy

```
- Tüm Faz 3 özellikleri Settings'e entegre
- Notification preferences detayı
- Performance optimization
- Load testing
- Production deploy update
```

---

## Future — Faz 4 — İleri Özellikler

⚠️ Bu adımlar **6 ay+ sonra**, ancak **gerçek ihtiyaç doğduğunda** eklenecek. Bazıları belki **hiç eklenmeyecek**.

### Adım 38 (Future): Backtest Engine

**Validasyon kriteri:** 100+ gerçek işlemden sonra Trade Journal verin **canlı edge'ini** sana zaten gösterecek. Backtest gerçekten **fazlalık** olabilir. Yine de istersen ekle.

**⚠️ Önemli uyarı:** Backtest'te %75 win rate çıkarsa, canlıda %50-58 olacak (overfitting + slippage + psikoloji). **İnanma**.

```
backend/app/services/backtest/:

engine.py:
- BacktestEngine
- run(symbol, start_date, end_date, config) → BacktestResult
- Simulated trading (komisyon + funding + slippage)

position_simulator.py:
- VirtualPosition
- mark_to_market()
- check_stop, check_target

stats.py:
- compute_full_stats() → win rate, PF, max DD, Sharpe, Sortino, Calmar
- by_month, by_setup_type, by_macro_regime

Config:
- min_quality
- position_sizing (fixed % veya Kelly)
- 3 yıl geçmiş veri (Binance'tan çek)

backend/app/workers/backtest_tasks.py (Celery):
- Async run, progress reporting
- DB'ye yaz

Endpoints:
- POST /api/v1/backtest/run
- GET /api/v1/backtest/{id}/status
- GET /api/v1/backtest/{id}/results
- GET /api/v1/backtest/runs

Frontend:
- src/pages/Backtest.tsx
- Yeni run formu
- Progress bar
- Sonuç tablosu, equity curve, stats
```

---

### Adım 39 (Future — OPSİYONEL): Wyckoff Schematics

**⚠️ Validasyon kriteri:** Wyckoff phase otomatik tespit etmek **algoritmik olarak çok zor**, false positive riski yüksek. **Manuel olarak grafiğe bakıp Wyckoff yorumu yapmak daha doğru olabilir.** Eklemeden önce dürüst sor: "Bu özelliği gerçekten kullanır mıyım?"

**Önerilen alternatif:** Wyckoff manuel öğren (kitap + YouTube), grafiğe bakarken kafanda uygula. Sistem'e entegre etme.

```
backend/app/services/indicators/wyckoff.py:

def detect_wyckoff_phase(df, lookback=200) → WyckoffPhase
    # Phase A: downtrend bitiyor (PS, SC, AR, ST)
    # Phase B: range içi sıkışma
    # Phase C: Spring (sweep + reversal)
    # Phase D: yükseliş (LPS, SOS, BU)
    # Phase E: markup

Algoritma:
- Range tespit (BB + ATR + ADX düşük)
- Volume divergence
- Spring tespiti (liquidity sweep + bullish engulfing kombinasyonu)
- Climax volume detection

Indicator engine'e entegre.
Confluence trend skoruna Wyckoff bonus +20 ekle.

Frontend:
- Dashboard'da "Wyckoff Phase" badge
- Phase'in açıklaması (tooltip)
```

---

### Adım 40 (Future): AI Assistant (Claude API)

**Validasyon kriteri:** İlk 6 ayda **gerçekten** sisteme bir şey sormak istediğin oldu mu? "BTC niye düştü?" gibi sorular için ChatGPT/Claude.ai zaten yeterli. Entegrasyon gereksiz olabilir. **Sadece çok fayda sağlıyorsa ekle.**

```
backend/app/services/ai_assistant.py:

class AIAssistant:
    async def ask(user_id, question, context_type) → AIResponse
        # Context build:
        # - Mevcut sembolün analizi
        # - Açık pozisyonlar
        # - Son 24h önemli eventler
        # - Genel piyasa durumu
        
        # Anthropic API (claude-sonnet-4-7)
        # System prompt: trading karar destek asistanı
        # Stream response

Endpoint:
- POST /api/v1/ai/chat
- GET /api/v1/ai/conversations
- POST /api/v1/ai/conversation (yeni)

Frontend:
- src/pages/AIAssistant.tsx
- Chat arayüzü
- Stream response
- Bağlam göstergesi (hangi sembol açık, vs.)

Maliyet: kullanıcının API key'ini kendi girmesi (Anthropic Console'dan).
```

---

### Adım 41 (Future): Mobile PWA

```
1. PWA setup:
   - manifest.json
   - service worker
   - Install prompt

2. Mobile responsive (768px ve altı):
   - Sidebar bottom-nav
   - Dashboard kart grid 1 sütun
   - Heatmap responsive
   - Touch gestures (swipe)

3. Push notifications (PWA)

4. Klavye kısayolları (1/2/3/4/5 = TF, B = BTC, vs.)
```

---

### Adım 42 (Future): Setup Type Stats + Pattern Insights

```
Adım 35'te başladık, derinleştir:

- Otomatik insight üretimi
  - "Son 30 işlemde StochRSI > 80'de short açtığında %25 win rate" gibi
- Insight notifications (Telegram)
- "Strategy Suggestions" sayfası
  - "Bu setup tipini deneyin" / "Bu setup'tan kaçının"

Frontend:
- Journal stats sayfasına AI-driven insights bölümü
```

---

### Adım 43 (Future): Final Polish + Production v1.0

```
1. Cross-browser test (Chrome, Safari, Firefox)
2. Mobile test (iOS Safari, Android Chrome)
3. Performance (Lighthouse score >90)
4. Yük testi
5. Documentation güncelle (kullanıcı rehberi)
6. README final
7. Production deploy
8. Backup automasyonu
9. Monitoring (Sentry, Uptime Kuma)
10. v1.0 release notes
```

---

## Geliştirme İpuçları

### Genel
- Her adım tek prompt = tek session
- Adım tamamlanmadan sonrakine geçme
- Her adımdan sonra: commit + manuel test
- CLAUDE.md güncellemeleri yapılırsa not düşülür

### Test
- Backend: pytest + factory_boy + httpx mock
- Frontend: vitest + testing-library
- E2E: playwright (kritik flow)

### Branch Stratejisi
- main: production
- develop: integration
- feature/adim-X-isim: her adım

### Code Review Self-Check
- [ ] Type hints tam mı?
- [ ] Error handling kapsamlı mı?
- [ ] Logging anlamlı mı?
- [ ] Test coverage yeterli mi?
- [ ] Cache stratejisi doğru mu?
- [ ] Security sağlam mı?
- [ ] DB queries indexed mi?
- [ ] Frontend loading/error/empty states var mı?
- [ ] Mobile responsive mi?
- [ ] Tooltip ekledim mi (yeni terim için)?
