"""Request/response schemas for the experiment results + re-evaluation API.

These describe the shape of data moving across the wire, mirroring the
split already established by `app.schemas.decision` (wire schemas) versus
`app.schemas.decision_resources` (stored entities) - `ExperimentResult` and
`ReEvaluation` themselves are stored entities and live in
`decision_resources.py`; this module holds only the request payload and
the composed API response.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.decision_resources import (
    AnalysisRunStatus,
    DecisionAssessmentStatus,
    ExperimentOutcome,
)


class ExperimentResultCreate(BaseModel):
    """Payload for submitting the observed outcome of running an experiment."""

    outcome: ExperimentOutcome
    summary: str = Field(..., min_length=1, max_length=2000)
    observations: list[str] = Field(default_factory=list)
    measured_values: dict[str, str | float | int | bool] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="Ids of already-uploaded Evidence records for this decision, if any "
        "supporting documents/screenshots were attached. Must reference real evidence - "
        "validated server-side before persistence.",
    )
    notes: str | None = Field(default=None, max_length=2000)
    completed_at: datetime | None = Field(
        default=None,
        description="When the experiment actually finished. Defaults to the submission time "
        "if omitted.",
    )


class ExperimentResultResponse(BaseModel):
    """Response returned after submitting an experiment result.

    Deliberately flat and stable-keyed (mirroring `AnalysisRunResponse`'s
    own convention) rather than nesting the full `ExperimentResult`/
    `ReEvaluation` entities, so the frontend has one unambiguous shape to
    key off of for the common "what just happened" case; the full records
    remain retrievable via their own GET endpoints.
    """

    experiment_id: UUID
    result_id: UUID
    reevaluation_id: UUID
    status: AnalysisRunStatus
    decision_assessment: DecisionAssessmentStatus
    key_learning: str
    next_step: str
