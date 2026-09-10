"""Read-only routes for an analysis run's structured child entities.

Thin, mirroring `app.api.routes.research`/`app.api.routes.experiments`:
each route confirms the decision exists and is owned by the caller via
`DecisionServiceDep`, then delegates to
`DecisionAnalysisResourcesService` for the actual read. None of these
entities can be created directly through the API - they only ever come
from `POST /decisions/{decision_id}/analyze` (assumptions, blindspots,
evidence findings, challenges, regret scenarios, thresholds) or
`POST /experiments/{experiment_id}/results` (re-evaluations).
"""

from uuid import UUID

from fastapi import APIRouter

from app.dependencies.decision_analysis_resources import DecisionAnalysisResourcesServiceDep
from app.dependencies.decisions import CurrentUserIdDep, DecisionServiceDep
from app.schemas.decision_resources import (
    Assumption,
    Blindspot,
    Challenge,
    ReEvaluation,
    Threshold,
)
from app.schemas.decision_resources import EvidenceFinding as StoredEvidenceFinding
from app.schemas.decision_resources import RegretScenario as StoredRegretScenario

router = APIRouter(prefix="/decisions", tags=["analysis-resources"])


@router.get("/{decision_id}/assumptions", response_model=list[Assumption])
async def list_assumptions(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    resources_service: DecisionAnalysisResourcesServiceDep,
    user_id: CurrentUserIdDep,
) -> list[Assumption]:
    """List the assumptions identified for a decision by the Assumption Hunter.

    Empty until the decision has a completed (or partially completed)
    analysis run that reached this stage.
    """
    decision_service.get_decision(user_id, decision_id)  # existence + ownership, raises 404
    return resources_service.list_assumptions(decision_id)


@router.get("/{decision_id}/blindspots", response_model=list[Blindspot])
async def list_blindspots(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    resources_service: DecisionAnalysisResourcesServiceDep,
    user_id: CurrentUserIdDep,
) -> list[Blindspot]:
    """List the blindspots identified for a decision by the Blindspot Hunter."""
    decision_service.get_decision(user_id, decision_id)
    return resources_service.list_blindspots(decision_id)


@router.get("/{decision_id}/evidence-findings", response_model=list[StoredEvidenceFinding])
async def list_evidence_findings(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    resources_service: DecisionAnalysisResourcesServiceDep,
    user_id: CurrentUserIdDep,
) -> list[StoredEvidenceFinding]:
    """List the Evidence Agent's analysis of the decision's user-uploaded evidence.

    Distinct from `GET /decisions/{decision_id}/evidence` (the raw uploaded
    documents) - this is the Evidence Agent's interpretation of them.
    """
    decision_service.get_decision(user_id, decision_id)
    return resources_service.list_evidence_findings(decision_id)


@router.get("/{decision_id}/challenges", response_model=list[Challenge])
async def list_challenges(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    resources_service: DecisionAnalysisResourcesServiceDep,
    user_id: CurrentUserIdDep,
) -> list[Challenge]:
    """List the Devil's Advocate's challenges against a decision."""
    decision_service.get_decision(user_id, decision_id)
    return resources_service.list_challenges(decision_id)


@router.get("/{decision_id}/regret-scenarios", response_model=list[StoredRegretScenario])
async def list_regret_scenarios(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    resources_service: DecisionAnalysisResourcesServiceDep,
    user_id: CurrentUserIdDep,
) -> list[StoredRegretScenario]:
    """List the Regret Simulator's failure scenarios for a decision."""
    decision_service.get_decision(user_id, decision_id)
    return resources_service.list_regret_scenarios(decision_id)


@router.get("/{decision_id}/thresholds", response_model=list[Threshold])
async def list_thresholds(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    resources_service: DecisionAnalysisResourcesServiceDep,
    user_id: CurrentUserIdDep,
) -> list[Threshold]:
    """List the Threshold Engine's tipping points for a decision."""
    decision_service.get_decision(user_id, decision_id)
    return resources_service.list_thresholds(decision_id)


@router.get("/{decision_id}/reevaluations", response_model=list[ReEvaluation])
async def list_reevaluations(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    resources_service: DecisionAnalysisResourcesServiceDep,
    user_id: CurrentUserIdDep,
) -> list[ReEvaluation]:
    """List every re-evaluation ever produced for a decision, oldest first.

    Populated by `POST /experiments/{experiment_id}/results` - empty until
    at least one experiment result has been submitted for this decision.
    """
    decision_service.get_decision(user_id, decision_id)
    return resources_service.list_reevaluations(decision_id)
