"""FastAPI dependency providers for the Cross-Decision Learning feature
(REGRET ENGINE 2.0, Step 23)."""

from typing import Annotated

from fastapi import Depends

from app.dependencies.decisions import get_decision_repository
from app.dependencies.memory import get_memory_repository
from app.learning.repository import CrossDecisionLearningRepository
from app.learning.service import CrossDecisionLearningService
from app.memory.memory_repository import MemoryRepository
from app.repositories.decision_repository import DecisionRepository


def get_cross_decision_learning_repository() -> CrossDecisionLearningRepository:
    return CrossDecisionLearningRepository()


def get_cross_decision_learning_service(
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
    memory_repository: Annotated[MemoryRepository, Depends(get_memory_repository)],
    learning_repository: Annotated[
        CrossDecisionLearningRepository, Depends(get_cross_decision_learning_repository)
    ],
) -> CrossDecisionLearningService:
    return CrossDecisionLearningService(decision_repository, memory_repository, learning_repository)


CrossDecisionLearningServiceDep = Annotated[
    CrossDecisionLearningService, Depends(get_cross_decision_learning_service)
]
