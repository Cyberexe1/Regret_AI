import { describe, expect, it } from 'vitest';
import {
  buildDecisionDeltaSummary,
  buildDecisionEvolutionSummary,
  EMPTY_DECISION_EVOLUTION_SUMMARY,
} from './buildDecisionEvolution';
import type { ApiDecisionDelta, ApiDecisionEvolution, ApiDecisionEvolutionEvent } from '@/api/types';

function event(overrides: Partial<ApiDecisionEvolutionEvent> = {}): ApiDecisionEvolutionEvent {
  return {
    event_id: 'event-1',
    decision_id: 'dec-1',
    cycle_number: null,
    event_type: 'decision_created',
    timestamp: '2026-01-01T00:00:00Z',
    title: 'Decision created',
    summary: 'Open a cloud kitchen',
    source_type: 'decision',
    source_id: 'dec-1',
    impact: 'minor',
    previous_state: null,
    new_state: null,
    reason: null,
    affected_assumption_ids: [],
    affected_threshold_ids: [],
    affected_experiment_ids: [],
    affected_regret_scenario_ids: [],
    evidence_ids: [],
    is_historical: false,
    ...overrides,
  };
}

function evolution(overrides: Partial<ApiDecisionEvolution> = {}): ApiDecisionEvolution {
  return {
    decision_id: 'dec-1',
    user_id: 'user-1',
    current_assessment: 'insufficient_evidence',
    current_cycle: null,
    total_cycles: 0,
    timeline: [event()],
    major_changes: [],
    current_uncertainties: [],
    validated_thresholds: [],
    failed_thresholds: [],
    current_primary_uncertainty: null,
    truncated: false,
    generated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('buildDecisionEvolutionSummary', () => {
  it('returns the empty, found=false summary when evolution is null', () => {
    const result = buildDecisionEvolutionSummary(null);

    expect(result).toEqual(EMPTY_DECISION_EVOLUTION_SUMMARY);
    expect(result.found).toBe(false);
  });

  it('maps a real evolution response into a found=true summary', () => {
    const result = buildDecisionEvolutionSummary(evolution());

    expect(result.found).toBe(true);
    expect(result.timeline).toHaveLength(1);
    expect(result.timeline[0]!.title).toBe('Decision created');
  });

  it('labels a known DecisionValidationState using the shared assessment vocabulary', () => {
    const result = buildDecisionEvolutionSummary(evolution({ current_assessment: 'weakened' }));

    expect(result.currentAssessmentLabel).toBe('Weakened');
    expect(result.currentAssessmentTone).toBe('warning');
  });

  it('MANDATORY: exposes previous/new state labels for a supported -> weakened assessment_changed event', () => {
    const result = buildDecisionEvolutionSummary(
      evolution({
        timeline: [
          event({
            event_type: 'assessment_changed',
            title: 'Assessment changed',
            previous_state: 'supported',
            new_state: 'weakened',
            reason: 'Observed value did not meet the required threshold.',
            source_type: 're_evaluation',
            source_id: 'reeval-1',
          }),
        ],
      }),
    );

    const row = result.timeline[0]!;
    expect(row.previousStateLabel).toBe('Supported');
    expect(row.newStateLabel).toBe('Weakened');
    expect(row.sourceTypeLabel).toBe('Re-evaluation');
    expect(row.sourceId).toBe('reeval-1');
    expect(row.reason).toBe('Observed value did not meet the required threshold.');
  });

  it('never fabricates a previous/new state label for an event with no real transition', () => {
    const result = buildDecisionEvolutionSummary(evolution());

    expect(result.timeline[0]!.previousStateLabel).toBeNull();
    expect(result.timeline[0]!.newStateLabel).toBeNull();
  });

  it('labels an unrecognized state string (e.g. a threshold state) with simple capitalization', () => {
    const result = buildDecisionEvolutionSummary(
      evolution({
        timeline: [
          event({
            event_type: 'threshold_validated',
            previous_state: 'under_test',
            new_state: 'validated',
          }),
        ],
      }),
    );

    expect(result.timeline[0]!.previousStateLabel).toBe('Under test');
    expect(result.timeline[0]!.newStateLabel).toBe('Validated');
  });

  it('counts experimentsCompletedCount from unique experiment_completed source ids only', () => {
    const result = buildDecisionEvolutionSummary(
      evolution({
        timeline: [
          event({ event_id: 'e1', event_type: 'experiment_completed', source_id: 'exp-1' }),
          event({ event_id: 'e2', event_type: 'experiment_completed', source_id: 'exp-1' }),
          event({ event_id: 'e3', event_type: 'experiment_completed', source_id: 'exp-2' }),
        ],
      }),
    );

    expect(result.experimentsCompletedCount).toBe(2);
  });

  it('labels a historical insight event with isHistorical true, never as current evidence', () => {
    const result = buildDecisionEvolutionSummary(
      evolution({
        timeline: [event({ event_type: 'historical_insight_surfaced', is_historical: true })],
      }),
    );

    expect(result.timeline[0]!.isHistorical).toBe(true);
  });

  it('passes through major_changes as their own mapped rows', () => {
    const majorEvent = event({ event_id: 'major-1', impact: 'major' });
    const result = buildDecisionEvolutionSummary(evolution({ major_changes: [majorEvent] }));

    expect(result.majorChanges).toHaveLength(1);
    expect(result.majorChanges[0]!.eventId).toBe('major-1');
  });

  it('surfaces truncated verbatim from the backend, never re-deciding it client-side', () => {
    const result = buildDecisionEvolutionSummary(evolution({ truncated: true }));

    expect(result.truncated).toBe(true);
  });
});

describe('buildDecisionDeltaSummary', () => {
  function delta(overrides: Partial<ApiDecisionDelta> = {}): ApiDecisionDelta {
    return {
      changed: true,
      assessment_changed: true,
      assumptions_changed: ['a1'],
      thresholds_changed: ['t1', 't2'],
      uncertainties_changed: ['a1'],
      experiments_changed: ['e1'],
      learnings_added: [],
      explanation: 'supported -> weakened',
      ...overrides,
    };
  }

  it('returns a valid unchanged summary when delta is null', () => {
    const result = buildDecisionDeltaSummary(null);

    expect(result.changed).toBe(false);
    expect(result.explanation).toBe('');
  });

  it('maps counts from real id arrays, never re-deriving them', () => {
    const result = buildDecisionDeltaSummary(delta());

    expect(result.thresholdsChangedCount).toBe(2);
    expect(result.assumptionsChangedCount).toBe(1);
    expect(result.experimentsChangedCount).toBe(1);
    expect(result.explanation).toBe('supported -> weakened');
  });
});
