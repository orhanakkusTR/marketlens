# MarketLens — Database Schema (v2)

PostgreSQL 16. Tüm tablolar `marketlens` schema'sında.

---

## users

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(100),
    telegram_chat_id VARCHAR(50),
    telegram_username VARCHAR(50),
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## symbols

```sql
CREATE TABLE symbols (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(20) UNIQUE NOT NULL,    -- "BTCUSDT", "XAUUSD"
    display_name    VARCHAR(50) NOT NULL,
    asset_type      VARCHAR(20) NOT NULL,           -- "crypto", "commodity"
    sector          VARCHAR(20),                    -- "L1", "L2", "DeFi", "Meme", "Other", "Commodity"
    quote_currency  VARCHAR(10) NOT NULL,
    exchange        VARCHAR(20) NOT NULL,
    has_futures     BOOLEAN DEFAULT false,
    is_active       BOOLEAN DEFAULT true,
    sort_order      INTEGER DEFAULT 0,
    metadata        JSONB,                          -- logo_url, decimals, vb.
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_symbols_active ON symbols(is_active, sort_order);
CREATE INDEX idx_symbols_sector ON symbols(sector);
```

---

## analyses

```sql
CREATE TABLE analyses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    symbol_id       INTEGER REFERENCES symbols(id),
    triggered_by    VARCHAR(20) NOT NULL,           -- "manual", "scanner", "scheduled", "volatility_alert"
    current_price   NUMERIC(20, 8) NOT NULL,
    
    -- Confluence
    overall_bias    VARCHAR(20),                    -- "long", "short", "neutral"
    alignment_score NUMERIC(5, 2),
    alignment_label VARCHAR(20),                    -- "Strong", "Aligned", "Conflicted"
    
    -- Setup quality
    setup_quality   CHAR(1),                        -- A/B/C/D
    setup_score     NUMERIC(5, 2),
    
    -- Macro context
    macro_regime    VARCHAR(30),                    -- "ALT_BULL", "BTC_BULL", "RISK_OFF", etc.
    macro_modifier  NUMERIC(5, 2),                  -- -25 to +25
    
    -- No-trade zone
    no_trade_active BOOLEAN DEFAULT false,
    no_trade_reason VARCHAR(255),
    
    -- Time of day
    market_session  VARCHAR(20),                    -- "asia", "europe", "us"
    
    raw_data        JSONB NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_analyses_user_symbol ON analyses(user_id, symbol_id, created_at DESC);
CREATE INDEX idx_analyses_quality ON analyses(setup_quality) WHERE setup_quality IN ('A', 'B');
CREATE INDEX idx_analyses_regime ON analyses(macro_regime, created_at DESC);
```

---

## confluence_scores

```sql
CREATE TABLE confluence_scores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id     UUID REFERENCES analyses(id) ON DELETE CASCADE,
    timeframe       VARCHAR(10) NOT NULL,           -- "1H", "4H", "1D", "1W", "1M"
    
    -- Local layer
    local_score     NUMERIC(5, 2) NOT NULL,
    trend_score     NUMERIC(5, 2) NOT NULL,
    momentum_score  NUMERIC(5, 2) NOT NULL,
    volume_score    NUMERIC(5, 2) NOT NULL,
    volatility_score NUMERIC(5, 2) NOT NULL,
    futures_score   NUMERIC(5, 2),
    
    -- Macro layer
    macro_modifier  NUMERIC(5, 2),
    
    -- Final
    final_score     NUMERIC(5, 2) NOT NULL,
    
    indicators      JSONB NOT NULL,                 -- detaylı indikatör değerleri
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_confluence_analysis ON confluence_scores(analysis_id);
```

---

## scenarios

```sql
CREATE TABLE scenarios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id     UUID REFERENCES analyses(id) ON DELETE CASCADE,
    direction       VARCHAR(10) NOT NULL,
    probability     NUMERIC(5, 2) NOT NULL,
    
    entry_low       NUMERIC(20, 8) NOT NULL,
    entry_high      NUMERIC(20, 8) NOT NULL,
    
    target_1        NUMERIC(20, 8) NOT NULL,
    target_1_pct    NUMERIC(5, 2) DEFAULT 40,       -- pozisyonun %
    target_1_rationale VARCHAR(255),
    target_2        NUMERIC(20, 8),
    target_2_pct    NUMERIC(5, 2) DEFAULT 35,
    target_2_rationale VARCHAR(255),
    target_3        NUMERIC(20, 8),
    target_3_pct    NUMERIC(5, 2) DEFAULT 25,
    target_3_rationale VARCHAR(255),
    
    stop_loss       NUMERIC(20, 8) NOT NULL,
    invalidation_note VARCHAR(255),
    
    risk_reward     NUMERIC(5, 2),
    atr_distance    NUMERIC(20, 8),
    
    -- Support/Resistance levels (JSON array)
    support_levels  JSONB,
    resistance_levels JSONB,
    
    -- Action summary text (Türkçe)
    summary_text    TEXT,
    warnings        JSONB,                          -- liste of warning objects
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scenarios_analysis ON scenarios(analysis_id);
```

---

## setups

```sql
CREATE TABLE setups (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    symbol_id       INTEGER REFERENCES symbols(id),
    analysis_id     UUID REFERENCES analyses(id),
    
    direction       VARCHAR(10) NOT NULL,
    timeframe       VARCHAR(10) NOT NULL,
    quality         CHAR(1) NOT NULL,
    confluence      NUMERIC(5, 2) NOT NULL,
    macro_regime    VARCHAR(30),
    risk_reward     NUMERIC(5, 2),
    
    setup_type      VARCHAR(50),                    -- categorized: "EMA50_RSI_bullish_div"
    
    status          VARCHAR(20) DEFAULT 'active',   -- "active", "expired", "triggered", "invalidated"
    expires_at      TIMESTAMPTZ,
    notified        BOOLEAN DEFAULT false,
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_setups_active ON setups(user_id, status, created_at DESC);
CREATE INDEX idx_setups_quality ON setups(quality) WHERE status = 'active';
CREATE INDEX idx_setups_type ON setups(setup_type);
```

---

## trades

```sql
CREATE TABLE trades (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    symbol_id       INTEGER REFERENCES symbols(id),
    setup_id        UUID REFERENCES setups(id),
    analysis_id     UUID REFERENCES analyses(id),
    
    direction       VARCHAR(10) NOT NULL,
    
    -- Giriş
    entry_price     NUMERIC(20, 8) NOT NULL,
    entry_time      TIMESTAMPTZ NOT NULL,
    position_size_usd NUMERIC(20, 2) NOT NULL,
    leverage        INTEGER NOT NULL,
    margin_used     NUMERIC(20, 2) NOT NULL,
    
    -- Plan
    planned_stop    NUMERIC(20, 8) NOT NULL,
    planned_target1 NUMERIC(20, 8),
    planned_target2 NUMERIC(20, 8),
    planned_target3 NUMERIC(20, 8),
    
    -- Çıkış
    exit_price      NUMERIC(20, 8),
    exit_time       TIMESTAMPTZ,
    exit_reason     VARCHAR(50),                    -- "stop", "target1/2/3", "manual", "trailing", "breakeven"
    
    -- Sonuç
    pnl_usd         NUMERIC(20, 2),
    pnl_pct         NUMERIC(7, 3),
    r_multiple      NUMERIC(5, 2),
    funding_paid    NUMERIC(20, 2) DEFAULT 0,
    fees_paid       NUMERIC(20, 2) DEFAULT 0,
    
    -- Meta
    setup_quality_at_entry CHAR(1),
    macro_regime_at_entry VARCHAR(30),
    timeframe       VARCHAR(10),
    market_session  VARCHAR(20),                    -- "asia", "europe", "us"
    setup_type      VARCHAR(50),
    user_note       TEXT,
    tags            VARCHAR(50)[],
    
    -- Position management
    trailing_stop_active BOOLEAN DEFAULT false,
    breakeven_set   BOOLEAN DEFAULT false,
    partial_closes  JSONB,                          -- liste of {price, qty, time}
    
    status          VARCHAR(20) DEFAULT 'open',
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trades_user_status ON trades(user_id, status, entry_time DESC);
CREATE INDEX idx_trades_closed ON trades(user_id, exit_time DESC) WHERE status = 'closed';
CREATE INDEX idx_trades_setup_type ON trades(setup_type) WHERE status = 'closed';
CREATE INDEX idx_trades_session ON trades(market_session) WHERE status = 'closed';
```

---

## alerts

```sql
CREATE TABLE alerts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    symbol_id       INTEGER REFERENCES symbols(id),
    
    alert_type      VARCHAR(40) NOT NULL,
    -- "setup_found", "price_target", "stop_warning", "target_warning",
    -- "funding_extreme", "no_trade_zone_start", "volatility_alert",
    -- "critical_news", "whale_alert", "sector_rotation"
    
    priority        VARCHAR(20) NOT NULL,           -- "critical", "high", "medium", "low"
    trigger_condition JSONB NOT NULL,
    message         TEXT NOT NULL,
    
    channel         VARCHAR(20) NOT NULL,           -- "telegram", "in_app"
    delivered       BOOLEAN DEFAULT false,
    delivered_at    TIMESTAMPTZ,
    
    related_setup_id UUID REFERENCES setups(id),
    related_trade_id UUID REFERENCES trades(id),
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alerts_user_undelivered ON alerts(user_id, delivered, created_at DESC);
CREATE INDEX idx_alerts_priority ON alerts(priority, created_at DESC);
```

---

## user_settings

```sql
CREATE TABLE user_settings (
    user_id         UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    
    -- Risk yönetimi
    account_balance     NUMERIC(20, 2) DEFAULT 3000,
    risk_per_trade_pct  NUMERIC(4, 2) DEFAULT 2.0,
    max_leverage        INTEGER DEFAULT 10,
    daily_max_trades    INTEGER DEFAULT 5,
    daily_max_risk_pct  NUMERIC(5, 2) DEFAULT 4.0,
    auto_pause_after_losses INTEGER DEFAULT 3,
    
    -- Akıllı azaltma (smart_reduction)
    smart_reduction_enabled BOOLEAN DEFAULT true,
    risk_after_2_losses_pct NUMERIC(4, 2) DEFAULT 1.5,
    risk_after_3_losses_pct NUMERIC(4, 2) DEFAULT 1.0,
    
    -- Volatility-adjusted
    volatility_adjustment_enabled BOOLEAN DEFAULT true,
    
    -- Tarama
    scanner_enabled     BOOLEAN DEFAULT true,
    scanner_interval_min INTEGER DEFAULT 15,
    scanner_min_quality CHAR(1) DEFAULT 'B',
    
    -- Volatility Alert eşikleri
    volatility_alert_5m_pct  NUMERIC(4, 2) DEFAULT 2.0,
    volatility_alert_1h_pct  NUMERIC(4, 2) DEFAULT 4.0,
    volatility_alert_4h_pct  NUMERIC(4, 2) DEFAULT 7.0,
    
    -- Telegram
    telegram_alerts_enabled BOOLEAN DEFAULT true,
    alert_setup_found   BOOLEAN DEFAULT true,
    alert_volatility    BOOLEAN DEFAULT true,
    alert_critical_news BOOLEAN DEFAULT true,
    alert_stop_warn_pct NUMERIC(4, 2) DEFAULT 1.0,
    alert_target_warn_pct NUMERIC(4, 2) DEFAULT 1.0,
    alert_funding_threshold NUMERIC(6, 4) DEFAULT 0.0500,
    alert_whale_threshold_usd NUMERIC(20, 2) DEFAULT 5000000,
    
    -- No-trade zone
    no_trade_macro_events BOOLEAN DEFAULT true,
    no_trade_weekly_close BOOLEAN DEFAULT true,
    no_trade_high_volatility BOOLEAN DEFAULT true,
    no_trade_asian_session BOOLEAN DEFAULT false,    -- opsiyonel
    
    -- MA strategy
    auto_ma_selection BOOLEAN DEFAULT true,         -- otomatik EMA/SMA
    
    -- Default UI
    default_timeframes  VARCHAR(10)[] DEFAULT ARRAY['4H', '1D'],
    default_modules     VARCHAR(20)[] DEFAULT ARRAY['trend', 'momentum', 'futures'],
    theme               VARCHAR(20) DEFAULT 'dark',
    sidebar_collapsed   BOOLEAN DEFAULT false,
    
    -- AI Assistant (Faz 4)
    anthropic_api_key   VARCHAR(255),               -- şifrelenmiş
    
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## watchlists

```sql
CREATE TABLE watchlists (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(50) NOT NULL,
    is_default      BOOLEAN DEFAULT false,
    is_favorite     BOOLEAN DEFAULT false,          -- ⭐ filter için
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE watchlist_symbols (
    watchlist_id    UUID REFERENCES watchlists(id) ON DELETE CASCADE,
    symbol_id       INTEGER REFERENCES symbols(id),
    sort_order      INTEGER DEFAULT 0,
    PRIMARY KEY (watchlist_id, symbol_id)
);
```

---

## daily_risk_tracker

```sql
CREATE TABLE daily_risk_tracker (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    
    trades_count    INTEGER DEFAULT 0,
    risk_used_pct   NUMERIC(5, 2) DEFAULT 0,
    consecutive_losses INTEGER DEFAULT 0,
    
    -- Smart reduction state
    current_risk_pct NUMERIC(4, 2),                 -- aktif risk %
    risk_reduction_until TIMESTAMPTZ,               -- ne zamana kadar azaltılmış
    
    is_paused       BOOLEAN DEFAULT false,
    pause_reason    VARCHAR(100),
    paused_at       TIMESTAMPTZ,
    
    UNIQUE (user_id, date)
);
```

---

## price_cache

```sql
CREATE TABLE price_cache (
    id              BIGSERIAL PRIMARY KEY,
    symbol_id       INTEGER REFERENCES symbols(id),
    timeframe       VARCHAR(10) NOT NULL,
    open_time       TIMESTAMPTZ NOT NULL,
    open_price      NUMERIC(20, 8) NOT NULL,
    high_price      NUMERIC(20, 8) NOT NULL,
    low_price       NUMERIC(20, 8) NOT NULL,
    close_price     NUMERIC(20, 8) NOT NULL,
    volume          NUMERIC(30, 8) NOT NULL,
    quote_volume    NUMERIC(30, 8),
    trade_count     INTEGER,
    
    UNIQUE (symbol_id, timeframe, open_time)
);

CREATE INDEX idx_price_cache_lookup ON price_cache(symbol_id, timeframe, open_time DESC);
```

---

## correlations

```sql
CREATE TABLE correlations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol_a_id     INTEGER REFERENCES symbols(id),
    symbol_b_code   VARCHAR(20) NOT NULL,           -- "BTC", "ETH", "TOTAL3", "DXY", "SP500"
    period_days     INTEGER DEFAULT 30,
    timeframe       VARCHAR(10) DEFAULT '4H',
    correlation     NUMERIC(5, 3) NOT NULL,         -- -1.000 to +1.000
    computed_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_correlations_lookup ON correlations(symbol_a_id, symbol_b_code, computed_at DESC);
```

---

## macro_metrics

```sql
CREATE TABLE macro_metrics (
    id              BIGSERIAL PRIMARY KEY,
    metric_code     VARCHAR(30) NOT NULL,           -- "TOTAL", "TOTAL2", "TOTAL3", "BTC.D", "ETH.D", "DXY", "SP500", "VIX", "US10Y", "ETH_BTC"
    timestamp       TIMESTAMPTZ NOT NULL,
    value           NUMERIC(30, 8) NOT NULL,
    
    UNIQUE (metric_code, timestamp)
);

CREATE INDEX idx_macro_metrics_lookup ON macro_metrics(metric_code, timestamp DESC);
```

---

## economic_events (Faz 2)

```sql
CREATE TABLE economic_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_time      TIMESTAMPTZ NOT NULL,
    name            VARCHAR(255) NOT NULL,
    country         VARCHAR(50),
    currency        VARCHAR(10),
    impact          VARCHAR(20),                    -- "high", "medium", "low"
    forecast        VARCHAR(50),
    previous        VARCHAR(50),
    actual          VARCHAR(50),
    source          VARCHAR(50) DEFAULT 'forexfactory',
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (event_time, name, currency)
);

CREATE INDEX idx_events_upcoming ON economic_events(event_time) WHERE event_time > NOW();
CREATE INDEX idx_events_high_impact ON economic_events(event_time) WHERE impact = 'high';
```

---

## news_items (Faz 2)

```sql
CREATE TABLE news_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source          VARCHAR(50) NOT NULL,           -- "cryptopanic"
    external_id     VARCHAR(100),
    title           VARCHAR(500) NOT NULL,
    url             VARCHAR(500),
    published_at    TIMESTAMPTZ NOT NULL,
    sentiment       VARCHAR(20),                    -- "positive", "negative", "neutral"
    impact          VARCHAR(20),                    -- "high", "medium", "low"
    related_symbols VARCHAR(20)[],                  -- ["BTC", "ETH"]
    is_critical     BOOLEAN DEFAULT false,
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source, external_id)
);

CREATE INDEX idx_news_recent ON news_items(published_at DESC);
CREATE INDEX idx_news_critical ON news_items(is_critical, published_at DESC);
```

---

## onchain_events (Faz 3)

```sql
CREATE TABLE onchain_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type      VARCHAR(30) NOT NULL,           -- "whale_transfer", "exchange_inflow", "exchange_outflow"
    symbol          VARCHAR(20) NOT NULL,
    amount_token    NUMERIC(30, 8),
    amount_usd      NUMERIC(20, 2),
    from_address    VARCHAR(100),
    to_address      VARCHAR(100),
    from_label      VARCHAR(100),                   -- "Binance", "Unknown Whale", etc.
    to_label        VARCHAR(100),
    tx_hash         VARCHAR(100),
    occurred_at     TIMESTAMPTZ NOT NULL,
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_onchain_recent ON onchain_events(occurred_at DESC);
CREATE INDEX idx_onchain_large ON onchain_events(amount_usd) WHERE amount_usd >= 1000000;
```

---

## backtest_runs (Faz 4)

```sql
CREATE TABLE backtest_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    symbol_id       INTEGER REFERENCES symbols(id),
    
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    timeframe       VARCHAR(10) NOT NULL,
    
    config          JSONB NOT NULL,
    
    -- Sonuçlar
    total_trades    INTEGER,
    win_rate        NUMERIC(5, 2),
    profit_factor   NUMERIC(8, 3),
    max_drawdown_pct NUMERIC(5, 2),
    sharpe_ratio    NUMERIC(6, 3),
    sortino_ratio   NUMERIC(6, 3),
    calmar_ratio    NUMERIC(6, 3),
    total_return_pct NUMERIC(8, 3),
    
    equity_curve    JSONB,
    trade_log       JSONB,
    stats_by_quality JSONB,
    stats_by_session JSONB,
    stats_by_regime JSONB,
    
    started_at      TIMESTAMPTZ NOT NULL,
    completed_at    TIMESTAMPTZ,
    status          VARCHAR(20) DEFAULT 'running',
    progress_pct    NUMERIC(5, 2) DEFAULT 0,
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## ai_conversations (Faz 4)

```sql
CREATE TABLE ai_conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    title           VARCHAR(255),
    context_symbol_id INTEGER REFERENCES symbols(id),
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ai_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES ai_conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,           -- "user", "assistant", "system"
    content         TEXT NOT NULL,
    context_data    JSONB,                          -- snapshot at message time
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_messages_conv ON ai_messages(conversation_id, created_at);
```

---

## Migration Stratejisi

Alembic. İlk migration tüm tabloları + extension'ları oluşturur:

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS marketlens;
```

Sonraki migration'lar incremental.

## Backup Stratejisi

- DigitalOcean Managed PostgreSQL → günlük snapshot
- Self-hosted: `pg_dump` cron, S3 (DO Spaces) push
- En azından 30 günlük tut
- Trade journal kritik — ayrı yedekleme önerilir
