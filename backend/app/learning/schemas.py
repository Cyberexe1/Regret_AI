"""Cross-Decision Learning data model (REGRET ENGINE 2.0, Step 23).

`CrossDecisionPattern` is the one new persisted entity this step adds -
a recurring observation across a user's OWN past decisions, never
fabricated: every pattern is backed by at least the minimum evidence
policy in `app.learning.pattern_detector` (never a "strong" pattern from
one observation), and every supporting/contradicting decision is a real,
already-persisted id. `PatternOccurrence` is the provenance record that
makes "why did REGRET learn this?" always answerable - each occurrence
points at one real canonical record (`source_type`/`source_id`).

Nothing here claims statistical significance. `confidence` is an
evidence-based heuristic band (low/medium/high), never a fabricated
percentage - see `pattern_detector.py`'s own confidence-scoring docstring.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class PatternType(StrEnum):
    """What kind of recurring observation this pattern describes - each
    value corresponds to a specific, deterministic detection rule in
    `app.learning.pattern_detector` (never an inference invented at this
    layer). Mirrors the vocabulary already established by
    `app.memory.memory_schemas.LearningType` where the concepts overlap.
    """

    RECURRING_FAILED_ASSUMPTION = "recurring_failed_assumption"
    RECURRING_VALIDATED_ASSUMPTION = "recurring_validated_assumption"
    RECURRING_THRESHOLD_FAILURE = "recurring_threshold_failure"
    RECURRING_THRESHOLD_VALIDATION = "recurring_threshold_validation"
    RECURRING_UNCERTAINTY = "recurring_uncertainty"
    RECURRING_EXPERIMENT_LEARNING = "recurring_experiment_learning"
    RECURRING_EXPERIMENT_SUCCESS = "recurring_experiment_success"
    RECURRING_EXPERIMENT_FAILURE = "recurring_experiment_failure"
    RECURRING_UNRESOLVED_QUESTION = "recurring_unresolved_question"
    RECURRING_UNEXPECTED_RESULT = "recurring_unexpected_result"


class PatternStatus(StrEnum):
    """A pattern's current standing in its own lifecycle (spec section
    19) - never jumps straight to a strong status from a single
    observation; see `app.learning.pattern_detector`'s minimum-evidence
    policy for the exact occurrence-count thresholds that move a pattern
    between these.

    Deliberately no "proven" value: this system never claims statistical
    proof from observational decision history (spec's own explicit rule)
    - `ESTABLISHED` is the strongest status it will ever assign, and only
    when the evidence is genuinely consistent.
    """

    EMERGING = "emerging"
    REPEATED = "repeated"
    ESTABLISHED = "established"
    CONTRADICTED = "contradicted"
    INACTIVE = "inactive"


class PatternConfidence(StrEnum):
    """Evidence-based confidence band - never a fabricated probability
    (spec section 6: no "87% likely" without a real deterministic/
    statistical calculation, which this system never performs)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OccurrenceRelation(StrEnum):
    """Whether one real observation SUPPORTS, CONTRADICTS, or only
    PARTIALLY_SUPPORTS the pattern it's attached to - see spec section
    18's conflict-handling requirement: mixed evidence must be shown as
    mixed, never silently collapsed into one confident claim."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    PARTIALLY_SUPPORTS = "partially_supports"


class HistoricalLearningSignal(StrEnum):
    """How strongly a user's own cross-decision history bears on one
    uncertainty in the CURRENT decision's Value-of-Information ranking
    (spec section 14) - a tiebreaker-strength signal, never something
    that overrides current evidence or the deterministic VOI formula
    itself. See `app.services.value_of_information_service`'s own
    "historical relevance is a tiebreaker only" principle, which this
    mirrors exactly rather than replacing."""

    NONE = "none"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class PatternOccurrence(BaseModel):
    """One real, traceable observation that supports (or contradicts) a
    `CrossDecisionPattern` - the provenance record that makes "why did
    REGRET learn this?" always answerable with a real record id, never a
    fabricated citation.

    `source_type`/`source_id` always point at one of: a `MemoryLearning`
    (`memory_learning`), a `ReEvaluation` (`re_evaluation`), an
    `ExperimentResult` (`experiment_result`), a `Threshold` (`threshold`),
    or an `Assumption`/`Blindspot` (`assumption`/`blindspot`) for an
    unresolved-uncertainty occurrence with no result yet.
    """

    occurrence_id: str = Field(
        ...,
        description="Deterministic, derived from (pattern_id, decision_id, source_type, "
        "source_id) - the same real record always produces the same occurrence id, so a "
        "refresh can never create a duplicate occurrence for the same evidence.",
    )
    pattern_id: str
    user_id: str
    decision_id: str
    learning_id: str | None = None
    source_type: str
    source_id: str
    observation: str = Field(
        ...,
        description="A single, factual sentence describing what was observed - copied "
        "or lightly re-labelled from the source record's own text, never a fabricated "
        "causal claim it doesn't support.",
    )
    observed_at: datetime
    relation: OccurrenceRelation
    confidence: float = Field(..., ge=0.0, le=1.0)


class CrossDecisionPattern(BaseModel):
    """A recurring observation across a user's OWN past decisions -
    never derived from, or shared with, any other user's data (see this
    package's own module docstring on user isolation).

    `normalized_key` is the deterministic grouping key (see
    `app.learning.normalization`) that let multiple decisions'
    observations be recognized as "the same recurring thing" - always a
    structured match (an exact/normalized variable name, decision type,
    or experiment type), never a semantic/embedding-based guess.

    Append-only bookkeeping fields (`occurrence_count`, `evidence_count`,
    `supporting_*_ids`, `contradicting_decision_ids`) are recomputed by
    `CrossDecisionLearningService.refresh_patterns` from the CURRENT set
    of canonical records every time it runs - the pattern record itself
    is upserted (never duplicated) via a deterministic `pattern_id`, and
    is never deleted merely for becoming `inactive` (spec section 19:
    "preserve provenance").
    """

    pattern_id: str = Field(
        ...,
        description="Deterministic, derived from (user_id, pattern_type, normalized_key) "
        "- the same recurring concept for the same user always upserts the same record, "
        "never creating a duplicate on refresh.",
    )
    user_id: str
    pattern_type: PatternType
    title: str = Field(
        ...,
        description="Short, human-readable label, e.g. 'Retention "
        "assumptions have repeatedly underperformed.'",
    )
    statement: str = Field(
        ...,
        description="The full, hedged statement shown to the user - phrased as a "
        "tendency observed in THEIR past decisions, never a prediction about the current "
        "one (spec section 13: never 'therefore your current X will fail').",
    )
    normalized_key: str
    variable: str | None = None
    domain: str | None = None
    decision_types: list[str] = Field(default_factory=list)
    occurrence_count: int = Field(..., ge=0)
    supporting_decision_ids: list[str] = Field(default_factory=list)
    supporting_learning_ids: list[str] = Field(default_factory=list)
    supporting_experiment_ids: list[str] = Field(default_factory=list)
    supporting_threshold_ids: list[str] = Field(default_factory=list)
    contradicting_decision_ids: list[str] = Field(default_factory=list)
    evidence_count: int = Field(..., ge=0)
    confidence: PatternConfidence
    confidence_basis: str = Field(
        ...,
        description="Plain-language explanation of why this confidence band was "
        "assigned - built only from real counts (supporting/contradicting decisions, "
        "observed-result vs speculative-analysis evidence), never a fabricated justification.",
    )
    first_seen_at: datetime
    last_seen_at: datetime
    status: PatternStatus
    created_at: datetime
    updated_at: datetime


class CrossDecisionPatternDetail(BaseModel):
    """Composite response for `GET /learning/patterns/{pattern_id}` -
    bundles the pattern with its full, real provenance in one call, so
    "show me why" never requires a second round of per-occurrence
    lookups."""

    pattern: CrossDecisionPattern
    occurrences: list[PatternOccurrence] = Field(default_factory=list)
    supporting_occurrences: list[PatternOccurrence] = Field(default_factory=list)
    contradicting_occurrences: list[PatternOccurrence] = Field(default_factory=list)


class CrossDecisionPatternListResponse(BaseModel):
    """Response for `GET /learning/patterns` and
    `GET /decisions/{id}/patterns`."""

    patterns: list[CrossDecisionPattern] = Field(default_factory=list)


class PatternRefreshResponse(BaseModel):
    """Response for `POST /learning/patterns/refresh` - reports what the
    rebuild actually did, never silently succeeds with no visibility."""

    user_id: str
    patterns_created: int
    patterns_updated: int
    patterns_unchanged: int
    total_patterns: int
    refreshed_at: datetime
