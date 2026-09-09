"""FastAPI dependency providers for the evidence feature."""

from typing import Annotated

from fastapi import Depends

from app.repositories.evidence_repository import EvidenceRepository
from app.services.evidence import EvidenceService
from app.services.storage import StorageBackend, get_storage_backend


def get_evidence_repository() -> EvidenceRepository:
    return EvidenceRepository()


def get_evidence_service(
    repository: Annotated[EvidenceRepository, Depends(get_evidence_repository)],
    storage: Annotated[StorageBackend, Depends(get_storage_backend)],
) -> EvidenceService:
    return EvidenceService(repository, storage)


EvidenceServiceDep = Annotated[EvidenceService, Depends(get_evidence_service)]
