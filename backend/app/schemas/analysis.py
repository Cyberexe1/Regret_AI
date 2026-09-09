"""Response schema for the analysis API.

Deliberately named `analysis_run_id` (not `id`) here, distinct from
`AnalysisRun.id`, so the frontend's future analysis client has one
unambiguous field name to key off of, matching the shape the frontend
already expects it can eventually consume (analysis_run_id, decision_id,
status) - see backend README for the exact contract.
"""

from uuid import UUID

from pydantic import BaseModel

from app.schemas.decision_resources import AnalysisRunStatus


class AnalysisRunResponse(BaseModel):
    analysis_run_id: UUID
    decision_id: UUID
    status: AnalysisRunStatus
