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
    """Metadata, extracted text, and a storage reference for one piece of evidence.

    The full original file lives in a `StorageBackend` (local disk today,
    S3 later) under `storage_key` - never inline in this record.
    `content_reference` holds extracted text up to a bounded length so this
    record stays a metadata-sized object rather than duplicating an entire
    large document; `content_truncated` says whether that bound was hit.
    """

    id: UUID
    decision_id: UUID
    title: str
    source_type: SourceType
    source_url: str | None = None
    storage_key: str | None = Field(
        default=None, description="Key into the storage backend (local path today, S3 key later)."
    )
    filename: str | None = Field(default=None, description="Original filename, sanitized.")
    file_type: str | None = Field(
        default=None, description="Extension without the dot, e.g. 'pdf'."
    )
    size_bytes: int | None = None
    page_count: int | None = Field(default=None, description="Available for PDF; null otherwise.")
    content_reference: str | None = Field(
        default=None, description="Extracted text, bounded in length - not the full document body."
    )
    content_truncated: bool = Field(
        default=False, description="True if extracted text exceeded the stored bound."
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
    # Structured agent output for this run (currently just the Decision
    # Analyzer's DecisionAnalysis, dumped to a plain dict). Stored as a
    # generic dict rather than a specific model type here so this schema
    # doesn't need to change as more agents contribute to a run later.
    result: dict[str, object] | None = None
