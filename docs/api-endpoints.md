# MarketLens — API Endpoints (v2)

Base URL: `/api/v1`
Auth: JWT Bearer token

---

## Auth

### `POST /auth/login`
### `POST /auth/refresh`
### `GET /auth/me`

---

## Symbols

### `GET /symbols`
Tüm aktif sembolleri sektör grupları ile döner.

### `GET /symbols/{code}/price`
Anlık fiyat + 24h değişim.

### `GET /symbols/{code}/klines?timeframe=4H&limit=200`
OHLCV mumları.

---

## Analysis

### `POST /analysis/run`

```json
Request: {
  "symbol_code": "SOLUSDT",
  "timeframes": ["1H", "4H", "1D"],
  "modules": ["trend", "momentum", "volume", "volatility", "futures", "macro"]
}

Response: {
  "analysis_id": "uuid",
  "symbol": "SOLUSDT",
  "current_price": 178.50,
  "overall_bias": "long",
  
  "alignment": {
    "score": 72,
    "label": "Strong"
  },
  
  "setup_quality": {
    "grade": "A",
    "score": 88,
    "factors": { ... }
  },
  
  "no_trade_zone": {
    "active": false,
    "reason": null
  },
  
  "market_regime": {
    "code": "ALT_BULL",
    "label": "🟢 Altcoin boğa rejimi",
    "factors": ["BTC.D düşüyor", "TOTAL3 yükseliyor"]
  },
  
  "macro_context": {
    "total": 2.4e12,
    "total_change_24h": 1.8,
    "total3": 0.8e12,
    "total3_change_24h": 2.4,
    "btc_dominance": 54.2,
    "btc_dominance_change_24h": -1.8,
    "eth_dominance": 16.5,
    "dxy": 103.2,
    "dxy_change_24h": -0.1,
    "sp500": 5180,
    "vix": 14.2,
    "fear_greed": 68,
    "eth_btc_ratio": 0.054,
    "eth_btc_change_7d": 3.1
  },
  
  "timeframes": {
    "1H": { /* TF detayı */ },
    "4H": { 
      "local_score": 65,
      "macro_modifier": 18,
      "final_score": 83,
      "trend_score": 75,
      "momentum_score": 60,
      "volume_score": 55,
      "volatility_score": 30,
      "futures_score": 80,
      "indicators": { /* tüm değerler */ }
    },
    "1D": { ... }
  },
  
  "scenarios": {
    "long": {
      "direction": "long",
      "probability": 78,
      "entry_zone": { "low": 178.20, "high": 178.80 },
      "targets": [
        {"level": 1, "price": 184.50, "pct": 40, "rationale": "EMA 50D + Fib 0.382"},
        {"level": 2, "price": 189.00, "pct": 35, "rationale": "Önceki swing high"},
        {"level": 3, "price": 196.00, "pct": 25, "rationale": "Fib ext 1.618"}
      ],
      "stop_loss": 174.50,
      "invalidation": "EMA 100 4H altında 4H kapanış",
      "risk_reward": 3.4,
      "atr_distance": 1.6,
      "support_levels": [
        {"price": 176.20, "rationale": "VWAP + Fib 0.618", "is_golden": true},
        {"price": 174.50, "rationale": "EMA 100 4H", "is_golden": false}
      ],
      "resistance_levels": [
        {"price": 184.50, "rationale": "EMA 50 + Fib 0.382", "is_golden": true},
        {"price": 189.00, "rationale": "swing high", "is_golden": false}
      ]
    },
    "short": { ... }
  },
  
  "futures_data": {
    "funding_rate_current": 0.0124,
    "funding_rate_24h_avg": 0.011,
    "open_interest_change_24h": 8.2,
    "long_short_ratio": 2.14
  },
  
  "correlations": {
    "btc": 0.91,
    "eth": 0.84,
    "total3": 0.78,
    "dxy": -0.42
  },
  
  "action_summary": {
    "recommendation": "🟢 LONG ÖNERİLİYOR",
    "recommendation_color": "long",
    "summary_text": "4H'de bullish yapı korunuyor. Macro destekleyici, alt rotasyon başlamış.",
    "warnings": [
      "L/S Ratio 2.14 — kalabalık long tarafında",
      "1H StochRSI aşırı alım → kısa pullback olabilir",
      "US CPI verisi 18 saat sonra → volatilite artabilir"
    ],
    "invalidation_criteria": [
      "4H kapanış 174.50 altında → long iptal",
      "176.20 altı + funding düşüşü → short fırsat",
      "BTC.D %57.5 üstü → macro tersine"
    ],
    "position_recommendation": {
      "direction": "long",
      "entry_low": 178.20,
      "entry_high": 178.80,
      "targets_with_pct": [
        {"price": 184.50, "pct": 40},
        {"price": 189.00, "pct": 35},
        {"price": 196.00, "pct": 25}
      ],
      "stop_loss": 174.50,
      "position_size_usd": 3000,
      "leverage": 5,
      "margin_used": 600,
      "risk_amount_usd": 60,
      "risk_pct": 2.0,
      "adjusted_risk_pct": 2.0,
      "volatility_factor": 1.0,
      "risk_reward": 3.4
    },
    "calculation_details": {
      "target_1": [
        {"indicator": "Fib 0.382", "value": 184.30},
        {"indicator": "EMA 50 günlük", "value": 184.80},
        {"indicator": "Önceki swing high", "value": 185.00},
        {"indicator": "Volume Profile POC üstü", "value": 184.20}
      ]
    }
  }
}
```

### `GET /analysis/{analysis_id}`
### `GET /analysis/history?symbol_code=SOLUSDT&limit=20`

---

## Heatmap

### `GET /heatmap`

```json
Response: {
  "updated_at": "2026-05-07T12:00:00Z",
  "symbols": [
    {
      "code": "BTCUSDT",
      "display_name": "Bitcoin",
      "sector": "L1",
      "price": 67432.50,
      "change_24h": 1.88,
      "scores": {
        "1H": { "final": 65, "color": "green" },
        "4H": { "final": 72, "color": "green" },
        "1D": { "final": 80, "color": "green" }
      },
      "setup_quality": "B",
      "volatility_alert": null
    },
    ...
  ]
}
```

---

## Macro

### `GET /macro/snapshot`
Tüm makro metrikler tek call'da.

### `GET /macro/regime`
Mevcut market regime + sebep.

### `GET /macro/correlations?symbol=SOLUSDT`
Sembol vs (BTC, ETH, TOTAL3, DXY, vs.).

### `GET /macro/rotation` (Faz 2)
Sektör rotasyon performansı.

### `GET /macro/etf-flows` (Faz 2)
BTC + ETH ETF net flow.

### `GET /macro/halving` (Faz 2)
Sonraki BTC halving sayacı.

---

## Liquidation (Faz 2)

### `GET /liquidation/heatmap?symbol_code=BTCUSDT&timeframe=24h`

### `GET /liquidation/clusters?symbol_code=BTCUSDT`

---

## Order Book

### `GET /orderbook/heatmap?symbol_code=BTCUSDT&depth=1000`

---

## Scanner

### `GET /scanner/active-setups?quality=A,B&limit=20`
### `POST /scanner/run-now`
### `GET /scanner/status/{scan_id}`

---

## Watchlists

### `GET /watchlists`
### `POST /watchlists`
### `PATCH /watchlists/{id}`
### `DELETE /watchlists/{id}`

---

## Trades (Journal)

### `GET /trades?status=open&limit=20`
### `GET /trades/{id}`
### `POST /trades`
### `PATCH /trades/{id}/close`
### `PATCH /trades/{id}/trailing-stop`
### `PATCH /trades/{id}/breakeven`
### `POST /trades/{id}/partial-close`
### `GET /trades/stats?period=30d`

```json
Response: {
  "period": "30d",
  "general": {
    "total_trades": 24,
    "win_rate": 58.3,
    "profit_factor": 3.36,
    "max_drawdown_pct": 8.4,
    "sharpe_ratio": 1.82,
    "sortino_ratio": 2.4
  },
  "by_quality": {
    "A": { "trades": 8, "win_rate": 75.0, "avg_r": 2.1 },
    "B": { "trades": 12, "win_rate": 58.3, "avg_r": 1.4 }
  },
  "by_timeframe": { "4H": {...}, "1D": {...} },
  "by_session": {
    "asia": { "trades": 4, "win_rate": 25.0 },
    "europe": { "trades": 10, "win_rate": 60.0 },
    "us": { "trades": 10, "win_rate": 70.0 }
  },
  "by_macro_regime": {
    "ALT_BULL": { "trades": 8, "win_rate": 75.0 },
    "RISK_OFF": { "trades": 4, "win_rate": 25.0 }
  },
  "by_setup_type": { ... },
  "patterns_detected": [
    "StochRSI aşırı alımda short açtığında %72 kayıp (n=11)",
    "ALT_BULL rejiminde A-setup long: %78 win rate (n=8)"
  ]
}
```

---

## Risk

### `POST /risk/calculate-position`

```json
Request: {
  "entry_price": 178.50,
  "stop_loss": 174.50,
  "direction": "long",
  "symbol_code": "SOLUSDT"
}

Response: {
  "account_balance": 3000,
  "base_risk_pct": 2.0,
  "volatility_factor": 1.0,
  "adjusted_risk_pct": 2.0,
  "risk_amount_usd": 60,
  "stop_distance_pct": 2.24,
  "recommended_position_size_usd": 2678,
  "recommended_leverage": 1,
  "min_required_leverage": 1,
  "liquidation_price_at_5x": 159.40,
  "liquidation_price_at_10x": 169.05,
  "estimated_funding_24h": 0.30,
  "estimated_funding_72h": 0.89,
  "estimated_funding_1w": 2.08,
  "warnings": []
}
```

### `GET /risk/daily-status`
### `GET /risk/no-trade-status`
### `POST /risk/pause`
### `POST /risk/resume`

---

## Portfolio (Faz 3)

### `GET /portfolio/state`

```json
Response: {
  "open_positions_count": 3,
  "total_open_risk_usd": 270,
  "total_open_risk_pct": 9.0,
  "max_allowed_pct": 15.0,
  "sector_exposure": {
    "L1": 0.6,
    "DeFi": 0.2,
    "Meme": 0.2
  },
  "correlation_risk": {
    "weighted_correlation": 0.82,
    "warning": "Pozisyonların yüksek korelasyonu. Gerçek riskin nominal'den 1.5x büyük."
  }
}
```

### `POST /portfolio/check-new-position`

---

## Alerts

### `GET /alerts?delivered=false&priority=high&limit=20`
### `POST /alerts/price`
### `DELETE /alerts/{id}`
### `POST /alerts/test-telegram`

---

## News (Faz 2)

### `GET /news/feed?symbol=BTC&limit=20`
### `GET /news/critical?since=24h`

---

## On-Chain (Faz 3)

### `GET /onchain/netflow?symbol=BTC&period=24h`
### `GET /onchain/whale-alerts?since=24h&min_usd=1000000`

---

## Settings

### `GET /settings`
### `PATCH /settings`
### `POST /settings/telegram-connect`
### `POST /settings/anthropic-key` (Faz 4)

---

## Backtest (Faz 4)

### `POST /backtest/run`
### `GET /backtest/{run_id}/status`
### `GET /backtest/{run_id}/results`
### `GET /backtest/runs`

---

## AI Assistant (Faz 4)

### `POST /ai/chat`

```json
Request: {
  "conversation_id": "uuid (optional)",
  "message": "BTC pozisyonumu kapatayım mı?",
  "context_type": "current_position"
}

Response: { /* streaming */ }
```

### `GET /ai/conversations`
### `GET /ai/conversations/{id}`
### `DELETE /ai/conversations/{id}`

---

## WebSocket

### `WS /ws`

Subscribe channels:
```json
{ "type": "subscribe", "channel": "price", "symbol": "BTCUSDT" }
{ "type": "subscribe", "channel": "alerts" }
{ "type": "subscribe", "channel": "trade_updates" }
{ "type": "subscribe", "channel": "heatmap" }
{ "type": "subscribe", "channel": "macro" }
```

Server events:
```json
{ "type": "price_update", "symbol": "...", "price": ..., "timestamp": ... }
{ "type": "alert", "alert_id": "...", "priority": "high", "message": "..." }
{ "type": "setup_found", "setup": { ... } }
{ "type": "volatility_alert", "symbol": "...", "magnitude": ..., "timeframe": "..." }
{ "type": "trade_warning", "trade_id": "...", "warning_type": "stop_near", ... }
{ "type": "macro_update", "regime": "ALT_BULL", ... }
{ "type": "heatmap_update", "symbol_changes": [...] }
```

---

## Error Format

```json
HTTP 4xx/5xx:
{
  "error": "validation_error",
  "message": "İnsan okunabilir mesaj",
  "details": { ... },
  "request_id": "uuid"
}
```

## Rate Limiting

- Auth: 5/dakika/IP
- Analysis: 30/dakika/user
- Scanner manual run: 5/saat/user
- AI chat: 20/dakika/user (Faz 4)
- Diğer: 60/dakika/user
