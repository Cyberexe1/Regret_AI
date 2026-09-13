import type { ApiDecisionSnapshot } from '@/api/types';

/**
 * Renders a `DecisionSnapshot` into the same free-text shape the
 * backend's own `InterviewService._compose_beliefs_text` writes into
 * the decision's `beliefs` field (REGRET ENGINE 2.0, Step 27) - used
 * only to SEED the editable "Notes" textarea in
 * `InterviewSnapshotSummary` with something that matches what was
 * actually persisted, never sent back verbatim without the user's own
 * edit passing through `PATCH /decisions/{id}` again.
 */
export function composeSnapshotNotes(snapshot: ApiDecisionSnapshot): string {
  const parts: string[] = [];
  if (snapshot.beliefs.length > 0) parts.push(`Beliefs: ${snapshot.beliefs.join('; ')}`);
  if (snapshot.constraints.length > 0) parts.push(`Constraints: ${snapshot.constraints.join('; ')}`);
  if (snapshot.uncertainties.length > 0) {
    parts.push(`Uncertainties: ${snapshot.uncertainties.join('; ')}`);
  }
  if (snapshot.alternatives.length > 0) parts.push(`Alternatives: ${snapshot.alternatives.join('; ')}`);
  if (snapshot.commitments.length > 0) parts.push(`At stake: ${snapshot.commitments.join('; ')}`);
  if (snapshot.evidence.length > 0) parts.push(`Evidence mentioned: ${snapshot.evidence.join('; ')}`);
  return parts.join('\n\n');
}
