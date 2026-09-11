"""Decision Memory data model.

Two entities, mirroring the split already established elsewhere in this
project (e.g. `Evidence` vs `EvidenceFinding`, `ExperimentResult` vs
`ReEvaluation`): a summary (`DecisionMemory`) and the individually
provenance-tracked facts that back it up (`MemoryLearning`).

Nothing here duplicates the original analysis records. `DecisionMemory`
*references* assumption/threshold/regret-scenario/experiment ids that
already live in `DecisionRepository` - it never re-stores their content.
`MemoryLearning` is always derived deterministically from an
already-persisted `ExperimentResult`/`ReEvaluation` record (see
`memory_service.py`); every learning's `source_id` points back to the
exact record it came from, so a learning's provenance is always
auditable and never fabricated.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.decision_resources import Experiment, ReEvaluation


class MemoryStage(StrEnum):
    """Whether a `DecisionMemory` reflects only what was planned, or an
    actual observed outcome.

    PRELIMINARY: no experiment result has been submitted for this decision
    yet. `outcome_summary`/`final_assessment` are `None`; everything in
    the memory is EXPECTED (from the analysis) or UNRESOLVED (not yet
    tested) - never presented as something that already happened.

    VALIDATED: at least one experiment result has been submitted and
    re-evaluated. `outcome_summary`/`final_assessment` now reflect real,
    observed evidence - KNOWN, not merely expected.
    """

    PRELIMINARY = "preliminary"
    VALIDATED = "validated"


class LearningType(StrEnum):
    """What kind of fact a `MemoryLearning` records.

    Every value here corresponds to a specific, deterministic transition
    already computed by `app.services.re_evaluation_service` (threshold
    comparison status, assumption re-evaluation status, regret scenario
    re-evaluation status) or to a directly observed, user-authored fact
    (an experiment's own submitted summary) - never an inference invented
    at the memory layer itself.
    """

    ASSUMPTION_VALIDATED = "assumption_validated"
    ASSUMPTION_WEAKENED = "assumption_weakened"
    ASSUMPTION_FAILED = "assumption_failed"
    THRESHOLD_VALIDATED = "threshold_validated"
    THRESHOLD_FAILED = "threshold_failed"
    THRESHOLD_INCONCLUSIVE = "threshold_inconclusive"
    UNEXPECTED_RESULT = "unexpected_result"
    EXPERIMENT_LEARNING = "experiment_learning"
    DECISION_OUTCOME = "decision_outcome"
    UNRESOLVED_UNCERTAINTY = "unresolved_uncertainty"


class LearningSourceType(StrEnum):
    """What kind of already-persisted record a `MemoryLearning` was derived from."""

    EXPERIMENT_RESULT = "experiment_result"
    RE_EVALUATION = "re_evaluation"
    EVIDENCE = "evidence"
    DECISION = "decision"
    ANALYSIS = "analysis"


class MemoryLearning(BaseModel):
    """One durable, provenance-tracked fact learned about a decision.

    Always derived deterministically from a stored record - `source_type`/
    `source_id` say exactly which one. `observed_value`/`expected_value`
    are populated only when both genuinely exist (e.g. a threshold
    comparison); `variance_description` is a plain, factual description
    of the difference between them, never a causal explanation the
    underlying data doesn't support (see `memory_service.py` for the
    "no fabricated causality" rule this schema exists to enforce).

    Immutable once created - a `MemoryLearning` is never edited or
    deleted; a later result produces a new, additional learning rather
    than changing history (see `MemoryRepository.create_learning`).
    """

    learning_id: UUID
    memory_id: UUID
    decision_id: UUID
    statement: str = Field(
        ..., description="A single, factual sentence describing what was learned - never a "
        "causal claim the source data doesn't support."
    )
    learning_type: LearningType
    source_type: LearningSourceType
    source_id: UUID = Field(
        ..., description="The id of the ExperimentResult/ReEvaluation/Evidence/Decision/"
        "AnalysisRun this learning was derived from."
    )
    confidence: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Carried over from the source record's own confidence (e.g. a "
        "DecisionAssessment's confidence) - never invented at this layer.",
    )
    evidence_basis: list[str] = Field(default_factory=list)
    observed_value: str | None = None
    expected_value: str | None = None
    variance_description: str | None = None
    related_assumption_ids: list[str] = Field(default_factory=list)
    related_threshold_ids: list[str] = Field(default_factory=list)
    related_regret_scenario_ids: list[str] = Field(default_factory=list)
    created_at: datetime


class DecisionMemory(BaseModel):
    """A structured summary of what REGRET ENGINE remembers about one decision.

    References canonical records by id (`critical_assumption_ids`,
    `critical_threshold_ids`, `critical_regret_scenario_ids`,
    `experiment_ids`) rather than duplicating their content - the full
    records remain the source of truth in `DecisionRepository`, retrievable
    via the existing `/decisions/{id}/assumptions`, `/thresholds`, etc.
    endpoints. This object exists to answer "what happened with this
    decision, overall" in one place, not to be a second copy of the
    analysis.

    Exactly one `DecisionMemory` exists per decision at any time - later
    experiment results update it in place (see `MemoryService`); nothing
    about that update ever discards the immutable `MemoryLearning`
    history that led to it.
    """

    memory_id: UUID
    decision_id: UUID
    user_id: str
    decision_type: str | None = None
    decision_summary: str
    created_at: datetime
    completed_at: datetime | None = None
    stage: MemoryStage = MemoryStage.PRELIMINARY
    original_assessment: str | None = Field(
        default=None, description="A plain description of the decision's state at analysis "
        "time, before any experiment result existed."
    )
    critical_assumption_ids: list[str] = Field(default_factory=list)
    critical_threshold_ids: list[str] = Field(default_factory=list)
    critical_regret_scenario_ids: list[str] = Field(default_factory=list)
    experiment_ids: list[str] = Field(default_factory=list)
    outcome_summary: str | None = Field(
        default=None, description="Null while `stage=preliminary` - only set once a real "
        "experiment result exists."
    )
    validated_learnings: list[str] = Field(
        default_factory=list,
        description="Learning ids (see MemoryLearning) whose learning_type reflects a real, "
        "observed outcome (validated/failed/weakened/decision_outcome) - not merely expected "
        "or unresolved.",
    )
    unresolved_uncertainties: list[str] = Field(
        default_factory=list,
        description="Learning ids whose learning_type is unresolved_uncertainty, or - while "
        "stage=preliminary - plain descriptions of what has not been tested yet.",
    )
    final_assessment: str | None = Field(
        default=None, description="Null while `stage=preliminary`. Mirrors the most recent "
        "ReEvaluation's decision_assessment status/summary once one exists."
    )
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    source_analysis_run_id: UUID | None = None
    updated_at: datetime


class DecisionMemoryResponse(BaseModel):
    """Composite response for `GET /decisions/{decision_id}/memory`.

    Bundles the memory summary with the learnings, experiments, and
    assessments (re-evaluations) it references, so a client can render
    the full "what we believed / what we tested / what we learned"
    picture in one request without needing four separate calls.
    `experiments`/`assessments` are the actual, already-persisted
    `Experiment`/`ReEvaluation` entities from `DecisionRepository` -
    nothing here is summarized, re-derived, or duplicated content; the
    memory's own `experiment_ids` list is simply resolved into the real
    records for display convenience.
    """

    memory: DecisionMemory | None
    learnings: list[MemoryLearning] = Field(default_factory=list)
    experiments: list[Experiment] = Field(default_factory=list)
    assessments: list[ReEvaluation] = Field(default_factory=list)
    unresolved_uncertainties: list[str] = Field(default_factory=list)
