/**
 * Analysis full result — Adım 17 backend payload minimal subset.
 *
 * Şu an için Symbol Header (Topbar) sadece şu alanları kullanır:
 *  - symbol, current_price
 *  - setup_quality.grade, setup_quality.direction
 *  - final_confluence.final_score
 *
 * İleride Dashboard kartları için genişletilecek.
 */
import type { Direction, GradeLetter } from "@/types/api";

export type Timeframe = "15m" | "1H" | "4H" | "1D";

export interface SetupQualitySubset {
  grade: GradeLetter | null;
  direction: Direction;
}

export interface FinalConfluenceSubset {
  final_score: number;
}

export interface AnalysisFullResult {
  symbol: string;
  timeframe: string;
  current_price: number;
  computed_at: string;
  setup_quality: SetupQualitySubset;
  final_confluence: FinalConfluenceSubset;
}
