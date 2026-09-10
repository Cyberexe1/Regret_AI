"""External research retrieval routes.

Thin, mirroring `app.api.routes.experiments`: confirms the decision exists
and is owned by the caller via `DecisionServiceDep`, then delegates to the
repository for the actual read. External research itself is never
triggered from a dedicated endpoint here - it runs automatically (and
optionally, per `Settings.research_provider`) as part of
`POST /decisions/{decision_id}/analyze`, per the existing analysis
pipeline's convention of not duplicating the main `/analyze` endpoint with
a separate trigger.
"""

from uuid import UUID

from fastapi import APIRouter

from app.dependencies.decisions import CurrentUserIdDep, DecisionServiceDep
from app.dependencies.research import ExternalEvidenceServiceDep
from app.schemas.decision_resources import ExternalEvidence

router = APIRouter(prefix="/decisions", tags=["research"])


@router.get("/{decision_id}/external-evidence", response_model=list[ExternalEvidence])
async def list_external_evidence(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    external_evidence_service: ExternalEvidenceServiceDep,
    user_id: CurrentUserIdDep,
) -> list[ExternalEvidence]:
    """List the external research findings recorded for a decision.

    Returns whatever the (optional) Research Agent produced on the most
    recent successful analysis run - empty if research was never enabled,
    was unavailable, or found nothing relevant.
    """
    decision_service.get_decision(user_id, decision_id)  # existence + ownership, raises 404
    return external_evidence_service.list_external_evidence(decision_id)
