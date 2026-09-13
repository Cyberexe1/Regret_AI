"""FastAPI dependency providers for the Adaptive Decision Interview
Agent (REGRET ENGINE 2.0, Step 27)."""

from typing import Annotated

from fastapi import Depends

from app.dependencies.decisions import get_decision_repository
from app.interview.repository import InterviewRepository
from app.interview.service import InterviewService
from app.repositories.decision_repository import DecisionRepository


def get_interview_repository() -> InterviewRepository:
    return InterviewRepository()


def get_interview_service(
    interview_repository: Annotated[InterviewRepository, Depends(get_interview_repository)],
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
) -> InterviewService:
    return InterviewService(interview_repository, decision_repository)


InterviewServiceDep = Annotated[InterviewService, Depends(get_interview_service)]
