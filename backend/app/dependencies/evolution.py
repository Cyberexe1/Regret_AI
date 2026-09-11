"""FastAPI dependency providers for the Decision Evolution feature
(REGRET ENGINE 2.0, Step 22)."""

from typing import Annotated

from fastapi import Depends

from app.adaptive.repository import AdaptiveStateRepository
from app.core.config import get_settings
from app.dependencies.adaptive import get_adaptive_state_repository
from app.dependencies.decisions import get_decision_repository
from app.dependencies.memory import get_memory_repository
from app.dependencies.value_of_information import get_value_of_information_repository
from app.evolution.repository import DecisionEvolutionRepository
from app.evolution.service import DecisionEvolutionService
from app.memory.memory_repository import MemoryRepository
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.decision_repository import DecisionRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.value_of_information_repository import ValueOfInformationRepository


def get_analysis_repository() -> AnalysisRepository:
    return AnalysisRepository()


def get_evidence_repository() -> EvidenceRepository:
    return EvidenceRepository()


def get_decision_evolution_repository(
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
    analysis_repository: Annotated[AnalysisRepository, Depends(get_analysis_repository)],
    evidence_repository: Annotated[EvidenceRepository, Depends(get_evidence_repository)],
    memory_repository: Annotated[MemoryRepository, Depends(get_memory_repository)],
    voi_repository: Annotated[
        ValueOfInformationRepository, Depends(get_value_of_information_repository)
    ],
    adaptive_repository: Annotated[AdaptiveStateRepository, Depends(get_adaptive_state_repository)],
) -> DecisionEvolutionRepository:
    return DecisionEvolutionRepository(
        decision_repository,
        analysis_repository,
        evidence_repository,
        memory_repository,
        voi_repository,
        adaptive_repository,
    )


def get_decision_evolution_service(
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
    evolution_repository: Annotated[
        DecisionEvolutionRepository, Depends(get_decision_evolution_repository)
    ],
) -> DecisionEvolutionService:
    settings = get_settings()
    return DecisionEvolutionService(
        decision_repository, evolution_repository, max_events=settings.evolution_max_events
    )


DecisionEvolutionServiceDep = Annotated[
    DecisionEvolutionService, Depends(get_decision_evolution_service)
]
