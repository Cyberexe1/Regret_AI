/**
 * REGRET ENGINE 2.0's Cross-Decision Learning Engine (Step 23): pure
 * mapping from the real backend `ApiCrossDecisionPattern` response into
 * a presentational view model - mirrors `buildAdaptiveLoop.ts` and
 * `buildValueOfInformation.ts` exactly.
 *
 * Nothing here is fabricated. `statement` is always the backend's own
 * already-hedged wording, copied through verbatim - this module never
 * rewrites a pattern into a stronger or more definitive claim.
 */
import type { ApiCrossDecisionPattern, PatternConfidence, PatternStatus } from '@/api/types';
import { formatRelative } from '@/lib/format';
import type { CrossDecisionPatternRow } from '@/types/report';
import type { Tone } from '@/types';

const STATUS_LABEL: Record<PatternStatus, string> = {
  emerging: 'Emerging',
  repeated: 'Repeated',
  established: 'Established',
  contradicted: 'Mixed evidence',
  inactive: 'Inactive',
};

const STATUS_TONE: Record<PatternStatus, Tone> = {
  emerging: 'info',
  repeated: 'info',
  established: 'success',
  contradicted: 'warning',
  inactive: 'neutral',
};

const CONFIDENCE_LABEL: Record<PatternConfidence, string> = {
  low: 'Low confidence',
  medium: 'Medium confidence',
  high: 'High confidence',
};

const CONFIDENCE_TONE: Record<PatternConfidence, Tone> = {
  low: 'neutral',
  medium: 'info',
  high: 'success',
};

export function buildCrossDecisionPatternRow(pattern: ApiCrossDecisionPattern): CrossDecisionPatternRow {
  return {
    patternId: pattern.pattern_id,
    title: pattern.title,
    statement: pattern.statement,
    statusLabel: STATUS_LABEL[pattern.status],
    statusTone: STATUS_TONE[pattern.status],
    confidenceLabel: CONFIDENCE_LABEL[pattern.confidence],
    confidenceTone: CONFIDENCE_TONE[pattern.confidence],
    confidenceBasis: pattern.confidence_basis,
    occurrenceCount: pattern.occurrence_count,
    supportingDecisionCount: pattern.supporting_decision_ids.length,
    contradictingDecisionCount: pattern.contradicting_decision_ids.length,
    variable: pattern.variable,
    lastSeenLabel: formatRelative(pattern.last_seen_at),
  };
}

/** Builds every pattern row from a real list response - patterns marked
 * `inactive` are excluded from this default view (spec section 19: they
 * are preserved in storage, never deleted, but a dashboard/decision-page
 * summary shouldn't lead with a pattern that's no longer active). */
export function buildCrossDecisionPatternRows(
  patterns: ApiCrossDecisionPattern[],
): CrossDecisionPatternRow[] {
  return patterns
    .filter((pattern) => pattern.status !== 'inactive')
    .map(buildCrossDecisionPatternRow)
    .sort((a, b) => b.occurrenceCount - a.occurrenceCount);
}
