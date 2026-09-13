import type { ApiDecisionCreate } from '@/api/types';
import { allContextChips } from '@/data/decisionTypes';
import type { DecisionDraftWithFiles } from '@/hooks/useDecisionIntake';

const MAX_TITLE_LENGTH = 200;
const MAX_DESCRIPTION_LENGTH = 5000;

/**
 * Maps a universal `DecisionDraftWithFiles` onto the EXISTING backend
 * `ApiDecisionCreate` contract (Step 25 - "Universal Decision Intake &
 * Adaptive Context UI", spec section 19: "Map the new universal
 * frontend fields to the existing backend contract... do not modify
 * backend models unless absolutely necessary" - carried over unchanged
 * by Step 26's minimal-intake rework, which only changes which fields
 * the UI shows, never this mapping's target contract).
 *
 * The backend's `DecisionCreate` schema (`backend/app/schemas/decision.py`)
 * has no field for `constraintsText`/`uncertainties`/`commitment`/
 * `alternatives`/`extraDetails` - there is nowhere structured to put
 * them without a backend change, so they are folded into `description`
 * as clearly labeled paragraphs. `description` is exactly what the
 * Decision Analyzer agent reads first (see
 * `app/agents/decision_analyzer.py`'s `build_analysis_prompt`), so this
 * actually gets MORE of the user's real context in front of the
 * analysis than before, not less - the decision statement itself always
 * stays the first, unmodified line.
 *
 * `budget`/`timeline`/`location`/`risk_tolerance` keep going through the
 * legacy `constraints` object exactly as before - the backend still has
 * dedicated columns for these, so nothing here changes their wire shape,
 * only their on-screen label (see `@/data/decisionTypes`).
 */
export function buildDecisionCreatePayload(draft: DecisionDraftWithFiles): ApiDecisionCreate {
  return {
    title: draft.decision.slice(0, MAX_TITLE_LENGTH) || 'Untitled decision',
    description: composeDescription(draft),
    desired_outcome: draft.desiredOutcome || undefined,
    budget: draft.constraints.budget ? Number(draft.constraints.budget) || undefined : undefined,
    timeline: draft.constraints.timeline || undefined,
    location: draft.constraints.location || undefined,
    risk_tolerance: draft.constraints.riskTolerance,
    beliefs: draft.beliefs || undefined,
  };
}

function composeDescription(draft: DecisionDraftWithFiles): string {
  const parts = [draft.decision.trim()];

  if (draft.constraintsText.trim()) {
    parts.push(`Constraints: ${draft.constraintsText.trim()}`);
  }
  if (draft.uncertainties.trim()) {
    parts.push(`Least certain about: ${draft.uncertainties.trim()}`);
  }
  if (draft.alternatives.trim()) {
    parts.push(`Alternatives considered: ${draft.alternatives.trim()}`);
  }
  if (draft.commitment.trim()) {
    parts.push(`Putting at stake: ${draft.commitment.trim()}`);
  }
  for (const [id, value] of Object.entries(draft.extraDetails)) {
    if (value.trim()) {
      parts.push(`${extraDetailLabel(id)}: ${value.trim()}`);
    }
  }

  return parts.join('\n\n').slice(0, MAX_DESCRIPTION_LENGTH);
}

/** Renders a chip's own `fieldLabel` when known, falling back to a
 * simple title-cased version of its id - see
 * `@/data/decisionTypes`'s `ContextChip`. Every "note" chip's field
 * label is included verbatim so the description never says something
 * different from what the user actually saw on screen. */
function extraDetailLabel(id: string): string {
  const chip = allContextChips.find((candidate) => candidate.id === id);
  if (chip?.fieldLabel) return chip.fieldLabel;
  return id
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
