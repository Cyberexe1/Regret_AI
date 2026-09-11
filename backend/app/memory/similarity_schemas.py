"""Decision Similarity & Historical Insight data model (REGRET ENGINE 2.0).

Three entities, all read-only, all derived from data that already exists
elsewhere in this project - nothing here is a new source of truth:

- `SimilarityScore`: an explainable, deterministic similarity score
  between the decision currently being analyzed and ONE of the same
  user's own past decisions. Never based on embeddings/vector search and
  never computed by an LLM - see `app.memory.similarity`.
- `HistoricalInsight`: one surfaced fact from a past decision's Decision
  Memory (a `MemoryLearning`, see `app.memory.memory_schemas`) that may be
  relevant to a new decision. Always traceable back to the exact learning
  it came from (`learning_id`) and the decision/memory that produced it.
- `HistoricalContext`: the bounded, aggregated result handed to the
  orchestrator and returned to the API - the relevant past decisions, the
  insights drawn from them, and a few deterministic aggregate summaries
  (recurring variables, previously-failed assumptions, previously-
  validated thresholds, unresolved patterns).

CRITICAL, non-negotiable framing (see module docstring in
`app.memory.historical_context` for the full rationale): everything here
is CONTEXT, never a verdict. A `HistoricalInsight`'s `relevance_score` is
explicitly a *historical relevance score* - a deterministic, explainable
number describing "how similar was the source decision", not a
statistically calibrated probability of anything about the new decision.
Nothing in this module is ever applied automatically to change a
threshold, an experiment result, or a user constraint - it is only ever
surfaced for the user (and, as clearly-labeled additional context, the
Decision Analyzer) to consider.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.memory.memory_schemas import LearningSourceType, LearningType


class SimilarityScore(BaseModel):
    """An explainable, deterministic similarity score between the current
    decision and one of the same user's own past decisions.

    Every component that contributed to `score` is named in
    `matched_features`, and `explanation` is a plain-English sentence
    built directly from those same components - never a black-box number.
    See `app.memory.similarity.DecisionSimilarityService` for exactly how
    `score` is computed (decision-type match, key-variable/assumption/
    constraint overlap, and lightweight text similarity - never vector
    embeddings, never an LLM judgment).
    """

    decision_id: UUID = Field(..., description="The id of the past decision being compared.")
    score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Deterministic, explainable similarity score in [0, 1]. NOT a probability "
        "or a statistically calibrated measure of anything - see module docstring.",
    )
    matched_features: list[str] = Field(
        default_factory=list,
        description="Which named scoring components actually contributed (e.g. "
        "'decision_type_match', 'key_variable_overlap') - never a component that scored zero.",
    )
    explanation: str = Field(
        ..., description="Plain-English sentence describing why this past decision was "
        "considered similar, built directly from matched_features - never free-form LLM prose.",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="How much signal actually went into this score - low when the current "
        "decision has very little structured content yet (e.g. before analysis has run) and "
        "the comparison rests on a thin basis, high when many features could be compared.",
    )


class HistoricalInsight(BaseModel):
    """One fact drawn from a past decision's Decision Memory, surfaced as
    potentially relevant context for a new decision.

    Always derived from an existing, already-persisted `MemoryLearning` -
    `learning_id`/`source_decision_id`/`source_memory_id` point at the
    exact records it came from, and `statement` is copied verbatim from
    that learning (never rephrased or reinterpreted at this layer, so
    provenance stays exact). `relevance_score` is deliberately named
    "relevance", not "probability" or "confidence in outcome" - see
    module docstring's evidence-hierarchy framing.
    """

    insight_id: UUID = Field(
        ..., description="Deterministic id derived from (source decision, learning) - see "
        "app.memory.historical_context for the exact derivation.",
    )
    source_decision_id: UUID
    source_memory_id: UUID
    learning_id: UUID
    statement: str = Field(..., description="Copied verbatim from the source MemoryLearning.")
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Historical relevance score: how similar the source decision was to the "
        "current one (mirrors that decision's own SimilarityScore.score). NOT a probability "
        "that this insight applies, and NOT statistically calibrated.",
    )
    relevance_reason: str = Field(
        ..., description="Plain-English reason this insight was surfaced, e.g. 'From a similar "
        "past decision about market entry with a comparable key variable.'",
    )
    learning_type: LearningType
    source_type: LearningSourceType
    observed_value: str | None = None
    expected_value: str | None = None
    related_variable: str | None = Field(
        default=None,
        description="The decision variable this insight is about, if one could be identified "
        "(e.g. the threshold's variable or the assumption's dependency) - used to group "
        "insights into HistoricalContext.recurring_variables.",
    )
    confidence: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Carried over unchanged from the source MemoryLearning's own confidence - "
        "never recomputed or blended with relevance_score.",
    )
    created_at: datetime = Field(
        ..., description="The source MemoryLearning's own created_at - when the underlying "
        "fact was actually learned, not when this insight was surfaced.",
    )


class HistoricalContext(BaseModel):
    """The bounded, aggregated historical context for one (new) decision.

    Everything here is additive context about the SAME user's own past
    decisions - never another user's data (see
    `app.memory.historical_context`'s user-scoping guarantee), and never
    something that changes a current threshold, experiment result, or
    user constraint on its own. `found=False` is the normal, valid
    result for a user with no sufficiently similar past decisions yet -
    never an error.
    """

    found: bool = Field(
        ..., description="Whether at least one sufficiently similar past decision was found."
    )
    relevant_decisions: list[SimilarityScore] = Field(
        default_factory=list,
        description="The user's own past decisions considered relevant, ranked by score, "
        "bounded by HISTORICAL_TOP_K.",
    )
    relevant_decisions_count: int = Field(
        default=0, description="len(relevant_decisions) - included as its own field so API "
        "consumers don't need to count the list themselves.",
    )
    relevant_learnings: list[HistoricalInsight] = Field(
        default_factory=list,
        description="Individual insights drawn from the relevant decisions' memories, bounded "
        "by HISTORICAL_INSIGHT_LIMIT, ranked by relevance_score.",
    )
    recurring_variables: list[str] = Field(
        default_factory=list,
        description="Decision variables (e.g. 'Repeat-order rate') that show up in more than "
        "one relevant past decision's insights - a deterministic aggregate, never inferred.",
    )
    previously_failed_assumptions: list[str] = Field(
        default_factory=list,
        description="Plain statements of assumptions that were previously found "
        "assumption_failed in a relevant past decision's memory.",
    )
    previously_validated_thresholds: list[str] = Field(
        default_factory=list,
        description="Plain statements of thresholds that were previously found "
        "threshold_validated in a relevant past decision's memory.",
    )
    unresolved_patterns: list[str] = Field(
        default_factory=list,
        description="Plain statements of unresolved_uncertainty learnings that recur across "
        "relevant past decisions - patterns that have never actually been tested.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Plain-English caveats about this context (e.g. 'Only 1 past decision was "
        "available for comparison.') - never a warning that implies the current decision is "
        "at risk; purely about the DATA basis of the context itself.",
    )
