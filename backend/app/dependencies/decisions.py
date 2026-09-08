"""FastAPI dependency providers for the decision feature."""

from typing import Annotated

from fastapi import Depends

from app.dependencies.auth import get_current_user_id
from app.repositories.decision_repository import DecisionRepository
from app.services.decisions import DecisionService


def get_decision_repository() -> DecisionRepository:
    return DecisionRepository()


def get_decision_service(
    repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
) -> DecisionService:
    return DecisionService(repository)


DecisionServiceDep = Annotated[DecisionService, Depends(get_decision_service)]
CurrentUserIdDep = Annotated[str, Depends(get_current_user_id)]
