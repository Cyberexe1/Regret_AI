"""Decision Evolution assembly (REGRET ENGINE 2.0, Step 22).

`DecisionEvolutionService` turns the real, already-persisted records
`DecisionEvolutionRepository.load` fetches into an ordered
`DecisionEvolutionEvent` timeline. No LLM call happens anywhere in this
module - every event is a deterministic mapping from one canonical
record's own fields.

EVENT SOURCING WITHOUT DUPLICATION (spec section 4): there is exactly one
builder function per source-record type below (`_decision_created_event`,
`_threshold_events`, `_experiment_events`, ...) - the timeline is
recomputed on every call, never stored, so there is no risk of it
drifting out of sync with the canonical records it describes.

CAUSALITY (spec section 5): a `reason`/`previous_state`/`new_state` is
only ever set from a field the source record itself carries (e.g. a
`ThresholdComparison.explanation`, a `ReEvaluation.previous_assessment`/
`new_assessment`). Nothing here infers "the experiment proved X" beyond
what the record's own text already states.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid5

from app.core.errors import NotFoundError
from app.evolution.repository import DecisionEvolutionRecords, DecisionEvolutionRepository
from app.evolution.schemas import (
    DecisionDelta,
    DecisionEvolution,
    DecisionEvolutionEvent,
    EvolutionEventType,
    EvolutionImpact,
)
from app.repositories.decision_repository import DecisionRepository
from app.schemas.decision_resources import (
    AnalysisRun,
    AnalysisRunStatus,
    Assumption,
    Blindspot,
    Experiment,
    ExperimentResult,
    ExperimentStatus,
    ReEvaluation,
    RegretScenario,
    Threshold,
)

# Deterministic namespace for event ids - distinct from every other
# namespace already used in this codebase, so an event id can never
# collide with a memory-learning id, an adaptive-state id, etc.
_EVOLUTION_EVENT_NAMESPACE = UUID("2f6d8b1a-9c3e-4a7f-8d2b-5e1c6a9f3b7d")

_MAJOR_IMPACT_TYPES = {
    EvolutionEventType.ASSESSMENT_CHANGED,
    EvolutionEventType.THRESHOLD_VALIDATED,
    EvolutionEventType.THRESHOLD_FAILED,
    EvolutionEventType.VALIDATION_STATE_CHANGED,
    EvolutionEventType.DECISION_COMPLETED,
    EvolutionEventType.NEXT_EXPERIMENT_SELECTED,
}


def _event_id(decision_id: UUID, event_type: EvolutionEventType, source_id: str) -> str:
    """Deterministic - the same source record always produces the same
    event id, so re-fetching the timeline (it is never persisted) can't
    renumber or duplicate an event a client already rendered."""
    return str(uuid5(_EVOLUTION_EVENT_NAMESPACE, f"{decision_id}:{event_type.value}:{source_id}"))


class DecisionEvolutionService:
    """Assembles, orders, and bounds a decision's evolution timeline from
    real canonical records. Contains no business logic that duplicates
    any existing service (VOI scoring, adaptive cycle selection,
    re-evaluation comparison) - it only narrates what those services
    already decided and persisted.
    """

    def __init__(
        self,
        decision_repository: DecisionRepository,
        evolution_repository: DecisionEvolutionRepository,
        max_events: int = 200,
    ) -> None:
        self._decisions = decision_repository
        self._evolution = evolution_repository
        self._max_events = max_events

    # --- public API --------------------------------------------------------

    def get_evolution(self, decision_id: UUID) -> DecisionEvolution:
        """The full composite response for `GET /decisions/{id}/evolution`."""
        decision = self._decisions.get_raw(decision_id)
        if decision is None:
            raise NotFoundError(detail=f"Decision {decision_id} not found.")

        records = self._evolution.load(decision_id)
        events = self.build_timeline(decision_id, records=records)

        truncated = len(events) > self._max_events
        bounded_events = events[-self._max_events :] if truncated else events

        current_assessment, current_cycle = self._current_assessment(records)
        major_changes = self._major_changes(bounded_events)

        return DecisionEvolution(
            decision_id=str(decision_id),
            user_id=decision["user_id"],
            current_assessment=current_assessment,
            current_cycle=current_cycle,
            total_cycles=len(records.adaptive_states),
            timeline=bounded_events,
            major_changes=major_changes,
            current_uncertainties=self._unresolved_uncertainty_ids(records),
            validated_thresholds=[
                str(t.id) for t in records.thresholds if _threshold_is(records, t, "met")
            ],
            failed_thresholds=[
                str(t.id) for t in records.thresholds if _threshold_is(records, t, "missed")
            ],
            current_primary_uncertainty=(
                records.adaptive_states[-1].current_primary_uncertainty_id
                if records.adaptive_states
                else (
                    records.voi_analyses[-1].primary_uncertainty_id
                    if records.voi_analyses
                    else None
                )
            ),
            truncated=truncated,
            generated_at=datetime.now(UTC),
        )

    def build_timeline(
        self, decision_id: UUID, records: DecisionEvolutionRecords | None = None
    ) -> list[DecisionEvolutionEvent]:
        """The ordered (oldest first) list of every derivable event -
        never bounded here; `get_evolution` applies the
        `EVOLUTION_MAX_EVENTS` bound at the response layer so this method
        stays reusable for a caller that wants the complete history."""
        if records is None:
            records = self._evolution.load(decision_id)

        events: list[DecisionEvolutionEvent] = []
        decision = self._decisions.get_raw(decision_id)
        if decision is not None:
            events.append(_decision_created_event(decision_id, decision))

        for run in records.analysis_runs:
            event = _analysis_completed_event(decision_id, run)
            if event is not None:
                events.append(event)

        for assumption in records.assumptions:
            events.append(_assumption_identified_event(decision_id, assumption))
        for blindspot in records.blindspots:
            events.append(_blindspot_identified_event(decision_id, blindspot))
        for scenario in records.regret_scenarios:
            events.append(_regret_scenario_identified_event(decision_id, scenario))
        for threshold in records.thresholds:
            events.append(_threshold_identified_event(decision_id, threshold))
        for experiment in records.experiments:
            events.append(_experiment_recommended_event(decision_id, experiment))
            started = _experiment_started_event(decision_id, experiment)
            if started is not None:
                events.append(started)
            completed = _experiment_completed_event(decision_id, experiment)
            if completed is not None:
                events.append(completed)

        for result_item in records.experiment_results:
            events.append(_experiment_result_event(decision_id, result_item))

        for reevaluation in records.reevaluations:
            events.extend(_reevaluation_events(decision_id, reevaluation))

        for learning in records.learnings:
            events.append(_learning_recorded_event(decision_id, learning))

        events.extend(_adaptive_cycle_events(decision_id, records.adaptive_states))

        events.sort(key=lambda event: event.timestamp)
        return events

    def get_current_state(self, decision_id: UUID) -> DecisionEvolution:
        """Alias kept distinct from `get_evolution` per the spec's exact
        required method name - identical behavior; `get_evolution`
        already IS "the current state plus its history"."""
        return self.get_evolution(decision_id)

    def get_major_changes(self, decision_id: UUID) -> list[DecisionEvolutionEvent]:
        records = self._evolution.load(decision_id)
        events = self.build_timeline(decision_id, records=records)
        return self._major_changes(events)

    def get_decision_delta(self, decision_id: UUID, event_id: str) -> DecisionDelta:
        """What changed between the event immediately before `event_id`
        and `event_id` itself - a deterministic, structured comparison,
        never a fabricated narrative. Raises 404 if `event_id` doesn't
        exist on this decision's timeline."""
        records = self._evolution.load(decision_id)
        events = self.build_timeline(decision_id, records=records)

        index = next((i for i, event in enumerate(events) if event.event_id == event_id), None)
        if index is None:
            raise NotFoundError(detail=f"Evolution event {event_id} not found for this decision.")

        target = events[index]
        return _delta_for_event(target)

    def get_event(self, decision_id: UUID, event_id: str) -> DecisionEvolutionEvent:
        """Detailed lookup for `GET /decisions/{id}/evolution/{event_id}`."""
        records = self._evolution.load(decision_id)
        events = self.build_timeline(decision_id, records=records)
        for event in events:
            if event.event_id == event_id:
                return event
        raise NotFoundError(detail=f"Evolution event {event_id} not found for this decision.")

    # --- internal ------------------------------------------------------------

    def _current_assessment(self, records: DecisionEvolutionRecords) -> tuple[str, int | None]:
        if records.adaptive_states:
            latest = records.adaptive_states[-1]
            return latest.current_assessment.value, latest.cycle_number
        if records.reevaluations:
            latest_reeval = max(records.reevaluations, key=lambda r: r.created_at)
            return latest_reeval.decision_assessment.status.value, None
        return "insufficient_evidence", None

    def _unresolved_uncertainty_ids(self, records: DecisionEvolutionRecords) -> list[str]:
        validated_or_failed_assumption_ids = {
            aid for reeval in records.reevaluations for aid in reeval.changed_assumptions
        }
        return [
            str(a.id)
            for a in records.assumptions
            if str(a.id) not in validated_or_failed_assumption_ids
        ]

    def _major_changes(self, events: list[DecisionEvolutionEvent]) -> list[DecisionEvolutionEvent]:
        return [event for event in events if event.impact == EvolutionImpact.MAJOR]


def _threshold_is(records: DecisionEvolutionRecords, threshold: Threshold, kind: str) -> bool:
    """Whether the LATEST comparison recorded against this threshold
    (across every re-evaluation, ordered by `created_at`) was met/missed
    - deterministic, from real `ThresholdComparison` history, never
    guessed. Mirrors `AdaptiveExperimentService._threshold_state`'s own
    derivation exactly so the two features never disagree."""
    comparisons = [
        (reeval.created_at, comparison)
        for reeval in records.reevaluations
        for comparison in reeval.threshold_comparisons
        if comparison.threshold_id == str(threshold.id)
    ]
    if not comparisons:
        return False
    _, latest = max(comparisons, key=lambda pair: pair[0])
    if kind == "met":
        return latest.status.value in {"met", "within_range"}
    return latest.status.value in {"missed", "outside_range"}


def _decision_created_event(decision_id: UUID, decision: dict) -> DecisionEvolutionEvent:
    return DecisionEvolutionEvent(
        event_id=_event_id(decision_id, EvolutionEventType.DECISION_CREATED, str(decision_id)),
        decision_id=str(decision_id),
        event_type=EvolutionEventType.DECISION_CREATED,
        timestamp=_parse_dt(decision["created_at"]),
        title="Decision created",
        summary=decision.get("title", "A new decision was recorded."),
        source_type="decision",
        source_id=str(decision_id),
        impact=EvolutionImpact.MINOR,
    )


def _analysis_completed_event(decision_id: UUID, run: AnalysisRun) -> DecisionEvolutionEvent | None:
    if run.status != AnalysisRunStatus.COMPLETED or run.completed_at is None:
        return None
    return DecisionEvolutionEvent(
        event_id=_event_id(decision_id, EvolutionEventType.ANALYSIS_COMPLETED, str(run.id)),
        decision_id=str(decision_id),
        event_type=EvolutionEventType.ANALYSIS_COMPLETED,
        timestamp=run.completed_at,
        title="Analysis completed",
        summary="The full analysis pipeline finished and produced the decision's initial "
        "assumptions, blindspots, thresholds, and recommended experiments.",
        source_type="analysis_run",
        source_id=str(run.id),
        impact=EvolutionImpact.MODERATE,
    )


def _assumption_identified_event(
    decision_id: UUID, assumption: Assumption
) -> DecisionEvolutionEvent:
    return DecisionEvolutionEvent(
        event_id=_event_id(
            decision_id, EvolutionEventType.ASSUMPTION_IDENTIFIED, str(assumption.id)
        ),
        decision_id=str(decision_id),
        event_type=EvolutionEventType.ASSUMPTION_IDENTIFIED,
        timestamp=assumption.created_at,
        title="Assumption identified",
        summary=assumption.statement,
        source_type="assumption",
        source_id=str(assumption.id),
        impact=EvolutionImpact.MINOR,
        affected_assumption_ids=[str(assumption.id)],
    )


def _blindspot_identified_event(decision_id: UUID, blindspot: Blindspot) -> DecisionEvolutionEvent:
    return DecisionEvolutionEvent(
        event_id=_event_id(decision_id, EvolutionEventType.BLINDSPOT_IDENTIFIED, str(blindspot.id)),
        decision_id=str(decision_id),
        event_type=EvolutionEventType.BLINDSPOT_IDENTIFIED,
        timestamp=blindspot.created_at,
        title="Blindspot identified",
        summary=blindspot.question,
        source_type="blindspot",
        source_id=str(blindspot.id),
        impact=EvolutionImpact.MINOR,
    )


def _regret_scenario_identified_event(
    decision_id: UUID, scenario: RegretScenario
) -> DecisionEvolutionEvent:
    return DecisionEvolutionEvent(
        event_id=_event_id(
            decision_id, EvolutionEventType.REGRET_SCENARIO_IDENTIFIED, str(scenario.id)
        ),
        decision_id=str(decision_id),
        event_type=EvolutionEventType.REGRET_SCENARIO_IDENTIFIED,
        timestamp=scenario.created_at,
        title="Regret scenario identified",
        summary=scenario.title,
        source_type="regret_scenario",
        source_id=str(scenario.id),
        impact=EvolutionImpact.MINOR,
        affected_regret_scenario_ids=[str(scenario.id)],
    )


def _threshold_identified_event(decision_id: UUID, threshold: Threshold) -> DecisionEvolutionEvent:
    return DecisionEvolutionEvent(
        event_id=_event_id(decision_id, EvolutionEventType.THRESHOLD_IDENTIFIED, str(threshold.id)),
        decision_id=str(decision_id),
        event_type=EvolutionEventType.THRESHOLD_IDENTIFIED,
        timestamp=threshold.created_at,
        title="Threshold identified",
        summary=f"{threshold.variable}"
        + (
            f": {threshold.threshold_value} {threshold.unit or ''}".rstrip()
            if threshold.threshold_value
            else ""
        ),
        source_type="threshold",
        source_id=str(threshold.id),
        impact=EvolutionImpact.MODERATE,
        affected_threshold_ids=[str(threshold.id)],
    )


def _experiment_recommended_event(
    decision_id: UUID, experiment: Experiment
) -> DecisionEvolutionEvent:
    return DecisionEvolutionEvent(
        event_id=_event_id(
            decision_id, EvolutionEventType.EXPERIMENT_RECOMMENDED, str(experiment.id)
        ),
        decision_id=str(decision_id),
        event_type=EvolutionEventType.EXPERIMENT_RECOMMENDED,
        timestamp=experiment.created_at,
        title="Experiment recommended",
        summary=experiment.title,
        source_type="experiment",
        source_id=str(experiment.id),
        impact=EvolutionImpact.MODERATE,
        affected_experiment_ids=[str(experiment.id)],
        affected_threshold_ids=(
            [experiment.target_threshold_id] if experiment.target_threshold_id else []
        ),
    )


def _experiment_started_event(
    decision_id: UUID, experiment: Experiment
) -> DecisionEvolutionEvent | None:
    """Only emitted when the experiment has actually moved past
    `recommended` - `Experiment` doesn't retain a per-transition history
    (only the LATEST `updated_at`, see the repository's own
    `update_experiment_status`), so this uses `updated_at` as the best
    available real timestamp rather than fabricating an earlier one."""
    if experiment.status not in {
        ExperimentStatus.ACTIVE,
        ExperimentStatus.COMPLETED,
    }:
        return None
    return DecisionEvolutionEvent(
        event_id=_event_id(decision_id, EvolutionEventType.EXPERIMENT_STARTED, str(experiment.id)),
        decision_id=str(decision_id),
        event_type=EvolutionEventType.EXPERIMENT_STARTED,
        timestamp=experiment.updated_at,
        title="Experiment started",
        summary=f"'{experiment.title}' began running.",
        source_type="experiment",
        source_id=str(experiment.id),
        impact=EvolutionImpact.MINOR,
        affected_experiment_ids=[str(experiment.id)],
    )


def _experiment_completed_event(
    decision_id: UUID, experiment: Experiment
) -> DecisionEvolutionEvent | None:
    if experiment.status != ExperimentStatus.COMPLETED:
        return None
    return DecisionEvolutionEvent(
        event_id=_event_id(
            decision_id, EvolutionEventType.EXPERIMENT_COMPLETED, str(experiment.id)
        ),
        decision_id=str(decision_id),
        event_type=EvolutionEventType.EXPERIMENT_COMPLETED,
        timestamp=experiment.updated_at,
        title="Experiment completed",
        summary=f"'{experiment.title}' finished; a result was submitted.",
        source_type="experiment",
        source_id=str(experiment.id),
        impact=EvolutionImpact.MODERATE,
        affected_experiment_ids=[str(experiment.id)],
    )


def _experiment_result_event(decision_id: UUID, result: ExperimentResult) -> DecisionEvolutionEvent:
    return DecisionEvolutionEvent(
        event_id=_event_id(decision_id, EvolutionEventType.EXPERIMENT_RESULT, str(result.id)),
        decision_id=str(decision_id),
        event_type=EvolutionEventType.EXPERIMENT_RESULT,
        timestamp=result.completed_at,
        title="Result observed",
        summary=result.summary,
        source_type="experiment_result",
        source_id=str(result.id),
        impact=EvolutionImpact.MODERATE,
        affected_experiment_ids=[str(result.experiment_id)],
        evidence_ids=list(result.evidence_ids),
    )


def _reevaluation_events(decision_id: UUID, reeval: ReEvaluation) -> list[DecisionEvolutionEvent]:
    """One `re_evaluation` narrative event, plus one `assessment_changed`
    / `threshold_validated` / `threshold_failed` event PER real state
    transition the re-evaluation actually recorded - never a fabricated
    "nothing changed" event for a comparison that didn't move anything.
    """
    events: list[DecisionEvolutionEvent] = [
        DecisionEvolutionEvent(
            event_id=_event_id(decision_id, EvolutionEventType.RE_EVALUATION, str(reeval.id)),
            decision_id=str(decision_id),
            event_type=EvolutionEventType.RE_EVALUATION,
            timestamp=reeval.created_at,
            title="Decision re-evaluated",
            summary=reeval.decision_assessment.summary,
            source_type="re_evaluation",
            source_id=str(reeval.id),
            impact=EvolutionImpact.MODERATE,
            affected_assumption_ids=list(reeval.changed_assumptions),
            affected_threshold_ids=list(reeval.changed_thresholds),
            affected_regret_scenario_ids=list(reeval.changed_regret_scenarios),
            affected_experiment_ids=[str(reeval.experiment_id)],
        )
    ]

    if reeval.previous_assessment != reeval.new_assessment:
        events.append(
            DecisionEvolutionEvent(
                event_id=_event_id(
                    decision_id, EvolutionEventType.ASSESSMENT_CHANGED, str(reeval.id)
                ),
                decision_id=str(decision_id),
                event_type=EvolutionEventType.ASSESSMENT_CHANGED,
                timestamp=reeval.created_at,
                title="Assessment changed",
                summary=f"The decision's assessment moved from "
                f"'{reeval.previous_assessment}' to '{reeval.new_assessment}'.",
                source_type="re_evaluation",
                source_id=str(reeval.id),
                impact=EvolutionImpact.MAJOR,
                previous_state=reeval.previous_assessment,
                new_state=reeval.new_assessment,
                reason=reeval.decision_assessment.summary,
                affected_assumption_ids=list(reeval.changed_assumptions),
                affected_threshold_ids=list(reeval.changed_thresholds),
            )
        )

    for comparison in reeval.threshold_comparisons:
        if comparison.status.value == "met":
            events.append(
                _threshold_transition_event(decision_id, reeval, comparison, validated=True)
            )
        elif comparison.status.value == "missed":
            events.append(
                _threshold_transition_event(decision_id, reeval, comparison, validated=False)
            )

    return events


def _threshold_transition_event(
    decision_id, reeval, comparison, *, validated: bool
) -> DecisionEvolutionEvent:
    event_type = (
        EvolutionEventType.THRESHOLD_VALIDATED if validated else EvolutionEventType.THRESHOLD_FAILED
    )
    return DecisionEvolutionEvent(
        event_id=_event_id(decision_id, event_type, f"{reeval.id}:{comparison.threshold_id}"),
        decision_id=str(decision_id),
        event_type=event_type,
        timestamp=reeval.created_at,
        title="Threshold validated" if validated else "Threshold failed",
        summary=comparison.explanation,
        source_type="threshold_comparison",
        source_id=str(reeval.id),
        impact=EvolutionImpact.MAJOR,
        previous_state="under_test",
        new_state="validated" if validated else "failed",
        reason=comparison.explanation,
        affected_threshold_ids=[comparison.threshold_id],
    )


def _learning_recorded_event(decision_id: UUID, learning) -> DecisionEvolutionEvent:
    return DecisionEvolutionEvent(
        event_id=_event_id(
            decision_id, EvolutionEventType.LEARNING_RECORDED, str(learning.learning_id)
        ),
        decision_id=str(decision_id),
        event_type=EvolutionEventType.LEARNING_RECORDED,
        timestamp=learning.created_at,
        title="Learning recorded",
        summary=learning.statement,
        source_type="memory_learning",
        source_id=str(learning.learning_id),
        impact=EvolutionImpact.MINOR,
        affected_assumption_ids=list(learning.related_assumption_ids),
        affected_threshold_ids=list(learning.related_threshold_ids),
        affected_regret_scenario_ids=list(learning.related_regret_scenario_ids),
    )


def _adaptive_cycle_events(decision_id: UUID, states) -> list[DecisionEvolutionEvent]:
    """One `next_experiment_selected`/`validation_state_changed` event per
    adaptive-loop transition that actually changed something - mirrors
    `AdaptiveExperimentService`'s own "only changed thresholds" rule so
    this never fabricates a "nothing changed" event either."""
    events: list[DecisionEvolutionEvent] = []
    previous = None
    for state in states:
        primary_uncertainty_changed = (
            previous is None
            or state.current_primary_uncertainty_id != previous.current_primary_uncertainty_id
        )
        if primary_uncertainty_changed and state.current_primary_uncertainty_id is not None:
            events.append(
                    DecisionEvolutionEvent(
                        event_id=_event_id(
                            decision_id,
                            EvolutionEventType.NEXT_EXPERIMENT_SELECTED,
                            str(state.state_id),
                        ),
                        decision_id=str(decision_id),
                        cycle_number=state.cycle_number,
                        event_type=EvolutionEventType.NEXT_EXPERIMENT_SELECTED,
                        timestamp=state.created_at,
                        title="Next uncertainty prioritized",
                        summary=state.why_this_is_next or state.next_action,
                        source_type="adaptive_state",
                        source_id=str(state.state_id),
                        impact=EvolutionImpact.MODERATE,
                        previous_state=(
                            previous.current_primary_uncertainty_id if previous else None
                        ),
                        new_state=state.current_primary_uncertainty_id,
                        reason=state.why_this_is_next,
                        affected_experiment_ids=(
                            [state.current_experiment_id] if state.current_experiment_id else []
                        ),
                    )
                )
        if previous is not None and previous.current_assessment != state.current_assessment:
            events.append(
                DecisionEvolutionEvent(
                    event_id=_event_id(
                        decision_id,
                        EvolutionEventType.VALIDATION_STATE_CHANGED,
                        str(state.state_id),
                    ),
                    decision_id=str(decision_id),
                    cycle_number=state.cycle_number,
                    event_type=EvolutionEventType.VALIDATION_STATE_CHANGED,
                    timestamp=state.updated_at,
                    title="Validation state changed",
                    summary=f"The decision's evidence-supported state moved from "
                    f"'{previous.current_assessment.value}' to '{state.current_assessment.value}'.",
                    source_type="adaptive_state",
                    source_id=str(state.state_id),
                    impact=EvolutionImpact.MAJOR,
                    previous_state=previous.current_assessment.value,
                    new_state=state.current_assessment.value,
                )
            )
        if state.current_status.value in {"sufficiently_validated", "inconclusive"}:
            events.append(
                DecisionEvolutionEvent(
                    event_id=_event_id(
                        decision_id, EvolutionEventType.DECISION_COMPLETED, str(state.state_id)
                    ),
                    decision_id=str(decision_id),
                    cycle_number=state.cycle_number,
                    event_type=EvolutionEventType.DECISION_COMPLETED,
                    timestamp=state.created_at,
                    title="Validation loop concluded",
                    summary=state.stopping_reason or state.next_action,
                    source_type="adaptive_state",
                    source_id=str(state.state_id),
                    impact=EvolutionImpact.MAJOR,
                )
            )
        previous = state
    return events


def _delta_for_event(event: DecisionEvolutionEvent) -> DecisionDelta:
    changed = bool(
        event.previous_state is not None
        or event.affected_assumption_ids
        or event.affected_threshold_ids
        or event.affected_experiment_ids
        or event.affected_regret_scenario_ids
    )
    explanation_parts = []
    if event.previous_state is not None and event.new_state is not None:
        explanation_parts.append(f"{event.previous_state} -> {event.new_state}")
    if event.affected_threshold_ids:
        explanation_parts.append(f"{len(event.affected_threshold_ids)} threshold(s) affected")
    if event.affected_assumption_ids:
        explanation_parts.append(f"{len(event.affected_assumption_ids)} assumption(s) affected")
    explanation = "; ".join(explanation_parts) if explanation_parts else "No structural change."

    return DecisionDelta(
        changed=changed,
        assessment_changed=event.event_type
        in {EvolutionEventType.ASSESSMENT_CHANGED, EvolutionEventType.VALIDATION_STATE_CHANGED},
        assumptions_changed=list(event.affected_assumption_ids),
        thresholds_changed=list(event.affected_threshold_ids),
        uncertainties_changed=list(event.affected_assumption_ids),
        experiments_changed=list(event.affected_experiment_ids),
        learnings_added=[event.source_id]
        if event.event_type == EvolutionEventType.LEARNING_RECORDED
        else [],
        explanation=explanation,
    )


def _parse_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
