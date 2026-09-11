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

/** REGRET ENGINE 2.0: what the system remembers about a decision -
 * "what we thought" (expected, from analysis) vs "what we learned"
 * (observed, from a real experiment result). Every field is either a
 * real backend `DecisionMemory` field or a deterministic re-labelling of
 * one, exactly like every other view model in this file - never
 * fabricated. */
export interface MemoryLearningRow {
  id: string;
  statement: string;
  typeLabel: string;
  typeTone: Tone;
  isValidated: boolean;
  observedValue: string | null;
  expectedValue: string | null;
  varianceDescription: string | null;
  createdAtLabel: string;
}

export interface DecisionMemorySummary {
  hasMemory: boolean;
  isValidated: boolean;
  decisionSummary: string;
  originalAssessment: string | null;
  outcomeSummary: string | null;
  finalAssessment: string | null;
  confidencePercent: number | undefined;
  learnings: MemoryLearningRow[];
  unresolvedUncertainties: string[];
  experimentCount: number;
  criticalAssumptionCount: number;
  criticalThresholdCount: number;
  criticalRegretScenarioCount: number;
}

export interface MemoryTimelineEvent {
  id: string;
  label: string;
  detail: string;
  timestampLabel: string;
  tone: Tone;
  sortKey: string;
}

/** REGRET ENGINE 2.0: Decision Similarity & Historical Insight Engine -
 * one past decision surfaced as relevant, with the deterministic
 * similarity score that produced it. Every field is a real backend
 * `SimilarityScore` field or a deterministic re-labelling of one -
 * `relevanceLabel` is NEVER phrased as a probability, see
 * `buildHistoricalContext.ts`. */
export interface RelatedDecisionRow {
  decisionId: string;
  title: string;
  relevancePercent: number;
  matchedFeatureLabels: string[];
  explanation: string;
}

/** One surfaced historical insight - "what we learned" from a similar
 * past decision, always traceable to a real `MemoryLearning`. Never
 * shown as a fact about the current decision - `statement` is the
 * source learning's own text, and the UI always frames it as
 * "Previous decision:" (see `HistoricalInsightsPanel`). */
export interface HistoricalInsightRow {
  id: string;
  statement: string;
  typeLabel: string;
  typeTone: Tone;
  isValidated: boolean;
  relevancePercent: number;
  sourceDecisionId: string;
  observedValue: string | null;
  expectedValue: string | null;
  createdAtLabel: string;
}

/** REGRET ENGINE 2.0's full historical-context view model, built from a
 * real `ApiHistoricalContext` response - see `buildHistoricalContext.ts`. */
export interface HistoricalContextSummary {
  found: boolean;
  relevantDecisions: RelatedDecisionRow[];
  insights: HistoricalInsightRow[];
  recurringVariables: string[];
  previouslyFailedAssumptions: string[];
  previouslyValidatedThresholds: string[];
  warnings: string[];
}

/** REGRET ENGINE 2.0's Value-of-Information Engine (Step 20): "which
 * uncertainty is most worth resolving before committing?" - explicitly
 * NOT the same question as "which risk is scariest." Every field here is
 * a real backend `ValueOfInformationItem` field or a deterministic
 * re-labelling of one - see `buildValueOfInformation.ts`. `practicalValueLabel`
 * is never phrased as a probability or a statistically calibrated score. */
export interface ValueOfInformationRow {
  uncertaintyId: string;
  rank: string;
  title: string;
  description: string;
  informationValueLabel: string;
  informationValueTone: Tone;
  practicalValueLabel: string;
  practicalValueTone: Tone;
  rationale: string;
  costLabel: string;
  durationLabel: string | null;
  feasibilityLabel: string;
  reversibilityLabel: string;
  thresholdId: string | null;
  thresholdStatusLabel: string;
  historicalRelevanceLabel: string | null;
  confidencePercent: number;
  /** 0-100, derived only from the item's own qualitative band (never a
   * fabricated precise score) - purely for the ranked bar-chart visual. */
  barPercent: number;
}

export interface ValueOfInformationSummary {
  found: boolean;
  ranked: ValueOfInformationRow[];
  primaryUncertaintyId: string | null;
  whyThisIsPrimary: string | null;
  summary: string;
}

/** REGRET ENGINE 2.0's Adaptive Experiment Loop (Step 21): the closed
 * loop Decision -> Uncertainties -> Value of Information -> Best
 * Experiment -> Real-World Result -> Re-evaluation -> Updated
 * Uncertainties -> ... Every field is a real backend
 * `AdaptiveExperimentState` field or a deterministic re-labelling of
 * one - see `buildAdaptiveLoop.ts`. `assessmentTone`/`statusTone` are
 * presentational only, never a probability. */
export interface AdaptiveThresholdRow {
  thresholdId: string;
  previousStatusLabel: string;
  currentStatusLabel: string;
  currentStatusTone: Tone;
  observedValue: string | null;
  requiredValue: string | null;
}

export interface AdaptiveLoopSummary {
  found: boolean;
  stateId: string;
  cycleNumber: number;
  statusLabel: string;
  statusTone: Tone;
  isConcluded: boolean;
  isBlocked: boolean;
  isUserStopped: boolean;
  currentAssessmentLabel: string;
  currentAssessmentTone: Tone;
  previousAssessmentLabel: string | null;
  /** True only when the assessment actually differs from the previous
   * cycle's - drives the "SUPPORTED -> WEAKENED" style change display. */
  assessmentChanged: boolean;
  currentPrimaryUncertaintyId: string | null;
  currentPrimaryThresholdId: string | null;
  currentExperimentId: string | null;
  previousExperimentId: string | null;
  nextAction: string;
  whyThisIsNext: string | null;
  stoppingReason: string | null;
  thresholdChanges: AdaptiveThresholdRow[];
  updatedAtLabel: string;
}

export interface AdaptiveCycleRow {
  stateId: string;
  cycleNumber: number;
  statusLabel: string;
  statusTone: Tone;
  currentAssessmentLabel: string;
  currentExperimentId: string | null;
  nextAction: string;
  createdAtLabel: string;
  sortKey: string;
}

/** One concrete attack on the decision, as identified by the Devil's
 * Advocate - `Challenge` on the backend. */
export interface ReportChallenge {
  id: string;
  claim: string;
  attack: string;
  severityLabel: string;
  severityTone: Tone;
  confidencePercent?: number;
  failureMechanism: string | null;
  evidenceBasis: string | null;
}
