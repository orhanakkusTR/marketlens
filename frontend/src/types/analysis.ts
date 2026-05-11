/**
 * Backend /analysis/full/{sym}/{tf} response — full schema aynası (Adım 17 + 21).
 *
 * Backend source: backend/app/schemas/analysis.py + sub-schemas:
 *  - indicators.py, confluence.py, setup_quality.py, scenario.py,
 *    no_trade_zone.py, risk.py, correlation.py, macro.py
 */
import type { Direction, GradeLetter } from "@/types/api";
import type { MacroSnapshot } from "@/types/macro";

export type Timeframe = "15m" | "1H" | "4H" | "1D" | "1W" | "1M";
export type SetupGrade = GradeLetter; // alias — backend "A"|"B"|"C"|"D"|"NO_TRADE"
export type ConfidenceLevel =
  | "VERY_LOW"
  | "LOW"
  | "MEDIUM"
  | "HIGH"
  | "VERY_HIGH";
export type CounterTrendSeverity = "low" | "medium" | "high";
export type TradeQualityVerdict = "EXCELLENT" | "GOOD" | "WEAK" | "AVOID";
export type NoTradeSeverity = "info" | "warning" | "blocking";

// ─── Setup Quality sub-types ───

export interface SetupFactor {
  name: string;
  passed: boolean;
  points: number;
  note: string | null;
}

export interface ConfidenceResult {
  level: ConfidenceLevel;
  label: string;
  trade_count: number;
  actual_win_rate: number | null;
  advice: string;
  setup_signature: string;
}

export interface CounterTrendWarning {
  type: string;
  severity: CounterTrendSeverity;
  message: string;
  advice: string | null;
}

export interface TradeQualityFactor {
  name: string;
  passed: boolean;
  value: string | null;
  note: string;
}

export interface TradeQualityResult {
  score: number; // 0..5
  verdict: TradeQualityVerdict;
  quality_modifier: number;
  factors: TradeQualityFactor[];
}

// ─── No-Trade Zone ───

export interface NoTradeZone {
  type: string;
  severity: NoTradeSeverity;
  message: string;
  advice: string | null;
  metadata: Record<string, unknown>;
}

export interface NoTradeSeveritySummary {
  info: number;
  warning: number;
  blocking: number;
}

export interface NoTradeZoneResult {
  symbol: string;
  timeframe: string;
  is_blocking: boolean;
  has_warning: boolean;
  severity_summary: NoTradeSeveritySummary;
  zones: NoTradeZone[];
  computed_at: string;
  now_utc: string;
}

// ─── Scenario ───

export interface ScenarioEntry {
  low: number;
  mid: number;
  high: number;
  width_atr: number;
}

export interface ScenarioStop {
  price: number;
  source: string;
  distance_atr: number;
  distance_pct: number;
  reasoning: string;
}

export interface ScenarioTarget {
  price: number;
  source: string;
  distance_atr: number;
  distance_pct: number;
  rr: number;
  reasoning: string;
}

export interface ScenarioResult {
  symbol: string;
  timeframe: string;
  direction: Direction;
  entry: ScenarioEntry;
  stop: ScenarioStop;
  targets: ScenarioTarget[];
  rr_weighted: number;
  final_confluence: number;
  reasoning: string;
  computed_at: string;
}

// ─── Setup Quality Result ───

export interface SetupQualityResult {
  symbol: string;
  timeframe: string;
  direction: Direction;
  final_score: number;
  raw_score: number;
  base_grade: SetupGrade;
  grade: SetupGrade;
  factors: SetupFactor[];
  grade_modifiers: Record<string, number>;
  confidence: ConfidenceResult;
  counter_trend_warnings: CounterTrendWarning[];
  trade_quality: TradeQualityResult;
  no_trade_zones: NoTradeZoneResult;
  scenario: ScenarioResult | null;
  computed_at: string;
}

// ─── Confluence ───

export interface FinalConfluenceResult {
  symbol: string;
  timeframe: string;
  symbol_type: string;
  local_score: number;
  macro_modifier: number;
  final_score: number;
  label: string;
  direction: Direction;
  components: Record<string, number>;
  macro_breakdown: Record<string, number | null>;
  weights_applied: Record<string, number>;
  market_regime: string | null;
  computed_at: string;
}

// ─── Multi-TF Alignment ───

export interface AlignmentTimeframe {
  timeframe: string;
  final_score: number;
  label: string;
  direction: string;
}

export interface AlignmentResult {
  symbol: string;
  alignment_score: number;
  label: string;
  consistent_direction: string | null;
  by_timeframe: AlignmentTimeframe[];
  weights: Record<string, number>;
  computed_at: string;
}

// ─── Indicators ───

export interface MovingAverage {
  period: number;
  type: string;
  value: number;
  distance_pct: number;
}

export interface TrendMA {
  timeframe: string;
  price: number;
  moving_averages: MovingAverage[];
  alignment: string;
}

export interface IchimokuData {
  tenkan: number | null;
  kijun: number | null;
  senkou_a: number | null;
  senkou_b: number | null;
  chikou: number | null;
  cloud_state: string;
  tk_cross: string;
}

export interface Swing {
  index: number;
  timestamp_ms: number;
  price: number;
  kind: string;
}

export interface MarketStructure {
  structure: string;
  recent_swings: Swing[];
  last_swing_high: Swing | null;
  last_swing_low: Swing | null;
}

export interface TrendIndicators {
  moving_averages: TrendMA;
  ichimoku: IchimokuData;
  market_structure: MarketStructure;
}

export interface RSIData {
  current: number;
  history: number[];
  state: string;
}

export interface MACDData {
  macd: number;
  signal: number;
  histogram: number;
  histogram_direction: string;
  cross: string;
}

export interface StochRSIData {
  k: number;
  d: number;
  state: string;
  cross: string;
}

export interface DivergenceData {
  detected: boolean;
  type: string | null;
}

export interface MomentumIndicators {
  rsi: RSIData;
  macd: MACDData;
  stoch_rsi: StochRSIData;
  divergence_rsi: DivergenceData;
  divergence_macd: DivergenceData;
}

export interface ATRData {
  value_usdt: number;
  value_pct: number;
  period: number;
}

export interface BollingerData {
  upper: number;
  middle: number;
  lower: number;
  width_pct: number;
  squeeze: boolean;
}

export interface VolatilityIndicators {
  atr: ATRData;
  bollinger: BollingerData;
}

export interface OBVData {
  current: number;
  slope: string;
}

export interface VolumeProfile {
  poc: number;
  vah: number;
  val: number;
  total_volume: number;
  bin_count: number;
  window_bars: number;
}

export interface VolumeIndicators {
  obv: OBVData;
  vwap: number | null;
  volume_profile: VolumeProfile;
}

export interface FibLevel {
  ratio: number;
  price: number;
  kind: string;
}

export interface FibonacciData {
  direction: string;
  swing_high: { price: number; index: number; timestamp_ms: number };
  swing_low: { price: number; index: number; timestamp_ms: number };
  levels: FibLevel[];
}

export interface FundingData {
  current_rate: number;
  avg_24h: number;
  avg_7d: number;
  extreme: boolean;
  next_funding_time: number | null;
}

export interface OIData {
  current: number;
  change_1h_pct: number | null;
  change_4h_pct: number | null;
  change_24h_pct: number | null;
}

export interface LongShortData {
  ratio: number;
  long_account: number;
  short_account: number;
  extreme: boolean;
  period: string;
}

export interface FuturesIndicators {
  funding: FundingData;
  open_interest: OIData;
  long_short: LongShortData;
}

export interface PriceLevel {
  price: number;
  kind: "support" | "resistance";
  sources: string[];
  confluence_count: number;
  strength_score: number;
}

export interface LevelsBundle {
  current_price: number;
  supports: PriceLevel[];
  resistances: PriceLevel[];
}

export interface IndicatorBundle {
  symbol: string;
  timeframe: string;
  computed_at: string;
  kline_count: number;
  trend: TrendIndicators;
  momentum: MomentumIndicators;
  volatility: VolatilityIndicators;
  volume: VolumeIndicators;
  fibonacci: FibonacciData;
  levels: LevelsBundle;
  futures: FuturesIndicators | null;
}

// ─── Position Risk ───

export interface RiskLiquidation {
  at_5x: number;
  at_10x: number;
  actual: number;
}

export interface RiskFunding {
  funding_rate: number;
  h24: number;
  h72: number;
  w1: number;
}

export interface RiskRR {
  tp1: number;
  tp2: number;
  tp3: number;
  weighted: number;
}

export interface VolatilityAdjustment {
  factor: number;
  reason: string;
}

export interface PositionRiskResult {
  symbol: string;
  direction: Direction;
  entry: number;
  stop: number;
  targets: number[];
  balance: number;
  base_risk_pct: number;
  adjusted_risk_pct: number;
  volatility_adjustment: VolatilityAdjustment;
  stop_distance_pct: number;
  risk_amount_usd: number;
  position_size_usd: number;
  leverage_required: number;
  leverage_actual: number;
  margin_used: number;
  liquidation: RiskLiquidation;
  funding_costs: RiskFunding;
  rr: RiskRR;
  warnings: string[];
  computed_at: string;
}

// ─── Correlations ───

export interface CorrelationItem {
  symbol: string;
  coefficient: number;
  category: string;
  sign: string;
}

export interface SymbolCorrelations {
  symbol: string;
  period_days: number;
  timeframe: string;
  all: CorrelationItem[];
  strong: CorrelationItem[];
  moderate: CorrelationItem[];
  weak: CorrelationItem[];
  decoupled: CorrelationItem[];
  by_sector_avg: Record<string, number>;
  vs_btc: number | null;
  vs_eth: number | null;
  vs_dxy: number | null;
  vs_sp500: number | null;
  computed_at: string;
}

// ─── Top-level ───

export interface AnalysisModuleStatus {
  name: string;
  ok: boolean;
  error: string | null;
  duration_ms: number | null;
}

export interface FetchTimings {
  total_ms: number;
  phase1_core_ms: number | null;
  phase2_parallel_ms: number | null;
  phase3_risk_ms: number | null;
}

export interface AnalysisFullResult {
  symbol: string;
  timeframe: string;
  current_price: number;
  computed_at: string;
  cache_hit: boolean;
  fetch_timings: FetchTimings;
  indicators: IndicatorBundle;
  final_confluence: FinalConfluenceResult;
  multi_tf_alignment: AlignmentResult;
  setup_quality: SetupQualityResult;
  macro: MacroSnapshot | null;
  correlations: SymbolCorrelations | null;
  risk_position: PositionRiskResult | null;
  module_statuses: AnalysisModuleStatus[];
  warnings: string[];
}
