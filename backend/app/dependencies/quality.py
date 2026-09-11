"""FastAPI dependency providers for the Quality & Calibration Engine
(REGRET ENGINE 2.0, Step 24)."""

from typing import Annotated

from fastapi import Depends

from app.dependencies.decisions import get_decision_repository
from app.dependencies.learning import get_cross_decision_learning_repository
from app.dependencies.memory import get_memory_repository
from app.learning.repository import CrossDecisionLearningRepository
from app.memory.memory_repository import MemoryRepository
from app.quality.repository import CalibrationRepository, QualityRepository
from app.quality.service import CalibrationService, QualityService
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.decision_repository import DecisionRepository
from app.repositories.evidence_repository import EvidenceRepository


def get_analysis_repository() -> AnalysisRepository:
    return AnalysisRepository()


def get_evidence_repository() -> EvidenceRepository:
    return EvidenceRepository()


def get_quality_repository() -> QualityRepository:
    return QualityRepository()


def get_calibration_repository() -> CalibrationRepository:
    return CalibrationRepository()


def get_quality_service(
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
    evidence_repository: Annotated[EvidenceRepository, Depends(get_evidence_repository)],
    analysis_repository: Annotated[AnalysisRepository, Depends(get_analysis_repository)],
    memory_repository: Annotated[MemoryRepository, Depends(get_memory_repository)],
    learning_repository: Annotated[
        CrossDecisionLearningRepository, Depends(get_cross_decision_learning_repository)
    ],
    quality_repository: Annotated[QualityRepository, Depends(get_quality_repository)],
) -> QualityService:
    return QualityService(
        decision_repository,
        evidence_repository,
        analysis_repository,
        memory_repository,
        learning_repository,
        quality_repository,
    )


def get_calibration_service(
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
    calibration_repository: Annotated[CalibrationRepository, Depends(get_calibration_repository)],
) -> CalibrationService:
    return CalibrationService(decision_repository, calibration_repository)


QualityServiceDep = Annotated[QualityService, Depends(get_quality_service)]
CalibrationServiceDep = Annotated[CalibrationService, Depends(get_calibration_service)]
