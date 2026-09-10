"""Business logic for retrieving external research findings.

Route handlers stay thin and delegate here. External evidence itself is
only ever created by the (optional) Research Agent via
`AnalysisOrchestrator` - this service is read-only, following the same
pattern as `ExperimentService`.
"""

from uuid import UUID

from app.repositories.decision_repository import DecisionRepository
from app.schemas.decision_resources import ExternalEvidence


class ExternalEvidenceService:
    """Coordinates external-evidence retrieval."""

    def __init__(self, repository: DecisionRepository) -> None:
        self._repository = repository

    def list_external_evidence(self, decision_id: UUID) -> list[ExternalEvidence]:
        return self._repository.list_external_evidence(decision_id)
