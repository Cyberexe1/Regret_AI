/**
 * REGRET ENGINE 2.0's Decision Evolution & Causal Timeline (Step 22):
 * pure mapping from the real backend `ApiDecisionEvolution` response
 * into presentational view models - mirrors `buildAdaptiveLoop.ts` and
 * `buildValueOfInformation.ts` exactly.
 *
 * Nothing here is fabricated. `typeLabel`/`sourceTypeLabel` are
 * deterministic re-labellings of the backend's own enum/string values.
 * `previousStateLabel`/`newStateLabel` are copied through only when the
 * source event itself carries them - never invented for an event with
 * no real transition.
 */
import type { ApiDecisionDelta, ApiDecisionEvolution, ApiDecisionEvolutionEvent, EvolutionEventType } from '@/api/types';
import { formatRelative } from '@/lib/format';
import { assessmentLabel, assessmentTone } from '@/lib/buildAdaptiveLoop';
import type { DecisionDeltaSummary, DecisionEvolutionSummary, EvolutionEventRow } from '@/types/report';
import type { DecisionValidationState } from '@/api/types';

const EVENT_TYPE_LABEL: Record<EvolutionEventType, string> = {
  decision_created: 'Decision created',
  analysis_completed: 'Analysis completed',
  assumption_identified: 'Assumption identified',
  blindspot_identified: 'Blindspot identified',
  regret_scenario_identified: 'Regret scenario identified',
  threshold_identified: 'Threshold identified',
  experiment_recommended: 'Experiment recommended',
  experiment_started: 'Experiment started',
  experiment_completed: 'Experiment completed',
  experiment_result: 'Result observed',
  threshold_validated: 'Threshold validated',
  threshold_failed: 'Threshold failed',
  re_evaluation: 'Decision re-evaluated',
  assessment_changed: 'Assessment changed',
  learning_recorded: 'Learning recorded',
  next_experiment_selected: 'Next uncertainty prioritized',
  validation_state_changed: 'Validation state changed',
  decision_completed: 'Validation loop concluded',
  historical_insight_surfaced: 'Historical insight',
};

const SOURCE_TYPE_LABEL: Record<string, string> = {
  decision: 'Decision',
  analysis_run: 'Analysis run',
  assumption: 'Assumption',
  blindspot: 'Blindspot',
  regret_scenario: 'Regret scenario',
  threshold: 'Threshold',
  experiment: 'Experiment',
  experiment_result: 'Experiment result',
  re_evaluation: 'Re-evaluation',
  threshold_comparison: 'Threshold comparison',
  memory_learning: 'Memory learning',
  adaptive_state: 'Adaptive cycle',
  historical_insight: 'Historical insight',
};

function sourceTypeLabel(sourceType: string): string {
  return SOURCE_TYPE_LABEL[sourceType] ?? sourceType;
}

/** Best-effort label for a raw state string (e.g. an assessment status,
 * a threshold state) - tries the shared assessment vocabulary first
 * since most previous_state/new_state values are DecisionValidationState
 * values, falls back to a simple capitalization for anything else
 * (e.g. threshold states, uncertainty ids) rather than guessing further. */
function stateLabel(value: string | null): string | null {
  if (value === null) return null;
  const known = ASSESSMENT_STATES.has(value as DecisionValidationState);
  if (known) return assessmentLabel(value as DecisionValidationState);
  return value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, ' ');
}

const ASSESSMENT_STATES = new Set<DecisionValidationState>([
  'strongly_supported',
  'supported',
  'partially_supported',
  'insufficient_evidence',
  'weakened',
  'strongly_weakened',
  'inconclusive',
  'requires_more_testing',
]);

function buildRow(event: ApiDecisionEvolutionEvent): EvolutionEventRow {
  return {
    eventId: event.event_id,
    cycleNumber: event.cycle_number,
    eventType: event.event_type,
    typeLabel: EVENT_TYPE_LABEL[event.event_type],
    timestampLabel: formatRelative(event.timestamp),
    sortKey: event.timestamp,
    title: event.title,
    summary: event.summary,
    sourceTypeLabel: sourceTypeLabel(event.source_type),
    sourceId: event.source_id,
    impact: event.impact,
    previousStateLabel: stateLabel(event.previous_state),
    newStateLabel: stateLabel(event.new_state),
    reason: event.reason,
    isHistorical: event.is_historical,
    affectedAssumptionIds: event.affected_assumption_ids,
    affectedThresholdIds: event.affected_threshold_ids,
    affectedExperimentIds: event.affected_experiment_ids,
    affectedRegretScenarioIds: event.affected_regret_scenario_ids,
    evidenceIds: event.evidence_ids,
  };
}

/** Empty state shown before a decision has an id yet - a normal, valid
 * state, never an error. */
export const EMPTY_DECISION_EVOLUTION_SUMMARY: DecisionEvolutionSummary = {
  found: false,
  currentAssessmentLabel: '',
  currentAssessmentTone: 'neutral',
  currentCycle: null,
  totalCycles: 0,
  cyclesCompleted: 0,
  uncertaintiesResolvedCount: 0,
  uncertaintiesRemainingCount: 0,
  experimentsCompletedCount: 0,
  timeline: [],
  majorChanges: [],
  currentUncertaintyIds: [],
  validatedThresholdIds: [],
  failedThresholdIds: [],
  currentPrimaryUncertaintyId: null,
  truncated: false,
};

/**
 * Builds the full "Decision Evolution" section's view model from a real
 * `ApiDecisionEvolution` response. `found=false` only when there is no
 * response at all yet (decision id not resolved) - once the decision
 * exists, a one-event timeline (just `decision_created`) is itself a
 * valid `found=true` state, never treated as empty/error.
 */
export function buildDecisionEvolutionSummary(
  evolution: ApiDecisionEvolution | null,
): DecisionEvolutionSummary {
  if (evolution === null) return EMPTY_DECISION_EVOLUTION_SUMMARY;

  const experimentsCompletedCount = new Set(
    evolution.timeline
      .filter((event) => event.event_type === 'experiment_completed')
      .map((event) => event.source_id),
  ).size;

  const currentAssessmentAsState = evolution.current_assessment as DecisionValidationState;
  const knownAssessment = ASSESSMENT_STATES.has(currentAssessmentAsState);

  return {
    found: true,
    currentAssessmentLabel: knownAssessment
      ? assessmentLabel(currentAssessmentAsState)
      : (stateLabel(evolution.current_assessment) ?? evolution.current_assessment),
    currentAssessmentTone: knownAssessment ? assessmentTone(currentAssessmentAsState) : 'neutral',
    currentCycle: evolution.current_cycle,
    totalCycles: evolution.total_cycles,
    cyclesCompleted: evolution.total_cycles,
    uncertaintiesResolvedCount:
      evolution.validated_thresholds.length + evolution.failed_thresholds.length,
    uncertaintiesRemainingCount: evolution.current_uncertainties.length,
    experimentsCompletedCount,
    timeline: evolution.timeline.map(buildRow),
    majorChanges: evolution.major_changes.map(buildRow),
    currentUncertaintyIds: evolution.current_uncertainties,
    validatedThresholdIds: evolution.validated_thresholds,
    failedThresholdIds: evolution.failed_thresholds,
    currentPrimaryUncertaintyId: evolution.current_primary_uncertainty,
    truncated: evolution.truncated,
  };
}

/** Builds the reusable "What changed?" card's view model from a real
 * `ApiDecisionDelta` - counts only, never a fabricated narrative beyond
 * the backend's own `explanation` string. */
export function buildDecisionDeltaSummary(delta: ApiDecisionDelta | null): DecisionDeltaSummary {
  if (delta === null) {
    return {
      changed: false,
      assessmentChanged: false,
      assumptionsChangedCount: 0,
      thresholdsChangedCount: 0,
      experimentsChangedCount: 0,
      learningsAddedCount: 0,
      explanation: '',
    };
  }

  return {
    changed: delta.changed,
    assessmentChanged: delta.assessment_changed,
    assumptionsChangedCount: delta.assumptions_changed.length,
    thresholdsChangedCount: delta.thresholds_changed.length,
    experimentsChangedCount: delta.experiments_changed.length,
    learningsAddedCount: delta.learnings_added.length,
    explanation: delta.explanation,
  };
}
