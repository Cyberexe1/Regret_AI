import type {
  DecisionDomain,
  DecisionStatus,
  ExperimentPhase,
  ExperimentStatus,
  Reversibility,
} from '@/types';

export const statusLabel: Record<DecisionStatus, string> = {
  draft: 'Draft',
  analyzing: 'Analyzing',
  analyzed: 'Analyzed',
  testing: 'Experiment running',
  committed: 'Committed',
  abandoned: 'Abandoned',
};

export const domainLabel: Record<DecisionDomain, string> = {
  career: 'Career',
  product: 'Product',
  financial: 'Financial',
  hiring: 'Hiring',
  relocation: 'Relocation',
  technology: 'Technology',
  'business-model': 'Business model',
};

export const reversibilityLabel: Record<Reversibility, string> = {
  reversible: 'Reversible',
  'costly-to-reverse': 'Costly to reverse',
  irreversible: 'Irreversible',
};

export const experimentStatusLabel: Record<ExperimentStatus, string> = {
  proposed: 'Proposed',
  running: 'Running',
  inconclusive: 'Inconclusive',
  validated: 'Validated',
  invalidated: 'Invalidated',
};

/**
 * Coarse grouping for listings. The precise status is still shown alongside, so
 * "Completed" never hides whether the experiment actually settled the question.
 */
export function experimentPhase(status: ExperimentStatus): ExperimentPhase {
  if (status === 'running') return 'Running';
  if (status === 'proposed') return 'Proposed';
  return 'Completed';
}
