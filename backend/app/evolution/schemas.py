"""Decision Evolution data model (REGRET ENGINE 2.0, Step 22).

`DecisionEvolutionEvent` is a VIEW row, not a persisted entity - it is
always assembled on the fly from a real, already-persisted record (see
`app.evolution.service`). `source_type`/`source_id` always point back to
that exact record, so every event is auditable to its canonical source.

Nothing here is a second history database: there is no `create_event`
anywhere in this package, no DynamoDB writes at all. The evolution
endpoint recomputes the timeline from canonical records on every read.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class EvolutionEventType(StrEnum):
    """Every kind of event the timeline can show - each one maps to
    exactly one already-existing canonical record type (see
    `app.evolution.service`'s per-type builder functions). Never a
    free-form string, so the frontend can render a fixed, known set of
    icons/labels rather than guessing at arbitrary text.
    """

    DECISION_CREATED = "decision_created"
    ANALYSIS_COMPLETED = "analysis_completed"
    ASSUMPTION_IDENTIFIED = "assumption_identified"
    BLINDSPOT_IDENTIFIED = "blindspot_identified"
    REGRET_SCENARIO_IDENTIFIED = "regret_scenario_identified"
    THRESHOLD_IDENTIFIED = "threshold_identified"
    EXPERIMENT_RECOMMENDED = "experiment_recommended"
    EXPERIMENT_STARTED = "experiment_started"
    EXPERIMENT_COMPLETED = "experiment_completed"
    EXPERIMENT_RESULT = "experiment_result"
    THRESHOLD_VALIDATED = "threshold_validated"
    THRESHOLD_FAILED = "threshold_failed"
    RE_EVALUATION = "re_evaluation"
    ASSESSMENT_CHANGED = "assessment_changed"
    LEARNING_RECORDED = "learning_recorded"
    NEXT_EXPERIMENT_SELECTED = "next_experiment_selected"
    VALIDATION_STATE_CHANGED = "validation_state_changed"
    DECISION_COMPLETED = "decision_completed"
    # Additive - not dropping any required type above. Needed so a
    # materially-influential historical insight (Step 19) can be shown as
    # its own distinct, clearly-labeled event rather than folded into a
    # current-evidence type (spec section 20's explicit requirement).
    HISTORICAL_INSIGHT_SURFACED = "historical_insight_surfaced"


class EvolutionImpact(StrEnum):
    """How much this specific event mattered to the decision's overall
    evolution - used only to decide what counts as a "major change"
    (see `DecisionEvolutionService.get_major_changes`), never a severity
    score presented as a statistic."""

    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"


class DecisionEvolutionEvent(BaseModel):
    """One point on the decision's evolution timeline - always derived
    from a real, already-persisted record, never fabricated.

    `previous_state`/`new_state` are populated ONLY for state-changing
    events (e.g. `assessment_changed`, `threshold_validated`,
    `validation_state_changed`) where the source record itself carries a
    before/after pair (a `ReEvaluation`'s `previous_assessment`/
    `new_assessment`, a `ThresholdCycleRecord`'s `previous_status`/
    `current_status`) - both are `None` for events with no such
    transition (e.g. `decision_created`).

    `affected_*_ids` are always real, already-persisted ids copied from
    the source record's own cross-reference fields - never invented or
    re-derived independently.
    """

    event_id: str = Field(
        ...,
        description="Deterministic, derived from (decision_id, event_type, source_id) - "
        "same source record always produces the same event_id, so re-fetching the timeline "
        "never renumbers or duplicates an event.",
    )
    decision_id: str
    cycle_number: int | None = Field(
        default=None,
        description="The adaptive-loop cycle this event belongs to, when known (see "
        "AdaptiveExperimentState.cycle_number) - null for events that predate or don't "
        "belong to any adaptive cycle (e.g. decision_created, analysis_completed).",
    )
    event_type: EvolutionEventType
    timestamp: datetime
    title: str
    summary: str = Field(
        ...,
        description="What happened, in plain language, using only real fields from the "
        "source record - never a fabricated causal claim the source data doesn't support.",
    )
    source_type: str = Field(
        ...,
        description="The canonical record kind this event was derived from, e.g. "
        "'threshold', 'experiment_result', 're_evaluation', 'memory_learning'.",
    )
    source_id: str
    impact: EvolutionImpact
    previous_state: str | None = None
    new_state: str | None = None
    reason: str | None = Field(
        default=None,
        description="Why the state changed, stated only when the source record itself "
        "supports the claim (e.g. a ThresholdComparison's own explanation) - never inferred.",
    )
    affected_assumption_ids: list[str] = Field(default_factory=list)
    affected_threshold_ids: list[str] = Field(default_factory=list)
    affected_experiment_ids: list[str] = Field(default_factory=list)
    affected_regret_scenario_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    is_historical: bool = Field(
        default=False,
        description="True only for a surfaced historical insight from a DIFFERENT past "
        "decision (Step 19) - the frontend must label this HISTORICAL and never present it "
        "as current evidence for THIS decision (spec section 20).",
    )


class DecisionDelta(BaseModel):
    """A deterministic, structured description of what changed between
    two points in a decision's evolution - "what changed?" answered with
    real, comparable fields, never a fabricated narrative.
    """

    changed: bool
    assessment_changed: bool = False
    assumptions_changed: list[str] = Field(default_factory=list)
    thresholds_changed: list[str] = Field(default_factory=list)
    uncertainties_changed: list[str] = Field(default_factory=list)
    experiments_changed: list[str] = Field(default_factory=list)
    learnings_added: list[str] = Field(default_factory=list)
    explanation: str = Field(
        ...,
        description="Plain-language summary of the delta, built only from the fields "
        "above - never free-form LLM prose.",
    )


class DecisionEvolution(BaseModel):
    """Composite response for `GET /decisions/{decision_id}/evolution`.

    Bundles the current state, the full (bounded) timeline, and a
    compact "major changes" list in one response - deliberately a single
    call rather than one request per timeline event (spec section 22's
    performance requirement).
    """

    decision_id: str
    user_id: str
    current_assessment: str = Field(
        ...,
        description="The decision's current evidence-supported assessment label - "
        "mirrors AdaptiveExperimentState.current_assessment when the adaptive loop has run, "
        "or the latest ReEvaluation's decision_assessment.status otherwise.",
    )
    current_cycle: int | None = None
    total_cycles: int = 0
    timeline: list[DecisionEvolutionEvent] = Field(default_factory=list)
    major_changes: list[DecisionEvolutionEvent] = Field(default_factory=list)
    current_uncertainties: list[str] = Field(
        default_factory=list,
        description="Real, unresolved assumption/blindspot ids - never a fabricated summary.",
    )
    validated_thresholds: list[str] = Field(default_factory=list)
    failed_thresholds: list[str] = Field(default_factory=list)
    current_primary_uncertainty: str | None = None
    truncated: bool = Field(
        default=False,
        description="True if the timeline was cut off at EVOLUTION_MAX_EVENTS - the oldest "
        "events are dropped first, never the most recent ones, so 'what changed most "
        "recently' is always visible even for a very long history.",
    )
    generated_at: datetime
