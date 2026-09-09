"""FastAPI dependency providers for the analysis feature."""

from typing import Annotated

from fastapi import Depends

from app.agents.orchestrator import AnalysisOrchestrator
from app.dependencies.decisions import get_decision_repository
from app.dependencies.evidence import get_evidence_repository
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.decision_repository import DecisionRepository
from app.repositories.evidence_repository import EvidenceRepository


def get_analysis_repository() -> AnalysisRepository:
    return AnalysisRepository()


def get_analysis_orchestrator(
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
    evidence_repository: Annotated[EvidenceRepository, Depends(get_evidence_repository)],
    analysis_repository: Annotated[AnalysisRepository, Depends(get_analysis_repository)],
) -> AnalysisOrchestrator:
    return AnalysisOrchestrator(decision_repository, evidence_repository, analysis_repository)


AnalysisOrchestratorDep = Annotated[AnalysisOrchestrator, Depends(get_analysis_orchestrator)]
