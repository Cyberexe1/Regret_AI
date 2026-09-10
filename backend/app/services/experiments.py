"""Business logic for retrieving experiments and their results.

Route handlers stay thin and delegate here. Experiments themselves are
only ever created by the Experiment Planner via `AnalysisOrchestrator` -
this service is read-only for experiments (list/get), following the same
ownership-check pattern as `DecisionService`/`EvidenceService`. Result
*submission* (which also triggers re-evaluation) lives in the separate
`ReEvaluationService` - this service only reads results back.
"""

from uuid import UUID

from app.core.errors import NotFoundError
from app.repositories.decision_repository import DecisionRepository
from app.schemas.decision_resources import Experiment
from app.schemas.decision_resources import ExperimentResult as StoredExperimentResult


class ExperimentService:
    """Coordinates experiment and experiment-result retrieval."""

    def __init__(self, repository: DecisionRepository) -> None:
        self._repository = repository

    def list_experiments(self, decision_id: UUID) -> list[Experiment]:
        return self._repository.list_experiments(decision_id)

    def get_experiment(self, experiment_id: UUID) -> Experiment:
        experiment = self._repository.get_experiment_by_id(experiment_id)
        if experiment is None:
            raise NotFoundError(detail=f"Experiment {experiment_id} not found.")
        return experiment

    def list_results_for_experiment(
        self, decision_id: UUID, experiment_id: UUID
    ) -> list[StoredExperimentResult]:
        return self._repository.list_experiment_results(decision_id, experiment_id)

    def list_results_for_decision(self, decision_id: UUID) -> list[StoredExperimentResult]:
        return self._repository.list_experiment_results(decision_id)
