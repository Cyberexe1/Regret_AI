import type {
  DecisionDomain,
  DecisionStatus,
  ExperimentStatus,
  RegretHorizon,
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

export const horizonLabel: Record<RegretHorizon, string> = {
  '6-months': '6 months',
  '1-year': '1 year',
  '3-years': '3 years',
  '5-years': '5 years',
};

export const horizonMonths: Record<RegretHorizon, number> = {
  '6-months': 6,
  '1-year': 12,
  '3-years': 36,
  '5-years': 60,
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
