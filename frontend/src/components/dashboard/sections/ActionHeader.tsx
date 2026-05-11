/**
 * Aksiyon Header (A) — Adım 21.
 *
 * Sol: büyük Grade badge + Direction ikonu
 * Orta: Confidence (level + label + advice tooltip)
 * Sağ: Final Confluence skoru + Multi-TF Alignment + modifier chips
 */
import { LevelsBlock } from "@/components/dashboard/sections/LevelsBlock";
import { cn } from "@/lib/utils";
import {
  confluenceColor,
  formatSignedScore,
} from "@/lib/format-macro";
import type {
  AlignmentResult,
  ConfidenceLevel,
  FinalConfluenceResult,
  LevelsBundle,
  SetupGrade,
  SetupQualityResult,
} from "@/types/analysis";
import type { Direction } from "@/types/api";

// ─── Grade büyük badge ───

const GRADE_STYLES: Record<SetupGrade, string> = {
  A: "bg-binance-long text-white",
  B: "bg-[#4ECCA3] text-binance-bg",
  C: "bg-binance-accent text-binance-bg",
  D: "bg-orange-500 text-white",
  NO_TRADE: "bg-binance-short text-white",
};

const GRADE_TOOLTIPS: Record<SetupGrade, string> = {
  A: "A kalite — en güçlü sinyal (90-100). Tam pozisyon ok.",
  B: "B kalite — güçlü sinyal (70-89). Normal pozisyon.",
  C: "C kalite — orta sinyal (50-69). Küçük pozisyon, dikkat.",
  D: "D kalite — zayıf sinyal (<50). Açma; izleme listesinde tut.",
  NO_TRADE: "No-Trade Zone — pozisyon açılmaz.",
};

function GradeBigBadge({ grade }: { grade: SetupGrade }) {
  const label = grade === "NO_TRADE" ? "DUR" : grade;
  return (
    <div
      title={GRADE_TOOLTIPS[grade]}
      className={cn(
        "flex h-14 w-14 items-center justify-center rounded-lg text-2xl font-bold",
        GRADE_STYLES[grade]
      )}
    >
      {label}
    </div>
  );
}

// ─── Direction ───

function DirectionBig({ direction }: { direction: Direction }) {
  if (direction === "long") {
    return (
      <span
        title="Long (yukarı yönlü setup)"
        className="text-lg font-bold leading-none text-binance-long"
      >
        ▲ LONG
      </span>
    );
  }
  if (direction === "short") {
    return (
      <span
        title="Short (aşağı yönlü setup)"
        className="text-lg font-bold leading-none text-binance-short"
      >
        ▼ SHORT
      </span>
    );
  }
  return (
    <span
      title="Nötr (yön yok)"
      className="text-lg font-bold leading-none text-binance-text-muted"
    >
      ◇ NÖTR
    </span>
  );
}

// ─── Confidence ───

const CONFIDENCE_COLOR: Record<ConfidenceLevel, string> = {
  VERY_LOW: "bg-binance-short/15 text-binance-short border-binance-short/40",
  LOW: "bg-orange-500/15 text-orange-400 border-orange-500/40",
  MEDIUM: "bg-binance-accent/15 text-binance-accent border-binance-accent/40",
  HIGH: "bg-[#4ECCA3]/15 text-[#4ECCA3] border-[#4ECCA3]/40",
  VERY_HIGH: "bg-binance-long/15 text-binance-long border-binance-long/40",
};

const CONFIDENCE_LABEL_TR: Record<ConfidenceLevel, string> = {
  VERY_LOW: "Çok düşük",
  LOW: "Düşük",
  MEDIUM: "Orta",
  HIGH: "Yüksek",
  VERY_HIGH: "Çok yüksek",
};

function ConfidenceBlock({
  confidence,
}: {
  confidence: SetupQualityResult["confidence"];
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
        Güven Seviyesi
      </span>
      <div className="flex items-center gap-2">
        <span
          title={confidence.advice}
          className={cn(
            "inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-xs font-semibold",
            CONFIDENCE_COLOR[confidence.level]
          )}
        >
          {CONFIDENCE_LABEL_TR[confidence.level]}
          <span className="font-mono text-[10px] opacity-70">
            {confidence.level}
          </span>
        </span>
      </div>
      <span className="text-[11px] text-binance-text-secondary">
        {confidence.label}
      </span>
      <span className="text-[10px] text-binance-text-muted">
        {confidence.trade_count} geçmiş işlem
      </span>
    </div>
  );
}

// ─── Confluence + Alignment ───

const ALIGNMENT_TR: Record<string, string> = {
  strong: "Güçlü hizalı",
  aligned: "Hizalı",
  weak: "Zayıf hizalı",
  conflicted: "Çelişkili",
  bullish: "Bullish",
  bearish: "Bearish",
  neutral: "Nötr",
};

function alignmentLabel(label: string): string {
  return ALIGNMENT_TR[label.toLowerCase()] ?? label;
}

function ScoresBlock({
  confluence,
  alignment,
}: {
  confluence: FinalConfluenceResult;
  alignment: AlignmentResult;
}) {
  const consistentTfs = alignment.by_timeframe.filter(
    (t) => t.direction === alignment.consistent_direction
  ).length;
  return (
    <div className="flex flex-col gap-1">
      <div>
        <span className="text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
          Confluence
        </span>
        <div className="flex items-baseline gap-2 font-mono">
          <span
            className={cn(
              "text-2xl font-bold tabular-nums",
              confluenceColor(confluence.final_score)
            )}
          >
            {formatSignedScore(confluence.final_score)}
          </span>
          <span className="text-xs text-binance-text-secondary">
            {alignmentLabel(confluence.label)}
          </span>
        </div>
      </div>
      <div>
        <span className="text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
          Multi-TF Hizalama
        </span>
        <div className="flex items-baseline gap-2 font-mono">
          <span className="text-sm font-semibold tabular-nums text-binance-text-primary">
            {formatSignedScore(alignment.alignment_score)}
          </span>
          <span className="text-xs text-binance-text-secondary">
            {alignmentLabel(alignment.label)}
            {alignment.consistent_direction
              ? ` — ${consistentTfs}/6 TF aynı yön`
              : " — çelişki"}
          </span>
        </div>
      </div>
    </div>
  );
}

// ─── Modifier chips ───

type ChipTone = "pos" | "neg" | "neutral" | "blocking";

interface ChipSpec {
  key: string;
  label: string;
  /** "+10.0" gibi sayı veya "KAÇIN" / "BLOKLAYICI" gibi override etiketi. */
  valueDisplay: string;
  tone: ChipTone;
}

const COMPONENT_LABELS_TR: Record<string, string> = {
  trend: "Trend",
  momentum: "Momentum",
  volume: "Hacim",
  volatility: "Volatilite",
  futures: "Futures",
};

function tonalize(v: number, threshold = 5): ChipTone {
  if (v > threshold) return "pos";
  if (v < -threshold) return "neg";
  return "neutral";
}

function gradeChip(key: string, value: number): ChipSpec {
  // Override marker'lar — sayı yerine etiket göster
  if (key === "trade_quality_avoid") {
    return {
      key,
      label: "Trade Quality",
      valueDisplay: "KAÇIN",
      tone: "blocking",
    };
  }
  if (key === "no_trade_zone_blocking") {
    return {
      key,
      label: "No-Trade Zone",
      valueDisplay: "BLOKLAYICI",
      tone: "blocking",
    };
  }
  // Normal grade modifier'lar
  if (key === "counter_trend") {
    return {
      key,
      label: "Counter-Trend",
      valueDisplay: formatSignedScore(value),
      tone: value > 0 ? "pos" : "neg",
    };
  }
  if (
    key === "trade_quality_excellent" ||
    key === "trade_quality_weak"
  ) {
    return {
      key,
      label: "Trade Quality",
      valueDisplay: formatSignedScore(value),
      tone: value > 0 ? "pos" : "neg",
    };
  }
  if (key === "no_trade_zone_warning") {
    return {
      key,
      label: "No-Trade Uyarı",
      valueDisplay: formatSignedScore(value),
      tone: "neg",
    };
  }
  if (key === "macro_strong_positive" || key === "macro_strong_negative") {
    return {
      key,
      label: "Macro",
      valueDisplay: formatSignedScore(value),
      tone: value > 0 ? "pos" : "neg",
    };
  }
  // Fallback — bilinmeyen anahtar: prettify
  const prettified = key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
  return {
    key,
    label: prettified,
    valueDisplay: formatSignedScore(value),
    tone: value > 0 ? "pos" : "neg",
  };
}

function ModifierChips({
  components,
  macroModifier,
  gradeModifiers,
}: {
  components: Record<string, number>;
  macroModifier: number;
  gradeModifiers: Record<string, number>;
}) {
  const chips: ChipSpec[] = [];

  // Confluence components — Türkçeleştir
  for (const [k, v] of Object.entries(components)) {
    chips.push({
      key: `comp_${k}`,
      label: COMPONENT_LABELS_TR[k] ?? k,
      valueDisplay: formatSignedScore(v),
      tone: tonalize(v),
    });
  }

  // Macro modifier
  chips.push({
    key: "macro_modifier",
    label: "Macro",
    valueDisplay: formatSignedScore(macroModifier),
    tone: tonalize(macroModifier),
  });

  // Grade modifiers — Türkçe etiket + override handling
  for (const [k, v] of Object.entries(gradeModifiers)) {
    if (v === 0) continue;
    chips.push(gradeChip(k, v));
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {chips.map((c) => (
        <span
          key={c.key}
          className={cn(
            "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium",
            c.tone === "pos" && "bg-binance-long/10 text-binance-long",
            c.tone === "neg" && "bg-binance-short/10 text-binance-short",
            c.tone === "neutral" &&
              "bg-binance-text-muted/15 text-binance-text-muted",
            c.tone === "blocking" &&
              "bg-binance-short/25 font-bold text-binance-short"
          )}
        >
          <span className="text-binance-text-muted">{c.label}</span>
          <span className="font-mono tabular-nums">{c.valueDisplay}</span>
        </span>
      ))}
    </div>
  );
}

// ─── Main ───

interface Props {
  symbol: string;
  timeframe: string;
  setupQuality: SetupQualityResult;
  confluence: FinalConfluenceResult;
  alignment: AlignmentResult;
  levels: LevelsBundle;
  atrUsdt: number;
}

export function ActionHeader({
  symbol,
  timeframe,
  setupQuality,
  confluence,
  alignment,
  levels,
  atrUsdt,
}: Props) {
  return (
    <div className="rounded-lg border border-binance-border bg-binance-surface p-4">
      {/* ÜST: 3-kolon (Grade+Dir | Güven | Skorlar) */}
      <div className="grid gap-6 lg:grid-cols-[auto_minmax(220px,1fr)_minmax(260px,auto)] lg:items-start">
        {/* Col 1: Grade + Direction */}
        <div className="flex items-center gap-3">
          <GradeBigBadge grade={setupQuality.grade} />
          <div className="flex flex-col gap-1">
            <DirectionBig direction={setupQuality.direction} />
            <span className="text-[10px] text-binance-text-muted">
              Setup Kalitesi
              {setupQuality.base_grade !== setupQuality.grade && (
                <span className="ml-1 font-mono">
                  (base: {setupQuality.base_grade})
                </span>
              )}
            </span>
          </div>
        </div>

        {/* Col 2: Confidence */}
        <ConfidenceBlock confidence={setupQuality.confidence} />

        {/* Col 3: Confluence + Alignment */}
        <ScoresBlock confluence={confluence} alignment={alignment} />
      </div>

      {/* ORTA: Seviyeler ladder */}
      <div className="mt-4 border-t border-binance-border/60 pt-3">
        <LevelsBlock
          symbol={symbol}
          timeframe={timeframe}
          levels={levels}
          atrUsdt={atrUsdt}
        />
      </div>

      {/* ALT: Skor kırılımı */}
      <div className="mt-3 border-t border-binance-border/60 pt-3">
        <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-binance-text-muted">
          Skor Kırılımı
        </div>
        <ModifierChips
          components={confluence.components}
          macroModifier={confluence.macro_modifier}
          gradeModifiers={setupQuality.grade_modifiers}
        />
      </div>
    </div>
  );
}
