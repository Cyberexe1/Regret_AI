"""Request/response schemas for the Decision API.

These describe the shape of data moving across the wire. They intentionally
do not carry any storage or business logic - that lives in
app.services.decisions.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class DecisionStatus(StrEnum):
    """Lifecycle states a decision can be in.

    Only ``draft`` is reachable in this step - the rest are reserved for the
    upcoming analysis pipeline (agents, evidence collection, experiments).
    """

    DRAFT = "draft"
    QUEUED = "queued"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    NEEDS_VALIDATION = "needs_validation"
    ARCHIVED = "archived"


class DecisionCreate(BaseModel):
    """Payload for submitting a new decision to be analyzed."""

    title: str = Field(
        ..., min_length=1, max_length=200, description="Short label for the decision."
    )
    description: str = Field(
        ..., min_length=1, max_length=5000, description="Full decision statement."
    )
    desired_outcome: str | None = Field(default=None, max_length=2000)
    budget: float | None = Field(default=None, ge=0, description="Available budget, if any.")
    currency: str | None = Field(
        default=None, max_length=8, description="ISO currency code, e.g. USD."
    )
    timeline: str | None = Field(
        default=None, max_length=200, description="Expected timeframe, free text."
    )
    location: str | None = Field(default=None, max_length=200)
    risk_tolerance: str | None = Field(default=None, max_length=50)
    beliefs: str | None = Field(
        default=None, max_length=5000, description="Stated assumptions or beliefs."
    )


class DecisionUpdate(BaseModel):
    """Partial update payload. Only provided fields are changed.

    `expected_updated_at`, when provided, is used as an optimistic-concurrency
    guard: the update is rejected with a conflict if the stored decision's
    `updated_at` no longer matches, i.e. it was changed by someone else since
    the client last read it.
    """

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    desired_outcome: str | None = Field(default=None, max_length=2000)
    budget: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=8)
    timeline: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    risk_tolerance: str | None = Field(default=None, max_length=50)
    beliefs: str | None = Field(default=None, max_length=5000)
    status: DecisionStatus | None = None
    expected_updated_at: datetime | None = Field(
        default=None,
        description="Optional optimistic-concurrency guard. Omit to update unconditionally.",
    )


class DecisionResponse(BaseModel):
    """Representation of a stored decision returned by the API.

    Deliberately omits `user_id`: there is no real authentication yet, so
    that field is an internal attribution detail rather than something a
    client needs back.
    """

    id: UUID
    title: str
    description: str
    desired_outcome: str | None = None
    budget: float | None = None
    currency: str | None = None
    timeline: str | None = None
    location: str | None = None
    risk_tolerance: str | None = None
    beliefs: str | None = None
    status: DecisionStatus
    created_at: datetime
    updated_at: datetime


class DecisionListResponse(BaseModel):
    """A page of decisions plus an opaque cursor for the next page."""

    items: list[DecisionResponse]
    next_cursor: str | None = Field(
        default=None, description="Pass as `cursor` on the next request. Omit when None."
    )
