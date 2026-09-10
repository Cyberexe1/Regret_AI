import { describe, expect, it } from 'vitest';
import { buildCriticalUncertainties, buildReportThresholds } from './buildDecisionReport';
import type { ApiAssumption, ApiThreshold } from '@/api/types';

function assumption(overrides: Partial<ApiAssumption> = {}): ApiAssumption {
  return {
    id: 'asm-1',
    decision_id: 'dec-1',
    statement: 'Repeat customers will sustain unit economics.',
    source: 'implicit',
    importance: 'critical',
    confidence: 0.4,
    evidence_status: 'not_addressed',
    dependency: null,
    failure_consequence: null,
    reason: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function threshold(overrides: Partial<ApiThreshold> = {}): ApiThreshold {
  return {
    id: 'thr-1',
    decision_id: 'dec-1',
    variable: 'Repeat-order rate',
    threshold_type: 'unknown',
    direction: 'below',
    threshold_value: null,
    lower_bound: null,
    upper_bound: null,
    unit: null,
    confidence: 0.6,
    derivation: 'unknown',
    consequence: null,
    related_regret_scenario_ids: [],
    related_assumption_ids: [],
    evidence_basis: null,
    validation_status: 'unknown',
    calculation_formula: null,
    calculation_inputs: null,
    calculation_provenance: null,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('buildCriticalUncertainties', () => {
  it('ranks by importance, critical first', () => {
    const low = assumption({ id: 'a-low', importance: 'low' });
    const critical = assumption({ id: 'a-critical', importance: 'critical' });

    const result = buildCriticalUncertainties([low, critical], []);

    expect(result[0]!.id).toBe('a-critical');
    expect(result[0]!.rank).toBe('01');
  });

  it('never fabricates a confidence label when confidence is null', () => {
    const result = buildCriticalUncertainties([assumption({ confidence: null })], []);
    expect(result[0]!.confidenceLabel).toBe('Unknown');
    expect(result[0]!.confidencePercent).toBeUndefined();
  });
});

describe('buildReportThresholds', () => {
  it('marks a threshold with no numeric value as non-numeric, never inventing one', () => {
    const result = buildReportThresholds([threshold({ threshold_value: null, lower_bound: null, upper_bound: null })]);
    expect(result[0]!.hasNumericValue).toBe(false);
  });

  it('marks a threshold with a real numeric value as numeric', () => {
    const result = buildReportThresholds([threshold({ threshold_value: '24' })]);
    expect(result[0]!.hasNumericValue).toBe(true);
  });

  it('uses the backend validation_status directly, never implying certainty', () => {
    const result = buildReportThresholds([threshold({ validation_status: 'provisional' })]);
    expect(result[0]!.validationStatusLabel).toBe('Provisional');
  });
});
