"""FastAPI dependency providers for the experiments feature."""

from typing import Annotated

from fastapi import Depends

from app.dependencies.decisions import get_decision_repository
from app.dependencies.evidence import get_evidence_repository
from app.repositories.decision_repository import DecisionRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.services.experiments import ExperimentService
from app.services.re_evaluation_service import ReEvaluationService


def get_experiment_service(
    repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
) -> ExperimentService:
    return ExperimentService(repository)


def get_re_evaluation_service(
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
    evidence_repository: Annotated[EvidenceRepository, Depends(get_evidence_repository)],
) -> ReEvaluationService:
    return ReEvaluationService(decision_repository, evidence_repository)


ExperimentServiceDep = Annotated[ExperimentService, Depends(get_experiment_service)]
ReEvaluationServiceDep = Annotated[ReEvaluationService, Depends(get_re_evaluation_service)]
