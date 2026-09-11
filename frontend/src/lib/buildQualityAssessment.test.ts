import { describe, expect, it } from 'vitest';
import {
  EMPTY_QUALITY_ASSESSMENT_SUMMARY,
  buildCalibrationInsightRow,
  buildCalibrationInsightRows,
  buildQualityAssessmentSummary,
} from './buildQualityAssessment';
import type { ApiCalibrationInsight, ApiQualityAssessment, ApiQualityCheck } from '@/api/types';

function check(overrides: Partial<ApiQualityCheck> = {}): ApiQualityCheck {
  return {
    check_id: 'check-1',
    category: 'evidence',
    name: 'critical_assumption_has_evidence',
    status: 'passed',
    severity: 'info',
    message: 'Every critical assumption has at least one linked evidence finding.',
    related_entity_type: 'assumption',
    related_entity_id: 'assumption-1',
    evidence_ids: [],
    recommendation: null,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function assessment(overrides: Partial<ApiQualityAssessment> = {}): ApiQualityAssessment {
  return {
    quality_id: 'quality-1',
    decision_id: 'decision-1',
    analysis_run_id: 'run-1',
    user_id: 'user-1',
    overall_quality: 'moderate',
    evidence_quality: 'strong',
    assumption_quality: 'moderate',
    threshold_quality: 'weak',
    experiment_quality: 'insufficient',
    provenance_quality: 'strong',
    consistency_quality: 'strong',
    freshness_quality: 'moderate',
    historical_learning_quality: 'strong',
    blocking_issues: [],
    warnings: [check({ check_id: 'warn-1', status: 'warning', severity: 'medium' })],
    strengths: [check({ check_id: 'strength-1' })],
    checks: [check({ check_id: 'strength-1' }), check({ check_id: 'warn-1', status: 'warning' })],
    generated_at: '2026-01-01T00:00:00Z',
    methodology_version: 'quality-v1',
    ...overrides,
  };
}

function insight(overrides: Partial<ApiCalibrationInsight> = {}): ApiCalibrationInsight {
  return {
    calibration_id: 'calibration-1',
    user_id: 'user-1',
    variable: 'Customer retention rate',
    expected_direction: 'above',
    observation_count: 4,
    successful_count: 1,
    unsuccessful_count: 3,
    inconclusive_count: 0,
    recurring_bias: 'consistently_overoptimistic',
    evidence_strength: 'moderate_calibration_evidence',
    confidence: 0.67,
    supporting_decision_ids: ['dec-1', 'dec-2', 'dec-3'],
    supporting_learning_ids: [],
    explanation:
      "3 of 4 comparable experiments for 'Customer retention rate' produced outcomes below the original expectation.",
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
    ...overrides,
  };
}

describe('buildQualityAssessmentSummary', () => {
  it('returns the empty summary when no assessment has ever been computed', () => {
    expect(buildQualityAssessmentSummary(null)).toEqual(EMPTY_QUALITY_ASSESSMENT_SUMMARY);
    expect(EMPTY_QUALITY_ASSESSMENT_SUMMARY.found).toBe(false);
  });

  it('maps a real assessment into a summary with 8 category bands, never fabricating a 9th', () => {
    const summary = buildQualityAssessmentSummary(assessment());

    expect(summary.found).toBe(true);
    expect(summary.overallBandLabel).toBe('Moderate');
    expect(summary.categoryBands).toHaveLength(8);
    expect(summary.categoryBands.map((c) => c.category)).toEqual([
      'evidence',
      'assumption',
      'threshold',
      'experiment',
      'provenance',
      'consistency',
      'freshness',
      'historical',
    ]);
  });

  it('copies each category band through from the real backend field, never re-deriving it', () => {
    const summary = buildQualityAssessmentSummary(assessment({ threshold_quality: 'insufficient' }));

    const thresholdBand = summary.categoryBands.find((c) => c.category === 'threshold');
    expect(thresholdBand?.band).toBe('insufficient');
    expect(thresholdBand?.bandLabel).toBe('Insufficient data');
  });

  it('separates blocking issues, warnings, and strengths without altering their messages', () => {
    const summary = buildQualityAssessmentSummary(
      assessment({
        blocking_issues: [check({ check_id: 'blocking-1', status: 'failed', severity: 'critical' })],
      }),
    );

    expect(summary.blockingIssues).toHaveLength(1);
    expect(summary.blockingIssues[0]!.message).toBe(check().message);
    expect(summary.warnings).toHaveLength(1);
    expect(summary.strengths).toHaveLength(1);
    expect(summary.checks).toHaveLength(2);
  });
});

describe('buildCalibrationInsightRow', () => {
  it('copies the explanation through verbatim, never rewriting it into a percentage', () => {
    const row = buildCalibrationInsightRow(insight());

    expect(row.explanation).toBe(insight().explanation);
    expect(row.explanation).not.toMatch(/%/);
    expect(row.biasLabel).toBe('Consistently over-optimistic');
    expect(row.evidenceStrengthLabel).toBe('Moderate calibration evidence');
    expect(row.supportingDecisionCount).toBe(3);
  });

  it('labels insufficient history distinctly from a detected bias', () => {
    const row = buildCalibrationInsightRow(
      insight({ recurring_bias: 'insufficient_history', observation_count: 1 }),
    );

    expect(row.biasLabel).toBe('Not enough history yet');
  });
});

describe('buildCalibrationInsightRows', () => {
  it('sorts by observation count, most-observed first', () => {
    const few = insight({ calibration_id: 'few', observation_count: 2 });
    const many = insight({ calibration_id: 'many', observation_count: 6 });

    const rows = buildCalibrationInsightRows([few, many]);

    expect(rows[0]!.calibrationId).toBe('many');
    expect(rows[1]!.calibrationId).toBe('few');
  });

  it('returns an empty array for an empty input, never fabricating an insight', () => {
    expect(buildCalibrationInsightRows([])).toEqual([]);
  });
});
