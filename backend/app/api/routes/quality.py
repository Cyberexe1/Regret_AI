"""Decision Intelligence Quality & Calibration routes (REGRET ENGINE
2.0, Step 24).

Every decision-scoped route confirms existence and ownership via
`DecisionServiceDep` before ever touching the quality service, mirroring
every other decision-scoped route in this codebase (e.g.
`app.api.routes.adaptive`) - a stranger's decision id returns a plain
404 before any computation happens. Every calibration route is scoped to
`CurrentUserIdDep` - there is no parameter anywhere here that could
target a different user's records.
"""

from uuid import UUID

from fastapi import APIRouter

from app.core.errors import NotFoundError
from app.dependencies.decisions import CurrentUserIdDep, DecisionServiceDep
from app.dependencies.quality import CalibrationServiceDep, QualityServiceDep
from app.quality.calibration import CalibrationInsight
from app.quality.schemas import QualityAssessment

router = APIRouter(tags=["quality"])


@router.get("/decisions/{decision_id}/quality", response_model=QualityAssessment)
async def get_decision_quality(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    quality_service: QualityServiceDep,
    user_id: CurrentUserIdDep,
) -> QualityAssessment:
    """The most recently computed quality assessment for a decision.
    Never triggers a new check itself - use `POST .../quality/check` for
    that. `404` if no assessment has ever been computed yet.
    """
    decision_service.get_decision(user_id, decision_id)  # existence + ownership, raises 404
    assessment = quality_service.get_latest(decision_id)
    if assessment is None:
        raise NotFoundError(
            detail=f"No quality assessment has been computed yet for decision {decision_id}."
        )
    return assessment


@router.get("/decisions/{decision_id}/quality/history", response_model=list[QualityAssessment])
async def list_decision_quality_history(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    quality_service: QualityServiceDep,
    user_id: CurrentUserIdDep,
) -> list[QualityAssessment]:
    """Every quality assessment ever computed for a decision, oldest
    first - append-only, so how much REGRET trusted its own analysis at
    each point in the decision's history stays reconstructable.
    """
    decision_service.get_decision(user_id, decision_id)
    return quality_service.list_history(decision_id)


@router.post("/decisions/{decision_id}/quality/check", response_model=QualityAssessment)
async def run_decision_quality_check(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    quality_service: QualityServiceDep,
    user_id: CurrentUserIdDep,
) -> QualityAssessment:
    """Explicitly (re)runs the deterministic quality engine against this
    decision's CURRENT canonical records and persists a new assessment.
    """
    decision_service.get_decision(user_id, decision_id)
    return quality_service.run_quality_check(decision_id, user_id)


@router.get("/learning/calibration", response_model=list[CalibrationInsight])
async def list_calibration_insights(
    calibration_service: CalibrationServiceDep,
    user_id: CurrentUserIdDep,
) -> list[CalibrationInsight]:
    """Every calibration insight currently recorded for the caller's own
    decision history - never another user's. Returns whatever the last
    refresh computed; reading never triggers recomputation.
    """
    return calibration_service.list_for_user(user_id)


@router.get("/learning/calibration/{variable}", response_model=CalibrationInsight)
async def get_calibration_insight_for_variable(
    variable: str,
    calibration_service: CalibrationServiceDep,
    user_id: CurrentUserIdDep,
) -> CalibrationInsight:
    """Calibration history for one specific variable, scoped to the
    caller's own decisions. `404` if no calibration insight has been
    computed yet for this variable.
    """
    insight = calibration_service.get_for_variable(user_id, variable)
    if insight is None:
        raise NotFoundError(
            detail=f"No calibration insight has been computed yet for variable '{variable}'."
        )
    return insight


@router.post("/learning/calibration/refresh", response_model=list[CalibrationInsight])
async def refresh_calibration_insights(
    calibration_service: CalibrationServiceDep,
    user_id: CurrentUserIdDep,
) -> list[CalibrationInsight]:
    """Rebuilds the caller's own calibration insights from their current
    canonical records. Always scoped to the caller's own `user_id`.
    """
    return calibration_service.refresh_calibration(user_id)
