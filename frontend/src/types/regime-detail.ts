/**
 * /api/v1/macro/regime-detail response tipi.
 * Backend: backend/app/schemas/regime_detail.py aynası.
 */
import type { MarketRegime } from "@/types/macro";

export interface RegimeMacroSummary {
  btc_trend_7d_pct: number | null;
  eth_btc_change_pct: number | null;
  btc_dominance: number;
  fear_greed_value: number;
  fear_greed_label_tr: string;
  tradfi_signal: "bullish" | "neutral" | "bearish";
}

export interface SetupGradeCounts {
  A: number;
  B: number;
  C: number;
  D: number;
  NO_TRADE: number;
  none: number;
}

export interface SetupDirectionCounts {
  long: number;
  short: number;
  neutral: number;
  none: number;
}

export interface SetupDistribution {
  grade_counts: SetupGradeCounts;
  direction_counts: SetupDirectionCounts;
  total_symbols: number;
}

export interface RecommendationTr {
  summary: string;
  bullets: string[];
}

export interface DetailedAnalysisTr {
  market_state: string;
  system_state: string;
  risk_factors: string[];
  recommendation: RecommendationTr;
}

export interface RegimeDetailResponse {
  regime: MarketRegime;
  regime_label_tr: string;
  reasoning_tr: string;
  macro_summary: RegimeMacroSummary;
  setup_distribution: SetupDistribution;
  warnings_tr: string[];
  strategy_tr: string;
  detailed_analysis_tr: DetailedAnalysisTr;
  computed_at: string;
}
