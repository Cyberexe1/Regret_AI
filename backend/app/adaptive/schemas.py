"""Adaptive Experiment Loop data model (REGRET ENGINE 2.0, Step 21).

`AdaptiveExperimentState` is the one new persisted entity this step adds.
It is a snapshot of "where the validation journey currently stands" for
one decision - which uncertainty is being tested (or was just tested),
what the decision's evidence-supported state currently is, and what
should happen next. It never duplicates data that already lives
elsewhere: the actual `Threshold`/`Experiment`/`ExperimentResult`/
`ReEvaluation`/`ValueOfInformationAnalysis` records remain the sources of
truth (see `app.repositories.decision_repository`,
`app.repositories.value_of_information_repository`); this schema only
references them by id and records the loop's own bookkeeping.

Append-only, exactly like `ReEvaluation` and `ValueOfInformationAnalysis`:
every transition (a new experiment selected, a result processed, a
stopping decision reached) creates a NEW `AdaptiveExperimentState` with
an incremented or unchanged `cycle_number` - never overwrites a previous
one - so the full validation journey (`Experiment 1 -> Result -> Learning
-> Experiment 2 -> Result -> Learning -> ...`) stays reconstructable.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class AdaptiveCycleStatus(StrEnum):
    """Where one decision's validation journey currently stands.

    State machine (see `app.adaptive.service` for the exact transitions):

        (none yet) --advance--> AWAITING_EXPERIMENT
        AWAITING_EXPERIMENT --user runs it, submits a result--> READY_FOR_NEXT_EXPERIMENT
        READY_FOR_NEXT_EXPERIMENT --advance--> AWAITING_EXPERIMENT | SUFFICIENTLY_VALIDATED
                                              | INCONCLUSIVE | BLOCKED
        (any) --user stops--> USER_STOPPED

    `EXPERIMENT_ACTIVE`/`AWAITING_RESULT`/`RE_EVALUATING`/
    `SELECTING_NEXT_TEST` are reserved, descriptive statuses for a future
    asynchronous version of this loop (e.g. if experiment execution or
    re-evaluation ever becomes a background job) - this step's flow is
    synchronous end to end, so a cycle never actually rests in one of
    those states, but they are part of the documented model per the
    spec's required enum and are included so the schema doesn't need to
    change if that becomes true later.
    """

    AWAITING_EXPERIMENT = "awaiting_experiment"
    EXPERIMENT_ACTIVE = "experiment_active"
    AWAITING_RESULT = "awaiting_result"
    RE_EVALUATING = "re_evaluating"
    SELECTING_NEXT_TEST = "selecting_next_test"
    READY_FOR_NEXT_EXPERIMENT = "ready_for_next_experiment"
    SUFFICIENTLY_VALIDATED = "sufficiently_validated"
    INCONCLUSIVE = "inconclusive"
    USER_STOPPED = "user_stopped"
    BLOCKED = "blocked"


class DecisionValidationState(StrEnum):
    """The decision's current evidence-supported state - NOT a
    probability, and NOT a verdict on whether the decision is "correct."

    Meaning: "the tested condition(s) have this much evidence relative to
    the validation criteria the analysis itself defined (the recorded
    thresholds)." A decision can be `strongly_weakened` and still be one
    the user chooses to proceed with (e.g. because the alternative is
    worse) - REGRET ENGINE reports the evidence state, never the decision
    itself. See `app.adaptive.service._decision_validation_state` for the
    deterministic derivation from real, already-persisted
    `ThresholdComparisonStatus` history.
    """

    STRONGLY_SUPPORTED = "strongly_supported"
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    WEAKENED = "weakened"
    STRONGLY_WEAKENED = "strongly_weakened"
    INCONCLUSIVE = "inconclusive"
    REQUIRES_MORE_TESTING = "requires_more_testing"


class ThresholdState(StrEnum):
    """One threshold's current standing in the validation journey -
    distinct from `ThresholdValidationStatus` (which describes how the
    threshold's VALUE was derived - Step 7's concern) and from
    `ThresholdComparisonStatus` (one experiment's raw comparison result -
    `app.services.threshold_comparison`'s concern). This is the adaptive
    loop's own, higher-level view: has this threshold been tested at all,
    and if so, with what outcome.
    """

    UNKNOWN = "unknown"
    PROVISIONAL = "provisional"
    UNDER_TEST = "under_test"
    VALIDATED = "validated"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class ThresholdCycleRecord(BaseModel):
    """One threshold's state change recorded at one adaptive transition.

    Only ever created when something about a threshold's standing
    actually changed this transition (e.g. a real experiment result was
    just processed) - a pure "select the next experiment" transition
    with no new evidence produces an empty `uncertainty_status` list on
    its `AdaptiveExperimentState`, never a fabricated "nothing changed"
    record for every threshold in the decision.
    """

    threshold_id: str
    previous_status: ThresholdState
    current_status: ThresholdState
    observed_value: str | None = None
    required_value: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    validation_status: str | None = None


class AdaptiveExperimentState(BaseModel):
    """One snapshot of the adaptive validation journey for a decision.

    Persisted under `SK=ADAPTIVE_STATE#<state_id>` (see
    `app.adaptive.repository`), append-only. `cycle_number` increments
    only when a NEW experiment is actually selected to be run next - a
    transition that only records a just-completed result, or that
    concludes the loop (sufficiently validated / inconclusive / blocked /
    user-stopped), keeps the same `cycle_number` as the cycle it's
    concluding.
    """

    state_id: UUID
    decision_id: UUID
    user_id: str
    cycle_number: int = Field(..., ge=1)
    current_status: AdaptiveCycleStatus

    current_primary_uncertainty_id: str | None = Field(
        default=None,
        description="The uncertainty_id (Assumption/Blindspot id) this cycle is testing or "
        "about to test - copied from the freshest ValueOfInformationAnalysis's "
        "primary_uncertainty_id, never re-derived independently.",
    )
    current_primary_threshold_id: str | None = None
    current_experiment_id: str | None = Field(
        default=None,
        description="The real, already-recommended (never fabricated) Experiment this cycle "
        "targets - null while blocked/concluded, or if no feasible not-yet-run experiment "
        "exists for the current primary uncertainty.",
    )

    previous_experiment_id: str | None = None
    previous_result_id: str | None = None
    previous_assessment: DecisionValidationState | None = None
    current_assessment: DecisionValidationState

    uncertainty_status: list[ThresholdCycleRecord] = Field(default_factory=list)

    stopping_reason: str | None = Field(
        default=None,
        description="Plain-English reason the loop stopped or is currently blocked - set only "
        "for SUFFICIENTLY_VALIDATED / INCONCLUSIVE / USER_STOPPED / BLOCKED.",
    )
    next_action: str = Field(
        ..., description="Plain-English description of what to do next, built only from real "
        "fields on this state - never free-form LLM prose.",
    )
    why_this_is_next: str | None = Field(
        default=None,
        description="Explainability: why this specific uncertainty/experiment was chosen this "
        "cycle, mirroring the underlying ValueOfInformationItem's own rationale plus what "
        "changed since the previous cycle. Null when there is no next uncertainty (concluded).",
    )

    created_at: datetime
    updated_at: datetime


class AdvanceOutcome(StrEnum):
    """What `advance_cycle` actually did - distinct from the resulting
    `AdaptiveCycleStatus`, so a caller (and the API response) can tell
    "a new cycle was actually selected" apart from "nothing changed,
    here is the existing state again" without parsing prose."""

    STARTED_FIRST_CYCLE = "started_first_cycle"
    ADVANCED_TO_NEXT_EXPERIMENT = "advanced_to_next_experiment"
    CONCLUDED = "concluded"
    NO_CHANGE = "no_change"


class AdaptiveAdvanceResponse(BaseModel):
    """Response for `POST /decisions/{id}/adaptive/advance`.

    Wraps the resulting `AdaptiveExperimentState` together with
    `outcome`, so a caller can distinguish "a new cycle was actually
    selected" from "nothing changed, here is the existing state again"
    without having to diff state ids itself - directly supports the
    idempotency guarantee: calling advance twice with no new evidence
    returns `outcome=no_change` and the SAME `state.state_id` both times.
    """

    state: AdaptiveExperimentState
    outcome: AdvanceOutcome
