"""FastAPI dependency providers for the decision analysis child-entity
retrieval feature (assumptions, blindspots, evidence findings, challenges,
regret scenarios, thresholds, re-evaluations)."""

from typing import Annotated

from fastapi import Depends

from app.dependencies.decisions import get_decision_repository
from app.repositories.decision_repository import DecisionRepository
from app.services.decision_analysis_resources import DecisionAnalysisResourcesService


def get_decision_analysis_resources_service(
    repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
) -> DecisionAnalysisResourcesService:
    return DecisionAnalysisResourcesService(repository)


DecisionAnalysisResourcesServiceDep = Annotated[
    DecisionAnalysisResourcesService, Depends(get_decision_analysis_resources_service)
]
