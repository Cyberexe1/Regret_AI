"""Structured external research result.

`ResearchResult` is the ONLY shape a `ResearchProvider` is allowed to
return. Every field here must be traceable to what the provider's search
API actually returned - nothing here is ever populated by an LLM guessing
at what a source probably says. See `app.agents.research_agent` for how
these are later turned into `ExternalEvidence` (a distinct, further step
that DOES involve LLM interpretation, but never invents the fields below).
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from app.research.provider import validate_external_url


class SourceCredibility(StrEnum):
    """The Research Agent's own judgment of how much weight to give a
    source, based only on what's visible in the result itself (source_type,
    source_name, recency) - never fabricated attributes about the source."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class SourceType(StrEnum):
    """Controlled vocabulary for what kind of source a result came from -
    used both for `ResearchResult.source_type` and (mirrored) for
    `ExternalEvidence`'s notion of source. Deliberately does not hardcode a
    credibility ranking (e.g. "government = always true") - credibility is
    assessed contextually by the Research Agent, per the project's explicit
    instruction not to hardcode simplistic source-type-to-credibility
    assumptions."""

    OFFICIAL = "official"
    GOVERNMENT = "government"
    ACADEMIC = "academic"
    NEWS = "news"
    INDUSTRY = "industry"
    COMPANY = "company"
    COMMUNITY = "community"
    OTHER = "other"


class ResearchResult(BaseModel):
    """One search result returned by a `ResearchProvider`, exactly as the
    provider's API reported it - no field here is ever inferred or
    invented downstream.

    `url` is validated at construction time (see `validate_external_url`)
    so a malformed or unsafe URL (wrong scheme, `javascript:`, `file://`,
    `data:`, oversized, etc.) can never enter the pipeline as if it were a
    real source - see `app.research.provider` for the exact rules.
    `published_at` is `None` whenever the provider didn't report one -
    never guessed. `retrieved_at` is always set by the provider/service at
    the moment of the actual search, giving every result a real,
    verifiable timestamp.
    """

    id: UUID = Field(default_factory=uuid4)
    title: str
    url: str
    source_name: str
    snippet: str = Field(
        ..., max_length=2000, description="A short excerpt from the source, never the full page."
    )
    published_at: datetime | None = None
    retrieved_at: datetime
    credibility: SourceCredibility = SourceCredibility.UNKNOWN
    source_type: SourceType = SourceType.OTHER
    query: str

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        return validate_external_url(value)
