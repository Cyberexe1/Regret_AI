"""FastAPI dependency providers for the Value-of-Information feature
(REGRET ENGINE 2.0, Step 20)."""

from typing import Annotated

from fastapi import Depends

from app.agents.value_of_information import ValueOfInformationService
from app.dependencies.decisions import get_decision_repository
from app.dependencies.historical_context import get_historical_context_service
from app.dependencies.learning import get_cross_decision_learning_service
from app.learning.service import CrossDecisionLearningService
from app.memory.historical_context import HistoricalContextService
from app.repositories.decision_repository import DecisionRepository
from app.repositories.value_of_information_repository import ValueOfInformationRepository


def get_value_of_information_repository() -> ValueOfInformationRepository:
    return ValueOfInformationRepository()


def get_value_of_information_service(
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
    voi_repository: Annotated[
        ValueOfInformationRepository, Depends(get_value_of_information_repository)
    ],
    historical_context_service: Annotated[
        HistoricalContextService, Depends(get_historical_context_service)
    ],
    cross_decision_learning_service: Annotated[
        CrossDecisionLearningService, Depends(get_cross_decision_learning_service)
    ],
) -> ValueOfInformationService:
    return ValueOfInformationService(
        decision_repository, voi_repository, historical_context_service,
        cross_decision_learning_service,
    )


ValueOfInformationServiceDep = Annotated[
    ValueOfInformationService, Depends(get_value_of_information_service)
]
