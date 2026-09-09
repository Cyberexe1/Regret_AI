"""Analysis routes.

Thin by design: the route only resolves the caller's identity, delegates
to `AnalysisOrchestrator`, and shapes the response. All the actual work
(loading the decision, invoking the agent, persisting results) lives in
the orchestrator - this file never touches a repository or an agent
directly.
"""

from uuid import UUID

from fastapi import APIRouter, status

from app.dependencies.analysis import AnalysisOrchestratorDep
from app.dependencies.decisions import CurrentUserIdDep
from app.schemas.analysis import AnalysisRunResponse

router = APIRouter(prefix="/decisions", tags=["analysis"])


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
    """Run the Decision Analyzer for a decision.

    Synchronous for now: the response is only returned once the analysis
    run has reached a terminal status (`completed` or `failed`) - there is
    no polling endpoint yet. Only the Decision Analyzer runs; the rest of
    the agent pipeline (assumptions, blindspots, evidence, stress-testing,
    regret simulation, thresholds, experiments) is not implemented yet.
    """
    run = await orchestrator.run_analysis(user_id, decision_id)
    return AnalysisRunResponse(
        analysis_run_id=run.id, decision_id=run.decision_id, status=run.status
    )
