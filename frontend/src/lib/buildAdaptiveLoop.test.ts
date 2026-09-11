import { describe, expect, it } from 'vitest';
import {
  buildAdaptiveCycleRows,
  buildAdaptiveLoopSummary,
  EMPTY_ADAPTIVE_LOOP_SUMMARY,
} from './buildAdaptiveLoop';
import type { ApiAdaptiveExperimentState } from '@/api/types';

function state(overrides: Partial<ApiAdaptiveExperimentState> = {}): ApiAdaptiveExperimentState {
  return {
    state_id: 'state-1',
    decision_id: 'dec-1',
    user_id: 'user-1',
    cycle_number: 1,
    current_status: 'awaiting_experiment',
    current_primary_uncertainty_id: 'assumption-1',
    current_primary_threshold_id: 'threshold-1',
    current_experiment_id: 'experiment-1',
    previous_experiment_id: null,
    previous_result_id: null,
    previous_assessment: null,
    current_assessment: 'insufficient_evidence',
    uncertainty_status: [],
    stopping_reason: null,
    next_action: "Run the recommended experiment ('14-day pilot') and submit its result.",
    why_this_is_next: "'Retention' has very high information value...",
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('buildAdaptiveLoopSummary', () => {
  it('returns the empty, found=false summary when state is null - never fabricating a loop', () => {
    const result = buildAdaptiveLoopSummary(null);

    expect(result).toEqual(EMPTY_ADAPTIVE_LOOP_SUMMARY);
    expect(result.found).toBe(false);
  });

  it('maps a real awaiting_experiment state into a found=true summary', () => {
    const result = buildAdaptiveLoopSummary(state());

    expect(result.found).toBe(true);
    expect(result.cycleNumber).toBe(1);
    expect(result.statusLabel).toBe('Awaiting experiment');
    expect(result.isConcluded).toBe(false);
    expect(result.currentExperimentId).toBe('experiment-1');
  });

  it('flags assessmentChanged only when previous and current assessments actually differ', () => {
    const changed = buildAdaptiveLoopSummary(
      state({ previous_assessment: 'supported', current_assessment: 'weakened' }),
    );
    const unchanged = buildAdaptiveLoopSummary(
      state({ previous_assessment: 'supported', current_assessment: 'supported' }),
    );
    const noPrevious = buildAdaptiveLoopSummary(state({ previous_assessment: null }));

    expect(changed.assessmentChanged).toBe(true);
    expect(changed.previousAssessmentLabel).toBe('Supported');
    expect(changed.currentAssessmentLabel).toBe('Weakened');
    expect(unchanged.assessmentChanged).toBe(false);
    expect(noPrevious.assessmentChanged).toBe(false);
  });

  it('MANDATORY: exposes the correct previous_state/new_state for a supported -> weakened transition', () => {
    // Mirrors the exact scenario the spec requires: an experiment causes
    // the decision's assessment to move from supported to weakened, and
    // the UI must show that transition, not merely "assessment updated."
    const result = buildAdaptiveLoopSummary(
      state({
        previous_assessment: 'supported',
        current_assessment: 'weakened',
        uncertainty_status: [
          {
            threshold_id: 'threshold-1',
            previous_status: 'under_test',
            current_status: 'failed',
            observed_value: null,
            required_value: '24',
            confidence: 0.7,
            validation_status: 'validated',
          },
        ],
      }),
    );

    expect(result.previousAssessmentLabel).toBe('Supported');
    expect(result.currentAssessmentLabel).toBe('Weakened');
    expect(result.assessmentChanged).toBe(true);
    expect(result.thresholdChanges).toHaveLength(1);
    expect(result.thresholdChanges[0]!.previousStatusLabel).toBe('Under test');
    expect(result.thresholdChanges[0]!.currentStatusLabel).toBe('Failed');
    expect(result.thresholdChanges[0]!.currentStatusTone).toBe('danger');
  });

  it('marks sufficiently_validated/inconclusive/user_stopped/blocked as concluded', () => {
    for (const status of ['sufficiently_validated', 'inconclusive', 'user_stopped', 'blocked'] as const) {
      const result = buildAdaptiveLoopSummary(state({ current_status: status }));
      expect(result.isConcluded).toBe(true);
    }
  });

  it('never marks an active status (awaiting_experiment/ready_for_next_experiment) as concluded', () => {
    for (const status of ['awaiting_experiment', 'ready_for_next_experiment'] as const) {
      const result = buildAdaptiveLoopSummary(state({ current_status: status }));
      expect(result.isConcluded).toBe(false);
    }
  });

  it('passes through next_action and why_this_is_next verbatim, never rewriting them', () => {
    const result = buildAdaptiveLoopSummary(state());

    expect(result.nextAction).toBe(state().next_action);
    expect(result.whyThisIsNext).toBe(state().why_this_is_next);
  });

  it('surfaces stopping_reason only when present, never fabricating one', () => {
    const blocked = buildAdaptiveLoopSummary(
      state({ current_status: 'blocked', stopping_reason: 'No VOI analysis yet.' }),
    );
    const active = buildAdaptiveLoopSummary(state());

    expect(blocked.stoppingReason).toBe('No VOI analysis yet.');
    expect(active.stoppingReason).toBeNull();
  });
});

describe('buildAdaptiveCycleRows', () => {
  it('returns an empty array for an empty history, never fabricating cycles', () => {
    expect(buildAdaptiveCycleRows([])).toEqual([]);
  });

  it('maps every real history entry in the order given, without re-sorting', () => {
    const history = [
      state({ state_id: 'a', cycle_number: 1, created_at: '2026-01-01T00:00:00Z' }),
      state({ state_id: 'b', cycle_number: 2, created_at: '2026-01-02T00:00:00Z' }),
    ];

    const rows = buildAdaptiveCycleRows(history);

    expect(rows).toHaveLength(2);
    expect(rows[0]!.stateId).toBe('a');
    expect(rows[0]!.cycleNumber).toBe(1);
    expect(rows[1]!.stateId).toBe('b');
    expect(rows[1]!.cycleNumber).toBe(2);
  });
});
