import { describe, expect, it } from 'vitest';
import { buildCrossDecisionPatternRow, buildCrossDecisionPatternRows } from './buildCrossDecisionPatterns';
import type { ApiCrossDecisionPattern } from '@/api/types';

function pattern(overrides: Partial<ApiCrossDecisionPattern> = {}): ApiCrossDecisionPattern {
  return {
    pattern_id: 'pattern-1',
    user_id: 'user-1',
    pattern_type: 'recurring_failed_assumption',
    title: 'Customer retention has repeatedly underperformed.',
    statement: 'In your past decisions, retention has repeatedly underperformed.',
    normalized_key: 'retention',
    variable: 'Customer retention rate',
    domain: null,
    decision_types: [],
    occurrence_count: 3,
    supporting_decision_ids: ['dec-1', 'dec-2'],
    supporting_learning_ids: ['learn-1'],
    supporting_experiment_ids: [],
    supporting_threshold_ids: [],
    contradicting_decision_ids: [],
    evidence_count: 3,
    confidence: 'high',
    confidence_basis: '3 decisions support this pattern with no contradicting evidence.',
    first_seen_at: '2026-01-01T00:00:00Z',
    last_seen_at: '2026-01-02T00:00:00Z',
    status: 'established',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
    ...overrides,
  };
}

describe('buildCrossDecisionPatternRow', () => {
  it('maps a real pattern into a row with the exact statement/basis verbatim', () => {
    const row = buildCrossDecisionPatternRow(pattern());

    expect(row.statement).toBe(pattern().statement);
    expect(row.confidenceBasis).toBe(pattern().confidence_basis);
    expect(row.statusLabel).toBe('Established');
    expect(row.confidenceLabel).toBe('High confidence');
    expect(row.supportingDecisionCount).toBe(2);
    expect(row.contradictingDecisionCount).toBe(0);
  });

  it('never rewrites a hedged statement into a stronger claim', () => {
    const hedged = pattern({
      statement: "In your past decisions, this threshold has repeatedly underperformed - this is not a claim it will always fail.",
    });
    const row = buildCrossDecisionPatternRow(hedged);

    expect(row.statement).toContain('not a claim it will always fail');
  });

  it('surfaces contradicting decision counts when present', () => {
    const mixed = pattern({
      supporting_decision_ids: ['dec-1', 'dec-2'],
      contradicting_decision_ids: ['dec-3'],
      status: 'repeated',
    });
    const row = buildCrossDecisionPatternRow(mixed);

    expect(row.contradictingDecisionCount).toBe(1);
    expect(row.statusLabel).toBe('Repeated');
  });
});

describe('buildCrossDecisionPatternRows', () => {
  it('excludes inactive patterns from the default view', () => {
    const active = pattern({ pattern_id: 'active', status: 'established' });
    const inactive = pattern({ pattern_id: 'inactive', status: 'inactive' });

    const rows = buildCrossDecisionPatternRows([active, inactive]);

    expect(rows).toHaveLength(1);
    expect(rows[0]!.patternId).toBe('active');
  });

  it('sorts by occurrence count, highest first', () => {
    const low = pattern({ pattern_id: 'low', occurrence_count: 2 });
    const high = pattern({ pattern_id: 'high', occurrence_count: 5 });

    const rows = buildCrossDecisionPatternRows([low, high]);

    expect(rows[0]!.patternId).toBe('high');
    expect(rows[1]!.patternId).toBe('low');
  });

  it('returns an empty array for an empty input, never fabricating a pattern', () => {
    expect(buildCrossDecisionPatternRows([])).toEqual([]);
  });
});
