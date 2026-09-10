import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ReevaluationPanel } from './ReevaluationPanel';
import type { ApiReEvaluation } from '@/api/types';

function sampleReevaluation(overrides: Partial<ApiReEvaluation> = {}): ApiReEvaluation {
  return {
    id: 'reval-1',
    decision_id: 'dec-1',
    experiment_id: 'exp-1',
    experiment_result_id: 'res-1',
    previous_assessment: 'Threshold was provisional at 24%.',
    new_assessment: 'Observed repeat rate came in at 18%.',
    threshold_comparisons: [
      {
        threshold_id: 'thr-1',
        variable: 'Repeat-order rate',
        observed_value: '18',
        threshold_value: '24',
        status: 'missed',
        explanation: 'Observed value fell below the recorded threshold.',
      },
    ],
    assumption_reevaluations: [],
    regret_scenario_reevaluations: [],
    decision_assessment: {
      status: 'weakened',
      confidence: 0.85,
      summary: 'The observed value did not meet the recorded threshold.',
      changed_assumptions: [],
      affected_thresholds: ['thr-1'],
      affected_regret_scenarios: [],
      recommended_next_step: 'Do not commit yet; investigate further.',
      evidence_basis: [],
    },
    changed_thresholds: ['thr-1'],
    changed_assumptions: [],
    changed_regret_scenarios: [],
    key_learning: 'Repeat-order rate was observed at 18%, below the 24% threshold.',
    recommended_next_step: 'Do not commit yet; investigate further.',
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('ReevaluationPanel', () => {
  it('renders the real before/after assessment from backend data, never inventing a verdict', () => {
    render(<ReevaluationPanel reevaluation={sampleReevaluation()} />);

    expect(screen.getByText('Threshold was provisional at 24%.')).toBeInTheDocument();
    expect(screen.getByText('Observed repeat rate came in at 18%.')).toBeInTheDocument();
    expect(screen.getByText('Weakened')).toBeInTheDocument();
    expect(screen.getByText('Do not commit yet; investigate further.')).toBeInTheDocument();
    expect(screen.getByText(/Repeat-order rate was observed at 18%/)).toBeInTheDocument();
  });

  it('renders threshold comparisons only when the backend actually provided them', () => {
    render(<ReevaluationPanel reevaluation={sampleReevaluation({ threshold_comparisons: [] })} />);

    expect(screen.queryByText('Threshold comparisons')).not.toBeInTheDocument();
  });
});
