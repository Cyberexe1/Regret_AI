"""Analysis routes.

Thin by design: routes only resolve the caller's identity, delegate to
`AnalysisOrchestrator`/`AnalysisRepository`, and shape the response. All
the actual work (loading the decision, invoking agents, persisting
results) lives in the orchestrator - this file never touches an agent
directly.
"""

from uuid import UUID

from fastapi import APIRouter, status

from app.core.errors import NotFoundError
from app.dependencies.analysis import AnalysisOrchestratorDep, AnalysisRepositoryDep
from app.dependencies.decisions import CurrentUserIdDep, DecisionServiceDep
from app.schemas.analysis import AnalysisRunResponse, AnalysisRunStatusResponse
from app.schemas.decision_resources import AgentRunStatus

router = APIRouter(prefix="/decisions", tags=["analysis"])

# Agents in pipeline order - used only to pick a human-meaningful
# "current_stage" for the status response (the first stage that hasn't
# reached a terminal per-stage status yet), never to drive the pipeline
# itself (that's the orchestrator's job).
_PIPELINE_STAGE_ORDER = [
    "decision_analyzer",
    "assumption_hunter",
    "blindspot_hunter",
    "research_agent",
    "evidence_agent",
    "devils_advocate",
    "regret_simulator",
    "threshold_engine",
    "experiment_planner",
]

_TERMINAL_STAGE_STATUSES = {
    AgentRunStatus.COMPLETED,
    AgentRunStatus.FAILED,
    AgentRunStatus.SKIPPED,
    AgentRunStatus.UNAVAILABLE,
}


@router.post(
    "/{decision_id}/analyze",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def analyze_decision(
    decision_id: UUID,
    orchestrator: AnalysisOrchestratorDep,
    user_id: CurrentUserIdDep,
) -> AnalysisRunResponse:
    """Run the full analysis pipeline for a decision.

    Synchronous: the response is only returned once the analysis run has
    reached a terminal status (`completed` or `failed`). Idempotent: if
    this decision already has an active (`queued`/`running`) analysis
    run, that existing run is returned rather than starting a duplicate
    one - see `AnalysisOrchestrator.run_analysis`. Use
    `GET /decisions/{decision_id}/analysis/{analysis_run_id}` to inspect
    per-stage progress for a run.
    """
    run = await orchestrator.run_analysis(user_id, decision_id)
    return AnalysisRunResponse(
        analysis_run_id=run.id, decision_id=run.decision_id, status=run.status
    )


def _to_status_response(run) -> AnalysisRunStatusResponse:
    stage_statuses = run.agent_statuses or {}
    current_stage = next(
        (
            stage
            for stage in _PIPELINE_STAGE_ORDER
            if stage_statuses.get(stage, AgentRunStatus.PENDING) not in _TERMINAL_STAGE_STATUSES
        ),
        None,
    )
    return AnalysisRunStatusResponse(
        analysis_run_id=run.id,
        decision_id=run.decision_id,
        status=run.status,
        current_stage=current_stage,
        stage_statuses=stage_statuses,
        created_at=run.created_at,
        updated_at=run.updated_at,
        error_message=run.error_message,
    )


@router.get(
    "/{decision_id}/analysis/latest",
    response_model=AnalysisRunStatusResponse,
)
async def get_latest_analysis_status(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    analysis_repository: AnalysisRepositoryDep,
    user_id: CurrentUserIdDep,
) -> AnalysisRunStatusResponse:
    """Fetch the status/progress of a decision's most recently created run.

    Exists because `POST /decisions/{decision_id}/analyze` is synchronous -
    it doesn't return an `analysis_run_id` until the whole pipeline has
    already reached a terminal status. A caller that wants to show live
    progress WHILE that request is still in flight (e.g. polling every 1-2
    seconds from the browser) has no run id to poll with yet, since it's
    all one blocking call - this endpoint lets it find and poll the
    just-created run from a second, concurrent request instead. Returns
    404 if the decision has never been analyzed. Route registered ahead of
    `/{analysis_run_id}` below so "latest" is never parsed as a UUID path
    param.
    """
    decision_service.get_decision(user_id, decision_id)  # existence + ownership, raises 404
    runs = analysis_repository.list_for_decision(decision_id)
    if not runs:
        raise NotFoundError(detail=f"Decision {decision_id} has no analysis runs yet.")

    latest = max(runs, key=lambda run: run.created_at)
    return _to_status_response(latest)


@router.get(
    "/{decision_id}/analysis/{analysis_run_id}",
    response_model=AnalysisRunStatusResponse,
)
async def get_analysis_status(
    decision_id: UUID,
    analysis_run_id: UUID,
    decision_service: DecisionServiceDep,
    analysis_repository: AnalysisRepositoryDep,
    user_id: CurrentUserIdDep,
) -> AnalysisRunStatusResponse:
    """Fetch the status/progress of one analysis run.

    Returns per-stage statuses (`stage_statuses`) and a best-effort
    `current_stage` (the first stage not yet in a terminal state) so a
    caller can show pipeline progress without polling anything beyond
    this one endpoint. Never returns chain-of-thought, raw prompts, or
    each stage's full structured output - only execution metadata; use
    the decision's own child-entity endpoints (assumptions, thresholds,
    experiments, etc.) to read actual findings once a run completes.
    """
    decision_service.get_decision(user_id, decision_id)  # existence + ownership, raises 404
    run = analysis_repository.get(decision_id, analysis_run_id)
    if run is None:
        raise NotFoundError(detail=f"Analysis run {analysis_run_id} not found.")

    return _to_status_response(run)
