"""FastAPI dependency providers for the Decision Memory feature."""

from typing import Annotated

from fastapi import Depends

from app.dependencies.decisions import get_decision_repository
from app.memory.memory_repository import MemoryRepository
from app.memory.memory_service import MemoryService
from app.repositories.decision_repository import DecisionRepository


def get_memory_repository() -> MemoryRepository:
    return MemoryRepository()


def get_memory_service(
    memory_repository: Annotated[MemoryRepository, Depends(get_memory_repository)],
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
) -> MemoryService:
    return MemoryService(memory_repository, decision_repository)


MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]
