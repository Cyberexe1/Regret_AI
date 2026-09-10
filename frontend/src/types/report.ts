import type { Tone } from './index';

/* -------------------------------------------------------------------------- *
 * Decision report - view types
 *
 * These are thin, presentational wrappers around the real backend entities
 * (`ApiAssumption`, `ApiBlindspot`, `ApiRegretScenario`, `ApiThreshold`,
 * `ApiChallenge`, `ApiExperiment` - see `@/api/types`), built by
 * `@/lib/reportModel`. Nothing here is fabricated: every field either comes
 * directly from a backend response or is a deterministic re-labelling of
 * one (e.g. a 0.0-1.0 confidence float mapped to a Low/Medium/High badge).
 * -------------------------------------------------------------------------- */

export interface SnapshotItem {
  label: string;
  value: string;
  tone?: Tone;
}

/** An assumption or blindspot, presented as one "thing that could break this
 * decision" - ranked by importance for display, never re-scored. */
export interface CriticalUncertainty {
  id: string;
  kind: 'assumption' | 'blindspot';
  rank: string;
  title: string;
  importanceLabel: string;
  importanceTone: Tone;
  confidenceLabel: string;
  confidenceTone: Tone;
  confidencePercent?: number;
  evidenceStatusLabel: string;
  evidenceStatusTone: Tone;
  reason?: string | null;
  dependency?: string | null;
  failureConsequence?: string | null;
  whyItMatters?: string | null;
  evidenceGap?: string | null;
}

export interface ReportScenario {
  id: string;
  title: string;
  failureCondition: string;
  probabilityBand: string | null;
  impact: string | null;
  impactTone: Tone;
  regretLevel: string | null;
  regretLevelTone: Tone;
  triggerVariable: string | null;
  triggerDirection: string | null;
  consequence: string | null;
  evidenceBasis: string | null;
}

export interface ReportThreshold {
  id: string;
  variable: string;
  unit: string | null;
  direction: string | null;
  thresholdValue: string | null;
  lowerBound: number | null;
  upperBound: number | null;
  hasNumericValue: boolean;
  validationStatusLabel: string;
  validationStatusTone: Tone;
  confidencePercent?: number;
  consequence: string | null;
  derivation: string | null;
  evidenceBasis: string | null;
}

export interface ReportAssumptionRow {
  id: string;
  statement: string;
  evidenceStatusLabel: string;
  evidenceStatusTone: Tone;
  note: string | null;
}
