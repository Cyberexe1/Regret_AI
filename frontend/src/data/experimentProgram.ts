import { ROUTES } from './navigation';
import type { ExperimentDetail } from '@/types';

/* -------------------------------------------------------------------------- *
 * Running detail for the recommended experiment.
 *
 * Figures are internally consistent: 28 of 126 participants is 22.2%, day 9 of
 * 14 is 64%, and the ₹15,000 cost matches exp-2210 in data/experiments.ts.
 * -------------------------------------------------------------------------- */

export const recommendedExperimentId = 'exp-2210';

const retentionPilot: ExperimentDetail = {
  experimentId: recommendedExperimentId,
  question: 'Will enough customers return to support the business model?',
  successThreshold: 'Repeat customer rate ≥ 24%',
  failureThreshold: 'Repeat customer rate < 24%',
  expectedLearning: 'high',

  durationDays: 14,
  currentDay: 9,
  progress: 64,
  milestones: [1, 5, 10, 14],

  measures: [
    'First-order customers',
    'Repeat orders',
    'Time to repeat',
    'Acquisition cost',
    'Average order value',
  ],

  results: [
    { label: 'Participants', value: '126', hint: 'First-order customers reached' },
    { label: 'Repeat customers', value: '28', hint: 'Ordered again within the window' },
    { label: 'Repeat rate', value: '22.2%', hint: '28 of 126', tone: 'warning' },
    { label: 'Threshold', value: '24%', hint: 'Required to sustain the model', tone: 'danger' },
  ],

  observedValue: 22.2,
  thresholdValue: 24,
  scaleMax: 30,

  statusLabel: 'Below threshold',
  statusTone: 'warning',

  verdict: {
    headline: 'Current evidence suggests the decision should be reconsidered.',
    detail:
      'With five days left, the repeat rate is 1.8 points under the threshold. That gap is small enough to close and large enough to matter, so none of the paths below is obviously right.',
    tone: 'warning',
    choices: [
      {
        id: 're-analyse',
        label: 'Re-run analysis',
        description: 'Feed the observed 22.2% back into the engine and re-score the decision.',
        to: ROUTES.analysis,
        emphasis: 'primary',
        recorded: 'Re-analysis is the recorded path. The engine will re-score using observed data.',
      },
      {
        id: 'modify',
        label: 'Modify experiment',
        description: 'Extend the window or drop the discount earlier to get a cleaner read.',
        emphasis: 'secondary',
        recorded: 'Modification is the recorded path. The design stays open for editing.',
      },
      {
        id: 'continue',
        label: 'Continue anyway',
        description: 'Commit despite the shortfall, with the gap logged against the decision.',
        emphasis: 'ghost',
        recorded:
          'Continuing is the recorded path. The 1.8 point shortfall is logged against the decision.',
      },
    ],
  },
};

const detailsByExperimentId: Record<string, ExperimentDetail> = {
  [retentionPilot.experimentId]: retentionPilot,
};

export function findExperimentDetail(experimentId: string): ExperimentDetail | undefined {
  return detailsByExperimentId[experimentId];
}
