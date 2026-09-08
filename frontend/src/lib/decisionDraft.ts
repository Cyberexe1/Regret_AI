import type { DecisionDraft } from '@/types';

const STORAGE_KEY = 'regret-engine:decision-draft';

export const emptyDecisionDraft: DecisionDraft = {
  decision: '',
  desiredOutcome: '',
  constraints: {
    budget: '',
    timeline: '',
    location: '',
    riskTolerance: 'balanced',
  },
  beliefs: '',
  evidence: [],
  sourceUrl: '',
};

/**
 * Session-scoped handoff between the intake page and the analysis workspace.
 *
 * Deliberately not a network call and not global state: the draft is written on
 * submit and read by whichever page needs it next. `sessionStorage` keeps it
 * across a reload without persisting a half-finished decision forever.
 */
export function saveDecisionDraft(draft: DecisionDraft): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
  } catch {
    // Storage can be unavailable (private browsing, quota). The draft is still
    // passed through router state, so submission must not fail because of this.
  }
}

export function readDecisionDraft(): DecisionDraft | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as DecisionDraft;
  } catch {
    return null;
  }
}

export function clearDecisionDraft(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nothing to do.
  }
}
