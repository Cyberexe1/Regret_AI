/**
 * REGRET ENGINE 2.0's Decision Intelligence Quality & Calibration Engine
 * (Step 24): pure mapping from the real backend `ApiQualityAssessment` /
 * `ApiCalibrationInsight` responses into presentational view models -
 * mirrors `buildDecisionEvolution.ts` and `buildCrossDecisionPatterns.ts`
 * exactly.
 *
 * Nothing here is fabricated. Every `message`/`explanation` string is
 * the backend's own deterministic, count-based wording, copied through
 * verbatim - this module only ever attaches display labels/tones to a
 * real enum value, it never invents new judgments.
 *
 * Core principle, carried over unchanged from the backend package
 * docstring: analysis quality is not the same as decision quality. This
 * view model describes how well-grounded the ANALYSIS is - never
 * whether the decision itself is wise.
 */
import type {
  ApiCalibrationInsight,
  ApiQualityAssessment,
  ApiQualityCheck,
  CalibrationEvidenceStrength,
  QualityBand,
  QualityCheckCategory,
  QualityCheckSeverity,
  QualityCheckStatus,
  RecurringBias,
} from '@/api/types';
import { formatRelative } from '@/lib/format';
import type {
  CalibrationInsightRow,
  QualityAssessmentSummary,
  QualityCategoryBand,
  QualityCheckRow,
} from '@/types/report';
import type { Tone } from '@/types';

const BAND_LABEL: Record<QualityBand, string> = {
  strong: 'Strong',
  moderate: 'Moderate',
  weak: 'Weak',
  insufficient: 'Insufficient data',
};

const BAND_TONE: Record<QualityBand, Tone> = {
  strong: 'success',
  moderate: 'info',
  weak: 'warning',
  insufficient: 'neutral',
};

const CATEGORY_LABEL: Record<QualityCheckCategory, string> = {
  evidence: 'Evidence',
  assumption: 'Assumptions',
  threshold: 'Thresholds',
  experiment: 'Experiments',
  provenance: 'Provenance',
  consistency: 'Consistency',
  freshness: 'Freshness',
  historical: 'Historical learning',
  completeness: 'Completeness',
};

const STATUS_LABEL: Record<QualityCheckStatus, string> = {
  passed: 'Passed',
  warning: 'Warning',
  failed: 'Failed',
  not_applicable: 'Not applicable',
};

const STATUS_TONE: Record<QualityCheckStatus, Tone> = {
  passed: 'success',
  warning: 'warning',
  failed: 'danger',
  not_applicable: 'neutral',
};

const SEVERITY_LABEL: Record<QualityCheckSeverity, string> = {
  info: 'Info',
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
};

const BIAS_LABEL: Record<RecurringBias, string> = {
  consistently_overoptimistic: 'Consistently over-optimistic',
  consistently_underoptimistic: 'Consistently under-optimistic',
  mixed: 'Mixed outcomes',
  insufficient_history: 'Not enough history yet',
  no_detectable_bias: 'No detectable bias',
};

const BIAS_TONE: Record<RecurringBias, Tone> = {
  consistently_overoptimistic: 'warning',
  consistently_underoptimistic: 'info',
  mixed: 'neutral',
  insufficient_history: 'neutral',
  no_detectable_bias: 'success',
};

const EVIDENCE_STRENGTH_LABEL: Record<CalibrationEvidenceStrength, string> = {
  limited_history: 'Limited history',
  emerging_calibration: 'Emerging calibration',
  moderate_calibration_evidence: 'Moderate calibration evidence',
  strong_calibration_evidence: 'Strong calibration evidence',
};

const CATEGORY_FIELDS = [
  ['evidence', 'evidence_quality'],
  ['assumption', 'assumption_quality'],
  ['threshold', 'threshold_quality'],
  ['experiment', 'experiment_quality'],
  ['provenance', 'provenance_quality'],
  ['consistency', 'consistency_quality'],
  ['freshness', 'freshness_quality'],
  ['historical', 'historical_learning_quality'],
] as const satisfies readonly [QualityCheckCategory, keyof ApiQualityAssessment][];

function buildCheckRow(check: ApiQualityCheck): QualityCheckRow {
  return {
    checkId: check.check_id,
    category: check.category,
    categoryLabel: CATEGORY_LABEL[check.category],
    name: check.name,
    statusLabel: STATUS_LABEL[check.status],
    statusTone: STATUS_TONE[check.status],
    severityLabel: SEVERITY_LABEL[check.severity],
    message: check.message,
    relatedEntityType: check.related_entity_type,
    relatedEntityId: check.related_entity_id,
    recommendation: check.recommendation,
  };
}

function buildCategoryBand(
  category: QualityCheckCategory,
  band: QualityBand,
): QualityCategoryBand {
  return {
    category,
    categoryLabel: CATEGORY_LABEL[category],
    band,
    bandLabel: BAND_LABEL[band],
    bandTone: BAND_TONE[band],
  };
}

/** Empty state shown before any quality check has ever been run for a
 * decision - a normal, valid state, never an error. */
export const EMPTY_QUALITY_ASSESSMENT_SUMMARY: QualityAssessmentSummary = {
  found: false,
  qualityId: '',
  overallBandLabel: '',
  overallBandTone: 'neutral',
  categoryBands: [],
  blockingIssues: [],
  warnings: [],
  strengths: [],
  checks: [],
  generatedAtLabel: '',
};

/**
 * Builds the "HOW STRONG IS THIS ANALYSIS?" panel's view model from a
 * real `ApiQualityAssessment`. `found=false` only when no assessment has
 * ever been computed yet for this decision.
 */
export function buildQualityAssessmentSummary(
  assessment: ApiQualityAssessment | null,
): QualityAssessmentSummary {
  if (assessment === null) return EMPTY_QUALITY_ASSESSMENT_SUMMARY;

  return {
    found: true,
    qualityId: assessment.quality_id,
    overallBandLabel: BAND_LABEL[assessment.overall_quality],
    overallBandTone: BAND_TONE[assessment.overall_quality],
    categoryBands: CATEGORY_FIELDS.map(([category, field]) =>
      buildCategoryBand(category, assessment[field] as QualityBand),
    ),
    blockingIssues: assessment.blocking_issues.map(buildCheckRow),
    warnings: assessment.warnings.map(buildCheckRow),
    strengths: assessment.strengths.map(buildCheckRow),
    checks: assessment.checks.map(buildCheckRow),
    generatedAtLabel: formatRelative(assessment.generated_at),
  };
}

/** Builds one "WHAT YOUR PAST DECISIONS REVEAL" row from a real
 * `ApiCalibrationInsight` - `explanation` is copied through verbatim,
 * never rewritten into a stronger or more definitive claim. */
export function buildCalibrationInsightRow(
  insight: ApiCalibrationInsight,
): CalibrationInsightRow {
  return {
    calibrationId: insight.calibration_id,
    variable: insight.variable,
    biasLabel: BIAS_LABEL[insight.recurring_bias],
    biasTone: BIAS_TONE[insight.recurring_bias],
    evidenceStrengthLabel: EVIDENCE_STRENGTH_LABEL[insight.evidence_strength],
    observationCount: insight.observation_count,
    successfulCount: insight.successful_count,
    unsuccessfulCount: insight.unsuccessful_count,
    inconclusiveCount: insight.inconclusive_count,
    explanation: insight.explanation,
    supportingDecisionCount: insight.supporting_decision_ids.length,
  };
}

/** Builds every calibration row from a real list response, ranked by
 * how much history backs each one (most-observed first) - mirrors
 * `buildCrossDecisionPatternRows`'s own occurrence-count ordering. */
export function buildCalibrationInsightRows(
  insights: ApiCalibrationInsight[],
): CalibrationInsightRow[] {
  return insights
    .map(buildCalibrationInsightRow)
    .sort((a, b) => b.observationCount - a.observationCount);
}
