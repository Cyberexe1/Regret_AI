"""Schemas for entities that hang off a decision.

None of these are exposed through public routes yet - the decision
analysis pipeline that would populate them doesn't exist yet either. They
exist now so the DynamoDB repository layer has a concrete, typed shape to
read and write, and so later steps (assumptions/blindspots/evidence
extraction, stress-testing, experiment design) can be built against a
stable schema instead of ad-hoc dicts.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceStatus(StrEnum):
    UNVERIFIED = "unverified"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"


class SourceType(StrEnum):
    DOCUMENT = "document"
    URL = "url"
    NOTE = "note"


class ExperimentStatus(StrEnum):
    PROPOSED = "proposed"
    RUNNING = "running"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class AnalysisRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Assumption(BaseModel):
    id: UUID
    decision_id: UUID
    statement: str
    importance: str | None = None
    confidence: str | None = None
    evidence_status: EvidenceStatus = EvidenceStatus.UNVERIFIED
    reason: str | None = None
    created_at: datetime
    updated_at: datetime


class Blindspot(BaseModel):
    id: UUID
    decision_id: UUID
    question: str
    importance: str | None = None
    confidence: str | None = None
    reason: str | None = None
    created_at: datetime


class Evidence(BaseModel):
    """Metadata and a reference to evidence content, never the content itself.

    Large uploaded documents belong in Amazon S3 (not implemented yet);
    `storage_key` is reserved for that S3 object key once ingestion exists.
    """

    id: UUID
    decision_id: UUID
    title: str
    source_type: SourceType
    source_url: str | None = None
    storage_key: str | None = Field(default=None, description="Future S3 object key.")
    content_reference: str | None = Field(
        default=None, description="Short reference/summary, not the full document body."
    )
    credibility: str | None = None
    created_at: datetime


class Scenario(BaseModel):
    id: UUID
    decision_id: UUID
    name: str
    description: str
    trigger: str | None = None
    impact: str | None = None
    created_at: datetime


class Threshold(BaseModel):
    id: UUID
    decision_id: UUID
    name: str
    metric: str
    current_value: float | None = None
    threshold_value: float | None = None
    unit: str | None = None
    direction: str | None = None
    impact: str | None = None
    confidence: str | None = None
    created_at: datetime


class Experiment(BaseModel):
    id: UUID
    decision_id: UUID
    title: str
    hypothesis: str
    success_criteria: str | None = None
    failure_criteria: str | None = None
    estimated_cost: float | None = None
    duration_days: int | None = None
    status: ExperimentStatus = ExperimentStatus.PROPOSED
    progress: int = Field(default=0, ge=0, le=100)
    results: str | None = None
    created_at: datetime
    updated_at: datetime


class AnalysisRun(BaseModel):
    id: UUID
    decision_id: UUID
    status: AnalysisRunStatus = AnalysisRunStatus.QUEUED
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
