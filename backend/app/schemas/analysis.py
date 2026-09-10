"""Response schemas for the analysis API.

Deliberately named `analysis_run_id` (not `id`) here, distinct from
`AnalysisRun.id`, so the frontend's future analysis client has one
unambiguous field name to key off of, matching the shape the frontend
already expects it can eventually consume (analysis_run_id, decision_id,
status) - see backend README for the exact contract.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.decision_resources import AgentRunStatus, AnalysisRunStatus


class AnalysisRunResponse(BaseModel):
    analysis_run_id: UUID
    decision_id: UUID
    status: AnalysisRunStatus


class AnalysisRunStatusResponse(BaseModel):
    """Full status/progress view of one analysis run.

    Used by `GET /decisions/{decision_id}/analysis/{analysis_run_id}` so a
    caller can poll progress through the pipeline's ~9 sequential stages
    without needing the full structured result of each stage - just
    `status`/`current_stage`/`stage_statuses`. Never includes chain-of-
    thought, raw prompts, or provider-internal error detail - only
    execution metadata, per the "make analysis lifecycle observable
    without exposing hidden model reasoning" requirement.
    """

    analysis_run_id: UUID
    decision_id: UUID
    status: AnalysisRunStatus
    current_stage: str | None
    stage_statuses: dict[str, AgentRunStatus]
    created_at: datetime | None
    updated_at: datetime | None
    error_message: str | None = None
