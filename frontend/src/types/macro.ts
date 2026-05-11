/**
 * Backend Macro schemaları aynası — Adım 10 / 20.
 *
 * Source of truth: backend/app/schemas/macro.py
 *
 * Trend olmayan alanlar (crypto_caps): CoinGecko free tier'da global history yok,
 * sadece current değerler döner. Frontend bu durumda "trend verisi yok" tooltip
 * gösterir.
 */

export type TrendDirection = "up" | "down" | "flat";

export interface MetricTrend {
  current: number;
  change_24h_pct: number | null;
  change_7d_pct: number | null;
  change_30d_pct: number | null;
  direction_24h: TrendDirection;
  direction_7d: TrendDirection;
  direction_30d: TrendDirection;
}

export interface CryptoCapsSnapshot {
  total: number;
  total2: number;
  total3: number;
  btc_dominance: number;
  eth_dominance: number;
}

export interface FearGreedSnapshot {
  value: number;
  classification: string;
  timestamp: string;
  value_7d_ago: number | null;
  change_7d: number | null;
}

export type MarketRegime =
  | "ALT_BULL"
  | "BTC_BULL"
  | "RISK_OFF"
  | "ALT_SEASON_EARLY"
  | "MIXED";

export interface RegimeResult {
  regime: MarketRegime;
  label: string;
  triggers: Record<string, boolean>;
}

export interface MacroSnapshot {
  crypto_caps: CryptoCapsSnapshot;
  btc_market_cap: MetricTrend;
  eth_btc_ratio: MetricTrend;
  dxy: MetricTrend;
  sp500: MetricTrend;
  nasdaq: MetricTrend;
  vix: MetricTrend;
  us10y: MetricTrend;
  gold: MetricTrend;
  fear_greed: FearGreedSnapshot;
  market_regime: RegimeResult;
  computed_at: string;
}
