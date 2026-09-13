import type { InterviewReadinessLevel } from '@/api/types';
import type { Tone } from '@/types';

/**
 * Exact readiness-state copy (REGRET ENGINE 2.0, Step 27 spec section
 * 12) - shared between `InterviewConsole` (mid-conversation) and
 * `InterviewSnapshotSummary` (after completion/skip) so the same
 * deterministic readiness band always reads the same way everywhere.
 * NEVER a fabricated confidence score - see the backend's own
 * `app.interview.state.compute_readiness`.
 */
export const READINESS_LABEL: Record<InterviewReadinessLevel, string> = {
  early: "We're still understanding the decision.",
  enough: 'I have enough context to stress-test this decision.',
  ready: "I've identified the main uncertainties worth testing.",
};

export const READINESS_TONE: Record<InterviewReadinessLevel, Tone> = {
  early: 'neutral',
  enough: 'info',
  ready: 'success',
};
