import type { DecisionDraft } from '@/types';

/**
 * Initial, empty intake form state. Submission now goes straight to the
 * real API (`useDecisionSubmission`) rather than being staged through
 * `sessionStorage` and handed off via router state - once a decision is
 * created it has a real id and every later page (analysis, report, graph)
 * fetches it fresh from the backend instead of reading a local draft.
 */
export const emptyDecisionDraft: DecisionDraft = {
  decision: '',
  categories: [],
  desiredOutcome: '',
  constraintsText: '',
  beliefs: '',
  uncertainties: '',
  alternatives: '',
  commitment: '',
  extraDetails: {},
  constraints: {
    budget: '',
    timeline: '',
    location: '',
    riskTolerance: 'balanced',
  },
  evidence: [],
  sourceUrl: '',
};


