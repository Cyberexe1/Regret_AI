"""Structured output schemas for the agent pipeline.

The Decision Analyzer's output is validated against `DecisionAnalysis`
before it's ever persisted or returned - if the model's response doesn't
conform, that's an application-level error (see
`app.agents.orchestrator`), never silently-accepted malformed data.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class InformationClassification(StrEnum):
    """Every claim the analyzer makes must be labeled as one of these.

    This is the mechanism that keeps the analyzer honest about what it
    actually knows versus what it's guessing - see the system prompt in
    `app.agents.decision_analyzer`.
    """

    FACT = "fact"
    ASSUMPTION = "assumption"
    UNKNOWN = "unknown"


class ImportanceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Assumption(BaseModel):
    """A single belief the decision rests on, as identified by the analyzer."""

    statement: str = Field(..., description="The assumption, stated plainly.")
    importance: ImportanceLevel = Field(
        ..., description="How much this assumption matters to the decision's outcome."
    )
    confidence: ConfidenceLevel = Field(
        ..., description="How confident the analyzer is that this assumption holds."
    )
    classification: InformationClassification = Field(
        ...,
        description=(
            "Whether this is a verified FACT, an unverified ASSUMPTION being treated as "
            "true, or something genuinely UNKNOWN that needs investigation."
        ),
    )
    reason: str = Field(..., description="Why this was identified as important.")


class DecisionAnalysis(BaseModel):
    """Structured understanding of a decision, produced by the Decision Analyzer.

    This is a first pass at understanding the decision, not a
    recommendation - it exists so downstream agents (assumption hunter,
    blindspot hunter, etc., not yet implemented) have a shared, structured
    starting point instead of re-parsing raw decision text each time.
    """

    decision_summary: str = Field(
        ...,
        description="One or two sentence restatement of the decision in the analyzer's own words.",
    )
    decision_type: str = Field(
        ...,
        description=(
            "Short category label for the kind of decision this is, e.g. "
            "'market entry', 'hiring', 'pricing change', 'build vs buy'."
        ),
    )
    goal: str = Field(..., description="The primary objective this decision is meant to achieve.")
    constraints: list[str] = Field(
        default_factory=list,
        description="Hard limits the decision must operate within (budget, time, etc.).",
    )
    success_criteria: list[str] = Field(
        default_factory=list, description="Concrete, checkable signs that the decision worked."
    )
    key_variables: list[str] = Field(
        default_factory=list,
        description="The handful of factors this decision's outcome most depends on.",
    )
    initial_assumptions: list[Assumption] = Field(
        default_factory=list,
        description="Beliefs the decision rests on, each classified fact/assumption/unknown.",
    )
    unknowns: list[str] = Field(
        default_factory=list,
        description="Important open questions the analyzer could not resolve from context.",
    )
