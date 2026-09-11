/**
 * REGRET ENGINE 2.0's Adaptive Experiment Loop (Step 21): pure mapping
 * from the real backend `ApiAdaptiveExperimentState`/history into
 * presentational view models - mirrors `buildValueOfInformation.ts` and
 * `buildDecisionMemory.ts` exactly.
 *
 * Nothing here is fabricated. `statusLabel`/`currentAssessmentLabel` are
 * deterministic re-labellings of the backend's own enum values - never a
 * probability, never a verdict on whether the decision is "correct" (see
 * the backend's own `DecisionValidationState` docstring).
 */
import type {
  AdaptiveCycleStatus,
  ApiAdaptiveExperimentState,
  DecisionValidationState,
  ThresholdState,
} from '@/api/types';
import { formatRelative } from '@/lib/format';
import type { AdaptiveCycleRow, AdaptiveLoopSummary, AdaptiveThresholdRow } from '@/types/report';
import type { Tone } from '@/types';

const STATUS_LABEL: Record<AdaptiveCycleStatus, string> = {
  awaiting_experiment: 'Awaiting experiment',
  experiment_active: 'Experiment active',
  awaiting_result: 'Awaiting result',
  re_evaluating: 'Re-evaluating',
  selecting_next_test: 'Selecting next test',
  ready_for_next_experiment: 'Ready for next experiment',
  sufficiently_validated: 'Sufficiently validated',
  inconclusive: 'Inconclusive',
  user_stopped: 'Stopped',
  blocked: 'Blocked',
};

const STATUS_TONE: Record<AdaptiveCycleStatus, Tone> = {
  awaiting_experiment: 'info',
  experiment_active: 'info',
  awaiting_result: 'info',
  re_evaluating: 'info',
  selecting_next_test: 'info',
  ready_for_next_experiment: 'accent',
  sufficiently_validated: 'success',
  inconclusive: 'warning',
  user_stopped: 'neutral',
  blocked: 'warning',
};

const ASSESSMENT_LABEL: Record<DecisionValidationState, string> = {
  strongly_supported: 'Strongly supported',
  supported: 'Supported',
  partially_supported: 'Partially supported',
  insufficient_evidence: 'Insufficient evidence',
  weakened: 'Weakened',
  strongly_weakened: 'Strongly weakened',
  inconclusive: 'Inconclusive',
  requires_more_testing: 'Requires more testing',
};

const ASSESSMENT_TONE: Record<DecisionValidationState, Tone> = {
  strongly_supported: 'success',
  supported: 'success',
  partially_supported: 'info',
  insufficient_evidence: 'neutral',
  weakened: 'warning',
  strongly_weakened: 'danger',
  inconclusive: 'neutral',
  requires_more_testing: 'neutral',
};

const THRESHOLD_STATE_LABEL: Record<ThresholdState, string> = {
  unknown: 'Unknown',
  provisional: 'Provisional',
  under_test: 'Under test',
  validated: 'Validated',
  failed: 'Failed',
  inconclusive: 'Inconclusive',
};

const THRESHOLD_STATE_TONE: Record<ThresholdState, Tone> = {
  unknown: 'neutral',
  provisional: 'neutral',
  under_test: 'info',
  validated: 'success',
  failed: 'danger',
  inconclusive: 'warning',
};

export function assessmentLabel(state: DecisionValidationState): string {
  return ASSESSMENT_LABEL[state];
}

export function assessmentTone(state: DecisionValidationState): Tone {
  return ASSESSMENT_TONE[state];
}

const CONCLUDED_STATUSES = new Set<AdaptiveCycleStatus>([
  'sufficiently_validated',
  'inconclusive',
  'user_stopped',
  'blocked',
]);

function buildThresholdRow(record: ApiAdaptiveExperimentState['uncertainty_status'][number]): AdaptiveThresholdRow {
  return {
    thresholdId: record.threshold_id,
    previousStatusLabel: THRESHOLD_STATE_LABEL[record.previous_status],
    currentStatusLabel: THRESHOLD_STATE_LABEL[record.current_status],
    currentStatusTone: THRESHOLD_STATE_TONE[record.current_status],
    observedValue: record.observed_value,
    requiredValue: record.required_value,
  };
}

/** Empty state shown before the adaptive loop has ever been started for
 * a decision - a normal, valid state, never an error. */
export const EMPTY_ADAPTIVE_LOOP_SUMMARY: AdaptiveLoopSummary = {
  found: false,
  stateId: '',
  cycleNumber: 0,
  statusLabel: '',
  statusTone: 'neutral',
  isConcluded: false,
  isBlocked: false,
  isUserStopped: false,
  currentAssessmentLabel: '',
  currentAssessmentTone: 'neutral',
  previousAssessmentLabel: null,
  assessmentChanged: false,
  currentPrimaryUncertaintyId: null,
  currentPrimaryThresholdId: null,
  currentExperimentId: null,
  previousExperimentId: null,
  nextAction: '',
  whyThisIsNext: null,
  stoppingReason: null,
  thresholdChanges: [],
  updatedAtLabel: '',
};

/**
 * Builds the "Decision Validation" panel's view model from a real
 * `ApiAdaptiveExperimentState`. `found=false` means the loop hasn't been
 * started yet (backend returned 404) - the normal case for a decision
 * that hasn't reached this stage.
 */
export function buildAdaptiveLoopSummary(
  state: ApiAdaptiveExperimentState | null,
): AdaptiveLoopSummary {
  if (state === null) return EMPTY_ADAPTIVE_LOOP_SUMMARY;

  return {
    found: true,
    stateId: state.state_id,
    cycleNumber: state.cycle_number,
    statusLabel: STATUS_LABEL[state.current_status],
    statusTone: STATUS_TONE[state.current_status],
    isConcluded: CONCLUDED_STATUSES.has(state.current_status),
    isBlocked: state.current_status === 'blocked',
    isUserStopped: state.current_status === 'user_stopped',
    currentAssessmentLabel: assessmentLabel(state.current_assessment),
    currentAssessmentTone: assessmentTone(state.current_assessment),
    previousAssessmentLabel: state.previous_assessment ? assessmentLabel(state.previous_assessment) : null,
    assessmentChanged:
      state.previous_assessment !== null && state.previous_assessment !== state.current_assessment,
    currentPrimaryUncertaintyId: state.current_primary_uncertainty_id,
    currentPrimaryThresholdId: state.current_primary_threshold_id,
    currentExperimentId: state.current_experiment_id,
    previousExperimentId: state.previous_experiment_id,
    nextAction: state.next_action,
    whyThisIsNext: state.why_this_is_next,
    stoppingReason: state.stopping_reason,
    thresholdChanges: state.uncertainty_status.map(buildThresholdRow),
    updatedAtLabel: formatRelative(state.updated_at),
  };
}

/** Builds the "Adaptive Decision Timeline" - every cycle ever recorded
 * for this decision, oldest first, exactly as returned by
 * `GET /decisions/{id}/adaptive/history`. Never re-sorted by anything
 * other than the backend's own `created_at`. */
export function buildAdaptiveCycleRows(history: ApiAdaptiveExperimentState[]): AdaptiveCycleRow[] {
  return history.map((state) => ({
    stateId: state.state_id,
    cycleNumber: state.cycle_number,
    statusLabel: STATUS_LABEL[state.current_status],
    statusTone: STATUS_TONE[state.current_status],
    currentAssessmentLabel: assessmentLabel(state.current_assessment),
    currentExperimentId: state.current_experiment_id,
    nextAction: state.next_action,
    createdAtLabel: formatRelative(state.created_at),
    sortKey: state.created_at,
  }));
}
