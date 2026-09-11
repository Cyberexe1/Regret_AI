"""FastAPI dependency providers for the Adaptive Experiment Loop feature
(REGRET ENGINE 2.0, Step 21)."""

from typing import Annotated

from fastapi import Depends

from app.adaptive.repository import AdaptiveStateRepository
from app.adaptive.service import AdaptiveExperimentService
from app.agents.value_of_information import ValueOfInformationService
from app.dependencies.decisions import get_decision_repository
from app.dependencies.memory import get_memory_service
from app.dependencies.value_of_information import get_value_of_information_service
from app.memory.memory_service import MemoryService
from app.repositories.decision_repository import DecisionRepository


def get_adaptive_state_repository() -> AdaptiveStateRepository:
    return AdaptiveStateRepository()


def get_adaptive_experiment_service(
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
    adaptive_repository: Annotated[AdaptiveStateRepository, Depends(get_adaptive_state_repository)],
    voi_service: Annotated[ValueOfInformationService, Depends(get_value_of_information_service)],
    memory_service: Annotated[MemoryService, Depends(get_memory_service)],
) -> AdaptiveExperimentService:
    return AdaptiveExperimentService(
        decision_repository, adaptive_repository, voi_service, memory_service
    )


AdaptiveExperimentServiceDep = Annotated[
    AdaptiveExperimentService, Depends(get_adaptive_experiment_service)
]
