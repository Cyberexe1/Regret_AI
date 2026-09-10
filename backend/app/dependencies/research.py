"""FastAPI dependency providers for the external-research retrieval feature."""

from typing import Annotated

from fastapi import Depends

from app.dependencies.decisions import get_decision_repository
from app.repositories.decision_repository import DecisionRepository
from app.services.external_evidence import ExternalEvidenceService


def get_external_evidence_service(
    repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
) -> ExternalEvidenceService:
    return ExternalEvidenceService(repository)


ExternalEvidenceServiceDep = Annotated[
    ExternalEvidenceService, Depends(get_external_evidence_service)
]
