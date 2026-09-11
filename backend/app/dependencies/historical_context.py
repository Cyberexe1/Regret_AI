"""FastAPI dependency providers for the Decision Similarity & Historical
Insight feature (REGRET ENGINE 2.0)."""

from typing import Annotated

from fastapi import Depends

from app.dependencies.decisions import get_decision_repository
from app.dependencies.memory import get_memory_repository
from app.memory.historical_context import HistoricalContextService
from app.memory.memory_repository import MemoryRepository
from app.memory.similarity import DecisionSimilarityService
from app.repositories.decision_repository import DecisionRepository


def get_similarity_service() -> DecisionSimilarityService:
    return DecisionSimilarityService()


def get_historical_context_service(
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
    memory_repository: Annotated[MemoryRepository, Depends(get_memory_repository)],
    similarity_service: Annotated[DecisionSimilarityService, Depends(get_similarity_service)],
) -> HistoricalContextService:
    return HistoricalContextService(decision_repository, memory_repository, similarity_service)


HistoricalContextServiceDep = Annotated[
    HistoricalContextService, Depends(get_historical_context_service)
]
