"""Adaptive Experiment Loop cycle logic (REGRET ENGINE 2.0, Step 21).

`AdaptiveExperimentService.advance_cycle` is the one operation this
module adds: given a decision, decide what should happen next in its
validation journey, using ONLY already-persisted, already-structured
data - no LLM call, no re-running any agent. Every input already exists
because of earlier steps:

    Threshold / Assumption / Blindspot / RegretScenario / Experiment
        (the analysis pipeline, existing)
    ExperimentResult / ReEvaluation
        (app.services.re_evaluation_service, existing)
    ValueOfInformationAnalysis
        (app.services.value_of_information_service, Step 20)
    DecisionMemory
        (app.memory.memory_service, Step 18 - read only for
         explainability text, never required for the cycle logic itself)

WHY AN EXPERIMENT IS NEVER BLINDLY REPEATED (spec section 5):

`_select_next_candidate` walks the freshest `ValueOfInformationAnalysis`'s
ranked uncertainties in order and skips any uncertainty whose linked
threshold has already reached a CONCLUSIVE state
(`ThresholdState.VALIDATED`/`FAILED`, derived from real
`ThresholdComparisonStatus` history in `_threshold_state`) or whose
linked experiment has already been completed. A cycle only ever proposes
a NOT-YET-RUN experiment - re-testing something only happens if a later
VOI recompute (which reads the CURRENT, possibly-changed evidence) marks
that threshold's state as no longer conclusive, which never happens by
itself; this service does not "reopen" a threshold on its own.

IDEMPOTENCY / CONCURRENCY (spec sections 12 & 22):

`advance_cycle` always computes the CANDIDATE next state first, derives
its `state_id` deterministically from
`(decision_id, cycle_number, current_status, current_experiment_id,
previous_result_id)`, and compares it against the latest EXISTING state.
If they match, nothing new is persisted - `advance_cycle` returns the
existing state with `AdvanceOutcome.NO_CHANGE`. This is what makes
calling `advance` twice with no new evidence a safe no-op, and what makes
two concurrent calls collide on the same DynamoDB item key rather than
each creating a duplicate "next" state - the repository's conditional
write (`Attr("PK").not_exists()`) guarantees only one of them wins; see
`app.adaptive.repository.AdaptiveStateRepository.create_adaptive_state`.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid5

from app.adaptive.repository import AdaptiveStateRepository
from app.adaptive.schemas import (
    AdaptiveAdvanceResponse,
    AdaptiveCycleStatus,
    AdaptiveExperimentState,
    AdvanceOutcome,
    DecisionValidationState,
    ThresholdCycleRecord,
    ThresholdState,
)
from app.agents.value_of_information import ValueOfInformationService
from app.agents.value_of_information_schemas import (
    ValueBand,
    ValueOfInformationAnalysis,
    ValueOfInformationItem,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.memory.memory_service import MemoryService
from app.repositories.decision_repository import DecisionRepository
from app.schemas.decision import DecisionResponse
from app.schemas.decision_resources import (
    Experiment,
    ExperimentStatus,
    ReEvaluation,
    Threshold,
    ThresholdComparisonStatus,
)

logger = get_logger(__name__)

# Deterministic namespace for adaptive-state ids - distinct from every
# other namespace already used in this codebase (memory learnings,
# historical insights) so id collisions across features are
# architecturally impossible, not just unlikely.
_ADAPTIVE_STATE_NAMESPACE = UUID("7c3f2a9e-4b6d-4e8a-9c1f-8a2d6e4b7f3c")

# Uncertainties scored below this band are never selected as the next
# experiment target, regardless of rank - see spec's "remaining
# uncertainty has low practical VOI" stopping condition.
_MINIMUM_WORTHWHILE_VALUE = {ValueBand.MEDIUM, ValueBand.HIGH, ValueBand.VERY_HIGH}

_CONCLUSIVE_THRESHOLD_STATES = {ThresholdState.VALIDATED, ThresholdState.FAILED}

_MET_LIKE = {ThresholdComparisonStatus.MET, ThresholdComparisonStatus.WITHIN_RANGE}
_MISSED_LIKE = {ThresholdComparisonStatus.MISSED, ThresholdComparisonStatus.OUTSIDE_RANGE}


class AdaptiveExperimentService:
    """Runs the closed-loop decision-validation cycle for one decision."""

    def __init__(
        self,
        decision_repository: DecisionRepository,
        adaptive_repository: AdaptiveStateRepository,
        voi_service: ValueOfInformationService,
        memory_service: MemoryService | None = None,
    ) -> None:
        self._decisions = decision_repository
        self._adaptive = adaptive_repository
        self._voi = voi_service
        # Optional: read-only, used only to enrich explainability text
        # (spec section 4 step 4) - never required for the cycle's own
        # decision logic. A missing/failed memory lookup never blocks a
        # cycle from advancing (spec section 22: "handle incomplete
        # memory").
        self._memory = memory_service

    # --- public API ------------------------------------------------------------

    def get_latest(self, decision_id: UUID) -> AdaptiveExperimentState | None:
        """The most recently recorded adaptive state for a decision, or
        `None` if the loop has never been started - never an error; a
        decision that hasn't reached this stage yet legitimately has
        nothing to report."""
        return self._adaptive.get_latest_adaptive_state(decision_id)

    def list_history(self, decision_id: UUID) -> list[AdaptiveExperimentState]:
        """Every adaptive state ever recorded for a decision, oldest
        first - the decision's full validation-journey history."""
        return self._adaptive.list_adaptive_states(decision_id)

    def advance_cycle(self, decision: DecisionResponse, user_id: str) -> AdaptiveAdvanceResponse:
        """Advance the decision to its next logical adaptive-loop state.

        Never raises for missing VOI/threshold/experiment/result data -
        each of those is treated as a legitimate "not enough to proceed"
        signal (`BLOCKED`/`INCONCLUSIVE`), never a crash. Idempotent: see
        module docstring.
        """
        decision_id = decision.id
        settings = get_settings()

        latest_state = self._adaptive.get_latest_adaptive_state(decision_id)
        reevaluations = self._decisions.list_reevaluations(decision_id)
        thresholds = self._decisions.list_thresholds(decision_id)
        experiments = self._decisions.list_experiments(decision_id)
        voi_analysis = self._voi.get_latest(decision_id)

        latest_reevaluation = (
            max(reevaluations, key=lambda r: r.created_at) if reevaluations else None
        )
        current_assessment = self._decision_validation_state(latest_reevaluation)
        threshold_states = {
            threshold.id: self._threshold_state(threshold, experiments, reevaluations)
            for threshold in thresholds
        }

        # A NEW cycle (an incremented cycle_number) only ever starts once
        # the previous cycle's experiment has produced a real result
        # (current_status == READY_FOR_NEXT_EXPERIMENT) or there was no
        # previous cycle at all. Re-advancing while still
        # AWAITING_EXPERIMENT, or while concluded/blocked, re-evaluates
        # the SAME cycle_number - this is what makes calling advance()
        # twice with no new evidence produce an identical candidate,
        # which `_same_transition` below then recognizes as a no-op.
        if latest_state is None:
            cycle_number = 1
        elif latest_state.current_status == AdaptiveCycleStatus.READY_FOR_NEXT_EXPERIMENT:
            cycle_number = latest_state.cycle_number + 1
        else:
            cycle_number = latest_state.cycle_number

        if voi_analysis is None:
            candidate = self._build_blocked_state(
                decision,
                user_id,
                latest_state,
                cycle_number,
                current_assessment,
                "No Value-of-Information analysis has been computed yet for this decision - "
                "run the analysis pipeline first.",
            )
        else:
            candidate = self._build_next_state(
                decision,
                user_id,
                latest_state,
                cycle_number,
                current_assessment,
                voi_analysis,
                thresholds,
                experiments,
                threshold_states,
                settings.max_adaptive_cycles,
            )

        if latest_state is not None and _same_transition(latest_state, candidate):
            logger.info(
                "Adaptive cycle advance was a no-op decision_id=%s state_id=%s status=%s",
                decision_id,
                latest_state.state_id,
                latest_state.current_status.value,
            )
            return AdaptiveAdvanceResponse(state=latest_state, outcome=AdvanceOutcome.NO_CHANGE)

        persisted, created = self._adaptive.create_adaptive_state(candidate)
        outcome = (
            AdvanceOutcome.NO_CHANGE
            if not created
            else AdvanceOutcome.STARTED_FIRST_CYCLE
            if latest_state is None
            else AdvanceOutcome.CONCLUDED
            if persisted.current_status
            in {
                AdaptiveCycleStatus.SUFFICIENTLY_VALIDATED,
                AdaptiveCycleStatus.INCONCLUSIVE,
                AdaptiveCycleStatus.BLOCKED,
            }
            else AdvanceOutcome.ADVANCED_TO_NEXT_EXPERIMENT
        )
        logger.info(
            "Adaptive cycle advanced decision_id=%s state_id=%s cycle=%d status=%s outcome=%s",
            decision_id,
            persisted.state_id,
            persisted.cycle_number,
            persisted.current_status.value,
            outcome.value,
        )
        return AdaptiveAdvanceResponse(state=persisted, outcome=outcome)

    def mark_experiment_completed(
        self, decision_id: UUID, experiment_id: UUID, result_id: UUID
    ) -> AdaptiveExperimentState | None:
        """Record that the experiment the current cycle was tracking now
        has a real result, WITHOUT selecting the next experiment yet -
        see spec section 13's explicitly preferred "safer approach": the
        result-submission endpoint only marks the state
        `ready_for_next_experiment`; the separate, explicit `advance`
        endpoint is what actually picks what runs next.

        A no-op (returns `None`, never raises) if the adaptive loop was
        never started for this decision, or if the latest state isn't
        currently tracking this exact experiment - e.g. a result was
        submitted for an experiment outside the loop's own tracked
        cycle. Never overwrites unrelated state.
        """
        latest = self._adaptive.get_latest_adaptive_state(decision_id)
        if latest is None:
            return None
        if latest.current_experiment_id != str(experiment_id):
            return None
        if latest.current_status != AdaptiveCycleStatus.AWAITING_EXPERIMENT:
            return None

        now = datetime.now(UTC)
        next_state = AdaptiveExperimentState(
            state_id=self._state_id_for(
                decision_id,
                latest.cycle_number,
                AdaptiveCycleStatus.READY_FOR_NEXT_EXPERIMENT,
                latest.current_experiment_id,
                str(result_id),
            ),
            decision_id=decision_id,
            user_id=latest.user_id,
            cycle_number=latest.cycle_number,
            current_status=AdaptiveCycleStatus.READY_FOR_NEXT_EXPERIMENT,
            current_primary_uncertainty_id=latest.current_primary_uncertainty_id,
            current_primary_threshold_id=latest.current_primary_threshold_id,
            current_experiment_id=latest.current_experiment_id,
            previous_experiment_id=latest.current_experiment_id,
            previous_result_id=str(result_id),
            previous_assessment=latest.current_assessment,
            current_assessment=latest.current_assessment,  # refreshed on the next advance() call
            uncertainty_status=[],
            stopping_reason=None,
            next_action=(
                "A result has been recorded for this cycle's experiment. Call "
                "POST /decisions/{id}/adaptive/advance to select the next uncertainty to test."
            ),
            why_this_is_next=None,
            created_at=now,
            updated_at=now,
        )
        persisted, _ = self._adaptive.create_adaptive_state(next_state)
        return persisted

    def stop(self, decision_id: UUID, reason: str | None = None) -> AdaptiveExperimentState | None:
        """The user manually stops the adaptive loop for this decision.
        Never deletes history - creates one final, clearly-marked state.
        """
        latest = self._adaptive.get_latest_adaptive_state(decision_id)
        if latest is None:
            return None
        now = datetime.now(UTC)
        stopped = latest.model_copy(
            update={
                "state_id": self._state_id_for(
                    decision_id,
                    latest.cycle_number,
                    AdaptiveCycleStatus.USER_STOPPED,
                    latest.current_experiment_id,
                    "user-stop",
                ),
                "current_status": AdaptiveCycleStatus.USER_STOPPED,
                "stopping_reason": reason or "Stopped by the user.",
                "next_action": (
                    "The adaptive loop has been stopped. No further experiments will be "
                    "recommended."
                ),
                "why_this_is_next": None,
                "created_at": now,
                "updated_at": now,
            }
        )
        persisted, _ = self._adaptive.create_adaptive_state(stopped)
        return persisted

    # --- internal: state derivation ---------------------------------------------

    def _build_blocked_state(
        self,
        decision: DecisionResponse,
        user_id: str,
        latest_state: AdaptiveExperimentState | None,
        cycle_number: int,
        current_assessment: DecisionValidationState,
        reason: str,
    ) -> AdaptiveExperimentState:
        now = datetime.now(UTC)
        return AdaptiveExperimentState(
            state_id=self._state_id_for(
                decision.id, cycle_number, AdaptiveCycleStatus.BLOCKED, None, reason
            ),
            decision_id=decision.id,
            user_id=user_id,
            cycle_number=cycle_number,
            current_status=AdaptiveCycleStatus.BLOCKED,
            current_primary_uncertainty_id=None,
            current_primary_threshold_id=None,
            current_experiment_id=None,
            previous_experiment_id=latest_state.current_experiment_id if latest_state else None,
            previous_result_id=latest_state.previous_result_id if latest_state else None,
            previous_assessment=latest_state.current_assessment if latest_state else None,
            current_assessment=current_assessment,
            uncertainty_status=[],
            stopping_reason=reason,
            next_action=reason,
            why_this_is_next=None,
            created_at=now,
            updated_at=now,
        )

    def _build_next_state(
        self,
        decision: DecisionResponse,
        user_id: str,
        latest_state: AdaptiveExperimentState | None,
        cycle_number: int,
        current_assessment: DecisionValidationState,
        voi_analysis: ValueOfInformationAnalysis,
        thresholds: list[Threshold],
        experiments: list[Experiment],
        threshold_states: dict[UUID, ThresholdState],
        max_cycles: int,
    ) -> AdaptiveExperimentState:
        now = datetime.now(UTC)
        threshold_states_by_str = {str(k): v for k, v in threshold_states.items()}
        experiments_by_id = {str(e.id): e for e in experiments}

        candidate_item, candidate_experiment, blocked_reason = self._select_next_candidate(
            voi_analysis, threshold_states_by_str, experiments_by_id
        )

        uncertainty_status = self._changed_threshold_records(
            latest_state, threshold_states, thresholds
        )
        previous_experiment_id = latest_state.current_experiment_id if latest_state else None
        previous_result_id = latest_state.previous_result_id if latest_state else None
        previous_assessment = latest_state.current_assessment if latest_state else None

        if candidate_item is not None and candidate_experiment is not None:
            if cycle_number > max_cycles:
                return AdaptiveExperimentState(
                    state_id=self._state_id_for(
                        decision.id,
                        cycle_number,
                        AdaptiveCycleStatus.BLOCKED,
                        None,
                        "max-cycles",
                    ),
                    decision_id=decision.id,
                    user_id=user_id,
                    cycle_number=cycle_number,
                    current_status=AdaptiveCycleStatus.BLOCKED,
                    current_primary_uncertainty_id=None,
                    current_primary_threshold_id=None,
                    current_experiment_id=None,
                    previous_experiment_id=previous_experiment_id,
                    previous_result_id=previous_result_id,
                    previous_assessment=previous_assessment,
                    current_assessment=current_assessment,
                    uncertainty_status=uncertainty_status,
                    stopping_reason=(
                        f"Maximum number of adaptive cycles ({max_cycles}) has been reached."
                    ),
                    next_action=(
                        "This decision has reached the maximum number of adaptive test cycles. "
                        "Review the accumulated evidence manually before continuing."
                    ),
                    why_this_is_next=None,
                    created_at=now,
                    updated_at=now,
                )

            threshold_id = (
                candidate_item.related_threshold_ids[0]
                if candidate_item.related_threshold_ids
                else None
            )
            why = (
                f"{candidate_item.rationale} This is the highest-ranked uncertainty that has not "
                "already been conclusively tested."
            )
            return AdaptiveExperimentState(
                state_id=self._state_id_for(
                    decision.id,
                    cycle_number,
                    AdaptiveCycleStatus.AWAITING_EXPERIMENT,
                    str(candidate_experiment.id),
                    previous_result_id,
                ),
                decision_id=decision.id,
                user_id=user_id,
                cycle_number=cycle_number,
                current_status=AdaptiveCycleStatus.AWAITING_EXPERIMENT,
                current_primary_uncertainty_id=candidate_item.uncertainty_id,
                current_primary_threshold_id=threshold_id,
                current_experiment_id=str(candidate_experiment.id),
                previous_experiment_id=previous_experiment_id,
                previous_result_id=previous_result_id,
                previous_assessment=previous_assessment,
                current_assessment=current_assessment,
                uncertainty_status=uncertainty_status,
                stopping_reason=None,
                next_action=(
                    f"Run the recommended experiment ('{candidate_experiment.title}') and submit "
                    "its real-world result."
                ),
                why_this_is_next=why,
                created_at=now,
                updated_at=now,
            )

        # No runnable candidate. Decide BLOCKED vs SUFFICIENTLY_VALIDATED vs INCONCLUSIVE.
        if blocked_reason is not None:
            status = AdaptiveCycleStatus.INCONCLUSIVE
            stopping_reason = blocked_reason
        else:
            status = AdaptiveCycleStatus.SUFFICIENTLY_VALIDATED
            stopping_reason = (
                "Every uncertainty with meaningful practical value to resolve has already been "
                "conclusively tested, or the uncertainty that remains has low practical value to "
                "resolve relative to the effort required."
            )

        return AdaptiveExperimentState(
            state_id=self._state_id_for(decision.id, cycle_number, status, None, stopping_reason),
            decision_id=decision.id,
            user_id=user_id,
            cycle_number=cycle_number,
            current_status=status,
            current_primary_uncertainty_id=None,
            current_primary_threshold_id=None,
            current_experiment_id=None,
            previous_experiment_id=previous_experiment_id,
            previous_result_id=previous_result_id,
            previous_assessment=previous_assessment,
            current_assessment=current_assessment,
            uncertainty_status=uncertainty_status,
            stopping_reason=stopping_reason,
            next_action=(
                "No further testing is recommended right now."
                if status == AdaptiveCycleStatus.SUFFICIENTLY_VALIDATED
                else "Review the decision manually - the remaining uncertainty could not be "
                "resolved with a feasible experiment."
            ),
            why_this_is_next=None,
            created_at=now,
            updated_at=now,
        )

    def _select_next_candidate(
        self,
        voi_analysis: ValueOfInformationAnalysis,
        threshold_states: dict[str, ThresholdState],
        experiments_by_id: dict[str, Experiment],
    ) -> tuple[ValueOfInformationItem | None, Experiment | None, str | None]:
        """Walk the ranked uncertainties in order, skipping anything
        already conclusively tested, and return the first one that both
        has meaningful practical value AND a real, not-yet-completed
        experiment. See module docstring for why an already-tested
        threshold is never re-selected.

        Returns `(item, experiment, blocked_reason)`. `blocked_reason` is
        set only when at least one uncertainty still has meaningful value
        but no feasible (not-yet-run) experiment exists for it - this is
        the INCONCLUSIVE case, distinct from "everything worthwhile is
        already resolved" (SUFFICIENTLY_VALIDATED).
        """
        blocked_reason: str | None = None
        for item in voi_analysis.ranked_uncertainties:
            if item.practical_value not in _MINIMUM_WORTHWHILE_VALUE:
                continue

            threshold_id = item.related_threshold_ids[0] if item.related_threshold_ids else None
            if threshold_id is not None:
                state = threshold_states.get(threshold_id, ThresholdState.UNKNOWN)
                if state in _CONCLUSIVE_THRESHOLD_STATES:
                    continue  # already conclusively tested - never repeat without new evidence

            experiment = (
                experiments_by_id.get(item.related_experiment_id)
                if item.related_experiment_id
                else None
            )
            if experiment is None:
                if blocked_reason is None:
                    blocked_reason = (
                        f"'{item.title}' still has meaningful practical value to resolve, but no "
                        "experiment has been recommended for it yet."
                    )
                continue
            if experiment.status == ExperimentStatus.COMPLETED:
                # Already run once - do not blindly repeat it. It remains
                # skipped even if its threshold state is technically
                # inconclusive; genuinely reopening it requires new
                # evidence this service does not fabricate on its own.
                continue
            if experiment.status == ExperimentStatus.CANCELLED:
                if blocked_reason is None:
                    blocked_reason = (
                        f"The experiment recommended for '{item.title}' was cancelled and no "
                        "replacement has been recommended."
                    )
                continue

            return item, experiment, None

        return None, None, blocked_reason

    def _changed_threshold_records(
        self,
        latest_state: AdaptiveExperimentState | None,
        threshold_states: dict[UUID, ThresholdState],
        thresholds: list[Threshold],
    ) -> list[ThresholdCycleRecord]:
        """Only the thresholds whose state actually differs from the
        previous cycle's own recorded state - see
        `ThresholdCycleRecord`'s docstring: never a fabricated
        "nothing changed" record for every threshold."""
        previous_by_id = (
            {
                record.threshold_id: record.current_status
                for record in latest_state.uncertainty_status
            }
            if latest_state
            else {}
        )
        thresholds_by_id = {t.id: t for t in thresholds}
        records: list[ThresholdCycleRecord] = []
        for threshold_id, state in threshold_states.items():
            previous = previous_by_id.get(str(threshold_id), ThresholdState.UNKNOWN)
            if previous == state:
                continue
            threshold = thresholds_by_id.get(threshold_id)
            records.append(
                ThresholdCycleRecord(
                    threshold_id=str(threshold_id),
                    previous_status=previous,
                    current_status=state,
                    observed_value=None,
                    required_value=threshold.threshold_value if threshold else None,
                    confidence=threshold.confidence if threshold else None,
                    validation_status=threshold.validation_status if threshold else None,
                )
            )
        return records

    @staticmethod
    def _threshold_state(
        threshold: Threshold, experiments: list[Experiment], reevaluations: list[ReEvaluation]
    ) -> ThresholdState:
        """Deterministically derive a threshold's current standing in the
        validation journey from real, already-persisted history - never
        guessed. See module docstring."""
        comparisons = [
            (reevaluation.created_at, comparison)
            for reevaluation in reevaluations
            for comparison in reevaluation.threshold_comparisons
            if comparison.threshold_id == str(threshold.id)
        ]
        if comparisons:
            _, latest_comparison = max(comparisons, key=lambda pair: pair[0])
            if latest_comparison.status in _MET_LIKE:
                return ThresholdState.VALIDATED
            if latest_comparison.status in _MISSED_LIKE:
                return ThresholdState.FAILED
            return ThresholdState.INCONCLUSIVE

        active_statuses = {
            ExperimentStatus.RECOMMENDED,
            ExperimentStatus.PLANNED,
            ExperimentStatus.ACTIVE,
        }
        has_active_experiment = any(
            e.target_threshold_id == str(threshold.id) and e.status in active_statuses
            for e in experiments
        )
        if has_active_experiment:
            return ThresholdState.UNDER_TEST
        if threshold.validation_status in {"provisional", "validated"}:
            return ThresholdState.PROVISIONAL
        return ThresholdState.UNKNOWN

    @staticmethod
    def _decision_validation_state(reevaluation: ReEvaluation | None) -> DecisionValidationState:
        """Deterministic mapping from the latest real `DecisionAssessment`
        (status + confidence, both already computed by
        `app.services.re_evaluation_service` - never recomputed here) to
        the adaptive loop's own evidence-state vocabulary. See
        `DecisionValidationState`'s own docstring: this is an evidence
        state, never a probability and never a verdict."""
        if reevaluation is None:
            return DecisionValidationState.INSUFFICIENT_EVIDENCE

        assessment = reevaluation.decision_assessment
        status = assessment.status
        confidence = assessment.confidence

        if status == "strengthened":
            return (
                DecisionValidationState.STRONGLY_SUPPORTED
                if confidence >= 0.7
                else DecisionValidationState.SUPPORTED
            )
        if status == "weakened":
            return (
                DecisionValidationState.STRONGLY_WEAKENED
                if confidence >= 0.7
                else DecisionValidationState.WEAKENED
            )
        if status == "unchanged":
            return DecisionValidationState.PARTIALLY_SUPPORTED
        if status == "inconclusive":
            return DecisionValidationState.INCONCLUSIVE
        return DecisionValidationState.REQUIRES_MORE_TESTING

    @staticmethod
    def _state_id_for(
        decision_id: UUID,
        cycle_number: int,
        status: AdaptiveCycleStatus,
        experiment_id: str | None,
        discriminator: str | None,
    ) -> UUID:
        """Deterministic state id - see module docstring's concurrency
        section. Two calls with identical (decision, cycle, status,
        experiment, discriminator) always produce the same id, which is
        exactly what makes duplicate/concurrent advancement safe."""
        return uuid5(
            _ADAPTIVE_STATE_NAMESPACE,
            f"adaptive:{decision_id}:{cycle_number}:{status.value}:{experiment_id}:{discriminator}",
        )


def _same_transition(existing: AdaptiveExperimentState, candidate: AdaptiveExperimentState) -> bool:
    """Whether `candidate` describes the exact same transition as the
    latest EXISTING state - i.e. nothing meaningful has changed since
    the last advance() call. Compares only the fields that describe the
    decision (never timestamps/ids), so a genuinely identical situation
    is recognized regardless of when it was computed."""
    return (
        existing.current_status == candidate.current_status
        and existing.current_primary_uncertainty_id == candidate.current_primary_uncertainty_id
        and existing.current_experiment_id == candidate.current_experiment_id
        and existing.current_assessment == candidate.current_assessment
        and existing.cycle_number == candidate.cycle_number
        and existing.stopping_reason == candidate.stopping_reason
    )
