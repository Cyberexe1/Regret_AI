import { describe, expect, it } from 'vitest';
import { buildHistoricalContext, EMPTY_HISTORICAL_SUMMARY } from './buildHistoricalContext';
import type { ApiHistoricalContext, ApiHistoricalInsight, ApiSimilarityScore } from '@/api/types';

function score(overrides: Partial<ApiSimilarityScore> = {}): ApiSimilarityScore {
  return {
    decision_id: 'dec-past-1',
    score: 0.62,
    matched_features: ['decision_text_similarity'],
    explanation: 'Considered similar because of similar wording.',
    confidence: 0.7,
    ...overrides,
  };
}

function insight(overrides: Partial<ApiHistoricalInsight> = {}): ApiHistoricalInsight {
  return {
    insight_id: 'insight-1',
    source_decision_id: 'dec-past-1',
    source_memory_id: 'mem-1',
    learning_id: 'learning-1',
    statement: 'Observed Repeat-order rate did not meet the recorded threshold (18 vs 24).',
    relevance_score: 0.62,
    relevance_reason: 'Considered similar because of similar wording.',
    learning_type: 'threshold_failed',
    source_type: 're_evaluation',
    observed_value: '18',
    expected_value: '24',
    related_variable: null,
    confidence: 0.7,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function response(overrides: Partial<ApiHistoricalContext> = {}): ApiHistoricalContext {
  return {
    found: false,
    relevant_decisions: [],
    relevant_decisions_count: 0,
    relevant_learnings: [],
    recurring_variables: [],
    previously_failed_assumptions: [],
    previously_validated_thresholds: [],
    unresolved_patterns: [],
    warnings: [],
    ...overrides,
  };
}

describe('buildHistoricalContext', () => {
  it('maps a found=false response to a found=false summary, never fabricating relevance', () => {
    const result = buildHistoricalContext(response());

    expect(result.found).toBe(false);
    expect(result.relevantDecisions).toEqual([]);
    expect(result.insights).toEqual([]);
  });

  it('renders relevance as a rounded percentage, never claiming it is a probability', () => {
    const result = buildHistoricalContext(
      response({ found: true, relevant_decisions: [score({ score: 0.6234 })] }),
    );

    expect(result.relevantDecisions[0]!.relevancePercent).toBe(62);
  });

  it('resolves a related decision title from the provided lookup map, never a fabricated title', () => {
    const titleById = new Map([['dec-past-1', 'Open a cloud kitchen']]);
    const result = buildHistoricalContext(
      response({ found: true, relevant_decisions: [score()] }),
      titleById,
    );

    expect(result.relevantDecisions[0]!.title).toBe('Open a cloud kitchen');
  });

  it('falls back to a generic label when the related decision title is unknown', () => {
    const result = buildHistoricalContext(response({ found: true, relevant_decisions: [score()] }));

    expect(result.relevantDecisions[0]!.title).toBe('A past decision');
  });

  it('maps matched_features to human-readable labels', () => {
    const result = buildHistoricalContext(
      response({
        found: true,
        relevant_decisions: [score({ matched_features: ['budget_similarity', 'unknown_feature'] })],
      }),
    );

    expect(result.relevantDecisions[0]!.matchedFeatureLabels).toContain('Comparable budget');
    // Unrecognized features fall back to the raw value, never dropped silently.
    expect(result.relevantDecisions[0]!.matchedFeatureLabels).toContain('unknown_feature');
  });

  it('marks threshold_validated/assumption_validated insights as validated, others as not', () => {
    const validated = buildHistoricalContext(
      response({
        found: true,
        relevant_learnings: [insight({ learning_type: 'threshold_validated' })],
      }),
    );
    const provisional = buildHistoricalContext(
      response({
        found: true,
        relevant_learnings: [insight({ learning_type: 'threshold_inconclusive' })],
      }),
    );

    expect(validated.insights[0]!.isValidated).toBe(true);
    expect(provisional.insights[0]!.isValidated).toBe(false);
  });

  it('passes through recurring_variables, previously_failed_assumptions, previously_validated_thresholds verbatim', () => {
    const result = buildHistoricalContext(
      response({
        found: true,
        recurring_variables: ['Repeat-order rate'],
        previously_failed_assumptions: ['Repeat customers will sustain unit economics.'],
        previously_validated_thresholds: ['Monthly cost stayed below the threshold.'],
      }),
    );

    expect(result.recurringVariables).toEqual(['Repeat-order rate']);
    expect(result.previouslyFailedAssumptions).toEqual([
      'Repeat customers will sustain unit economics.',
    ]);
    expect(result.previouslyValidatedThresholds).toEqual([
      'Monthly cost stayed below the threshold.',
    ]);
  });
});

describe('EMPTY_HISTORICAL_SUMMARY', () => {
  it('is a valid found=false summary usable as a loading placeholder', () => {
    expect(EMPTY_HISTORICAL_SUMMARY.found).toBe(false);
    expect(EMPTY_HISTORICAL_SUMMARY.relevantDecisions).toEqual([]);
  });
});
