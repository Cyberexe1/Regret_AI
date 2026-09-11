import { describe, expect, it } from 'vitest';
import { buildValueOfInformation, EMPTY_VOI_SUMMARY } from './buildValueOfInformation';
import type { ApiValueOfInformationAnalysis, ApiValueOfInformationItem } from '@/api/types';

function item(overrides: Partial<ApiValueOfInformationItem> = {}): ApiValueOfInformationItem {
  return {
    uncertainty_id: 'assumption-1',
    title: 'Repeat customers will sustain unit economics.',
    description: 'Repeat customers will sustain unit economics.',
    related_assumption_ids: ['assumption-1'],
    related_blindspot_ids: [],
    related_threshold_ids: ['threshold-1'],
    related_regret_scenario_ids: ['scenario-1'],
    related_experiment_id: 'experiment-1',
    potential_decision_impact: 'severe',
    decision_sensitivity: 'high',
    regret_severity: 'critical',
    current_evidence_strength: 'none',
    uncertainty_level: 'very_high',
    estimated_test_cost: 'low',
    estimated_test_duration_days: 14,
    feasibility: 'high',
    reversibility: 'high',
    historical_relevance: 'none',
    prior_learning_count: 0,
    threshold_status: 'linked',
    information_value: 'very_high',
    practical_value: 'very_high',
    priority: 1,
    rationale: "'x' has very high information value because...",
    confidence: 0.9,
    ...overrides,
  };
}

function analysis(overrides: Partial<ApiValueOfInformationAnalysis> = {}): ApiValueOfInformationAnalysis {
  return {
    analysis_id: 'voi-1',
    decision_id: 'dec-1',
    ranked_uncertainties: [item()],
    primary_uncertainty_id: 'assumption-1',
    primary_threshold_id: 'threshold-1',
    why_this_is_primary: "'x' has very high information value because...",
    summary: "'Repeat customers will sustain unit economics.' is the highest-priority uncertainty.",
    methodology_version: 'voi-v1',
    created_at: '2026-01-01T00:00:00Z',
    superseded_by_analysis_id: null,
    ...overrides,
  };
}

describe('buildValueOfInformation', () => {
  it('returns the empty summary when analysis is null, never fabricating a ranking', () => {
    const result = buildValueOfInformation(null);

    expect(result.found).toBe(false);
    expect(result.ranked).toEqual([]);
  });

  it('returns the empty summary when ranked_uncertainties is empty', () => {
    const result = buildValueOfInformation(analysis({ ranked_uncertainties: [] }));

    expect(result.found).toBe(false);
  });

  it('maps a real analysis into a found=true summary with ranked rows', () => {
    const result = buildValueOfInformation(analysis());

    expect(result.found).toBe(true);
    expect(result.ranked).toHaveLength(1);
    expect(result.primaryUncertaintyId).toBe('assumption-1');
    expect(result.ranked[0]!.rank).toBe('01');
  });

  it('never labels information_value/practical_value as anything but the qualitative band text', () => {
    const result = buildValueOfInformation(analysis());

    expect(result.ranked[0]!.informationValueLabel).toBe('Very high');
    expect(result.ranked[0]!.practicalValueLabel).toBe('Very high');
  });

  it('derives barPercent only from practical_value, using the fixed documented mapping', () => {
    const high = buildValueOfInformation(analysis({ ranked_uncertainties: [item({ practical_value: 'very_high' })] }));
    const low = buildValueOfInformation(analysis({ ranked_uncertainties: [item({ practical_value: 'very_low' })] }));
    const unknown = buildValueOfInformation(analysis({ ranked_uncertainties: [item({ practical_value: 'unknown' })] }));

    expect(high.ranked[0]!.barPercent).toBe(100);
    expect(low.ranked[0]!.barPercent).toBeLessThan(high.ranked[0]!.barPercent);
    expect(unknown.ranked[0]!.barPercent).toBeLessThan(low.ranked[0]!.barPercent);
  });

  it('surfaces threshold linkage honestly: linked shows the id, not_established shows null', () => {
    const linked = buildValueOfInformation(
      analysis({ ranked_uncertainties: [item({ threshold_status: 'linked', related_threshold_ids: ['t-1'] })] }),
    );
    const notEstablished = buildValueOfInformation(
      analysis({ ranked_uncertainties: [item({ threshold_status: 'not_established', related_threshold_ids: [] })] }),
    );

    expect(linked.ranked[0]!.thresholdId).toBe('t-1');
    expect(notEstablished.ranked[0]!.thresholdId).toBeNull();
    expect(notEstablished.ranked[0]!.thresholdStatusLabel).toContain('No threshold established');
  });

  it('never fabricates a duration label when estimated_test_duration_days is null', () => {
    const result = buildValueOfInformation(
      analysis({ ranked_uncertainties: [item({ estimated_test_duration_days: null })] }),
    );

    expect(result.ranked[0]!.durationLabel).toBeNull();
  });

  it('renders confidence as a percentage, never claiming it is a probability of success', () => {
    const result = buildValueOfInformation(analysis({ ranked_uncertainties: [item({ confidence: 0.42 })] }));

    expect(result.ranked[0]!.confidencePercent).toBe(42);
  });

  it('surfaces historical relevance only when it is not "none"', () => {
    const withHistory = buildValueOfInformation(
      analysis({ ranked_uncertainties: [item({ historical_relevance: 'high' })] }),
    );
    const withoutHistory = buildValueOfInformation(
      analysis({ ranked_uncertainties: [item({ historical_relevance: 'none' })] }),
    );

    expect(withHistory.ranked[0]!.historicalRelevanceLabel).not.toBeNull();
    expect(withoutHistory.ranked[0]!.historicalRelevanceLabel).toBeNull();
  });

  it('passes through the summary and why_this_is_primary verbatim', () => {
    const result = buildValueOfInformation(analysis());

    expect(result.summary).toBe(analysis().summary);
    expect(result.whyThisIsPrimary).toBe(analysis().why_this_is_primary);
  });
});

describe('EMPTY_VOI_SUMMARY', () => {
  it('is a valid found=false summary usable as a loading placeholder', () => {
    expect(EMPTY_VOI_SUMMARY.found).toBe(false);
    expect(EMPTY_VOI_SUMMARY.ranked).toEqual([]);
  });
});
