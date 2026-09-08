import type { Confidence, RiskLevel, Tone } from './index';

/* -------------------------------------------------------------------------- *
 * Decision report
 *
 * The shape of a finished stress test as it is presented to the user. Kept
 * separate from `DecisionAnalysis`, which is the engine-facing model: a report
 * is a curated, ranked view built for reading, not the full analysis payload.
 * -------------------------------------------------------------------------- */

export type AssumptionSupport = 'supported' | 'uncertain' | 'unsupported';

export interface SnapshotItem {
  label: string;
  value: string;
  /** Rendered as a progress bar when present, e.g. decision confidence. */
  percentage?: number;
  tone?: Tone;
}

/** A measurable quantity the decision turns on. */
export interface CriticalUncertainty {
  id: string;
  rank: string;
  title: string;
  /** One line on why this is on the list. */
  summary: string;
  current: { label: string; value: string };
  threshold: { label: string; value: string };
  impact: RiskLevel;
  confidence: Confidence;
  /** Revealed when the card is expanded. */
  detail: {
    whyItMatters: string;
    evidence: string[];
    howToResolve: string;
  };
}

export interface ThresholdPoint {
  /** Repeat customer rate, in percent. */
  rate: number;
  /** Expected monthly contribution in rupees; negative below break-even. */
  contribution: number;
}

export interface RegretThreshold {
  metricLabel: string;
  valueLabel: string;
  narrative: string;
  /** Inclusive band of the current estimate. */
  currentRange: [number, number];
  thresholdValue: number;
  /** Upper bound of the plotted x-axis. */
  domain: [number, number];
  breakEvenRate: number;
  curve: ThresholdPoint[];
}

export type ScenarioKind = 'base' | 'failure' | 'upside';

export interface FutureScenario {
  id: string;
  kind: ScenarioKind;
  title: string;
  description: string;
  /** Illustrative only, and labelled as such in the UI. */
  probability: number;
  impact: RiskLevel;
  trigger: string;
  tone: Tone;
}

export interface ReportAssumption {
  id: string;
  statement: string;
  support: AssumptionSupport;
  note: string;
}

export interface ReportRecommendation {
  verdict: string;
  action: string;
  costLabel: string;
  expectedLearning: RiskLevel;
  decisionImpact: RiskLevel;
  ctaLabel: string;
}

export interface DecisionReport {
  decisionId: string;
  title: string;
  statusLabel: string;
  riskLevel: RiskLevel;
  summary: string;
  snapshot: SnapshotItem[];
  uncertainties: CriticalUncertainty[];
  threshold: RegretThreshold;
  scenarios: FutureScenario[];
  assumptions: ReportAssumption[];
  recommendation: ReportRecommendation;
}
