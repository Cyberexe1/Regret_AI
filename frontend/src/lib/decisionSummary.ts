import type { Decision, Experiment, RiskLevel, Tone } from '@/types';

/* -------------------------------------------------------------------------- *
 * Row data for the decision history.
 *
 * Everything here is derived from the decision, its analysis and its
 * experiments. Nothing is stored twice, so a list row can never disagree with
 * the report it links to.
 * -------------------------------------------------------------------------- */

export const DECISION_STATUS_LABELS = {
  notStarted: 'Not started',
  evidenceIncomplete: 'Evidence incomplete',
  experimentRunning: 'Experiment running',
  experimentRecommended: 'Experiment recommended',
  needsValidation: 'Needs validation',
  decisionReady: 'Decision ready',
  committed: 'Committed',
  abandoned: 'Abandoned',
} as const;

export type DecisionStatusLabel =
  (typeof DECISION_STATUS_LABELS)[keyof typeof DECISION_STATUS_LABELS];

const STATUS_TONE: Record<DecisionStatusLabel, Tone> = {
  'Not started': 'neutral',
  'Evidence incomplete': 'warning',
  'Experiment running': 'info',
  'Experiment recommended': 'accent',
  'Needs validation': 'warning',
  'Decision ready': 'success',
  Committed: 'success',
  Abandoned: 'neutral',
};

/**
 * Risk band. Uses the regret index once an analysis exists, and falls back to
 * declared stakes before then, since stakes are the only signal available.
 */
export function deriveRiskLevel(decision: Decision): RiskLevel {
  const regretIndex = decision.analysis?.regretIndex;

  if (typeof regretIndex === 'number') {
    if (regretIndex >= 67) return 'high';
    if (regretIndex >= 34) return 'medium';
    return 'low';
  }

  switch (decision.stakes) {
    case 'defining':
    case 'high':
      return 'high';
    case 'moderate':
      return 'medium';
    default:
      return 'low';
  }
}

function deriveStatusLabel(decision: Decision, experiments: Experiment[]): DecisionStatusLabel {
  switch (decision.status) {
    case 'draft':
      return DECISION_STATUS_LABELS.notStarted;
    case 'abandoned':
      return DECISION_STATUS_LABELS.abandoned;
    case 'committed':
      return DECISION_STATUS_LABELS.committed;
    case 'analyzing':
      return DECISION_STATUS_LABELS.evidenceIncomplete;
    case 'testing':
      return DECISION_STATUS_LABELS.experimentRunning;
    case 'analyzed':
      break;
  }

  const analysis = decision.analysis;
  if (!analysis) return DECISION_STATUS_LABELS.evidenceIncomplete;

  // Low regret exposure and nothing left to test: ready to commit.
  if (analysis.regretIndex < 25) return DECISION_STATUS_LABELS.decisionReady;

  // A recommended experiment that has not started yet is the next move.
  const recommended = experiments.find(
    (experiment) => experiment.id === analysis.recommendedExperimentId,
  );
  if (recommended?.status === 'proposed') {
    return DECISION_STATUS_LABELS.experimentRecommended;
  }

  return DECISION_STATUS_LABELS.needsValidation;
}

/** Assumptions the engine is not confident about are the open uncertainties. */
function countUncertainties(decision: Decision): number {
  return (
    decision.analysis?.assumptions.filter((assumption) => assumption.confidence !== 'high')
      .length ?? 0
  );
}

export interface DecisionSummary {
  decision: Decision;
  risk: RiskLevel;
  statusLabel: DecisionStatusLabel;
  statusTone: Tone;
  uncertaintyCount: number;
  experimentCount: number;
}

export function summariseDecision(
  decision: Decision,
  allExperiments: Experiment[],
): DecisionSummary {
  const statusLabel = deriveStatusLabel(decision, allExperiments);

  return {
    decision,
    risk: deriveRiskLevel(decision),
    statusLabel,
    statusTone: STATUS_TONE[statusLabel],
    uncertaintyCount: countUncertainties(decision),
    experimentCount: allExperiments.filter(
      (experiment) => experiment.decisionId === decision.id,
    ).length,
  };
}
