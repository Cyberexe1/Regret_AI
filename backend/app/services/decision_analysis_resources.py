"""Business logic for retrieving an analysis run's structured child entities:
assumptions, blindspots, evidence findings, challenges, regret scenarios,
thresholds, and re-evaluations.

These entities were, until now, only ever written by
`AnalysisOrchestrator`/`ReEvaluationService` and read back internally (e.g.
`ReEvaluationService._reevaluate` reading thresholds/assumptions/regret
scenarios) - nothing exposed them through a public route. The frontend
decision report, threshold visualization, and decision graph all need to
read this data, so this service exposes it read-only, mirroring the exact
pattern already established by `ExternalEvidenceService`/`ExperimentService`.

Route handlers stay thin and delegate here. Nothing in this module ever
creates or mutates these entities - they are only ever produced by the
analysis pipeline or the re-evaluation service.
"""

from uuid import UUID

from app.repositories.decision_repository import DecisionRepository
from app.schemas.decision_resources import (
    Assumption,
    Blindspot,
    Challenge,
    ReEvaluation,
    Threshold,
)
from app.schemas.decision_resources import EvidenceFinding as StoredEvidenceFinding
from app.schemas.decision_resources import RegretScenario as StoredRegretScenario


class DecisionAnalysisResourcesService:
    """Coordinates read-only retrieval of an analysis run's child entities."""

    def __init__(self, repository: DecisionRepository) -> None:
        self._repository = repository

    def list_assumptions(self, decision_id: UUID) -> list[Assumption]:
        return self._repository.list_assumptions(decision_id)

    def list_blindspots(self, decision_id: UUID) -> list[Blindspot]:
        return self._repository.list_blindspots(decision_id)

    def list_evidence_findings(self, decision_id: UUID) -> list[StoredEvidenceFinding]:
        return self._repository.list_evidence_findings(decision_id)

    def list_challenges(self, decision_id: UUID) -> list[Challenge]:
        return self._repository.list_challenges(decision_id)

    def list_regret_scenarios(self, decision_id: UUID) -> list[StoredRegretScenario]:
        return self._repository.list_regret_scenarios(decision_id)

    def list_thresholds(self, decision_id: UUID) -> list[Threshold]:
        return self._repository.list_thresholds(decision_id)

    def list_reevaluations(self, decision_id: UUID) -> list[ReEvaluation]:
        return self._repository.list_reevaluations(decision_id)
