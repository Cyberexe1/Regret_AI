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
    """How an assumption stands against evidence actually submitted for its
    decision. Mirrors `app.agents.schemas.AssumptionEvidenceStatus` so the
    storage layer and the agent's own findings use the same vocabulary.

    UNVERIFIED is the pre-analysis default for assumptions created outside
    the agent pipeline; the Assumption Hunter always assigns one of the
    other three explicitly.
    """

    UNVERIFIED = "unverified"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    NOT_ADDRESSED = "not_addressed"


class SourceType(StrEnum):
    DOCUMENT = "document"
    URL = "url"
    NOTE = "note"


class ExperimentStatus(StrEnum):
    """Lifecycle state of one recommended experiment. Mirrors
    `app.agents.schemas.ExperimentPlanStatus`.

    The Experiment Planner always creates experiments as RECOMMENDED;
    later API endpoints move an experiment through
    PLANNED/ACTIVE/COMPLETED/CANCELLED as the user actually acts on it.
    """

    RECOMMENDED = "recommended"
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AnalysisRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AssumptionSource(StrEnum):
    """Whether the decision owner stated the assumption outright, or is
    relying on it without ever saying so. Mirrors
    `app.agents.schemas.AssumptionSource`."""

    EXPLICIT = "explicit"
    IMPLICIT = "implicit"


class Assumption(BaseModel):
    """A stored assumption underpinning a decision.

    Populated by the Assumption Hunter (see `app.agents.assumption_hunter`
    and `AnalysisOrchestrator`), one row per `AssumptionFinding` it
    returns. `source`, `dependency`, and `failure_consequence` are new in
    this step; `confidence` moved from a coarse level to a 0.0-1.0 float to
    match the agent's own schema.
    """

    id: UUID
    decision_id: UUID
    statement: str
    source: AssumptionSource | None = None
    importance: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_status: EvidenceStatus = EvidenceStatus.UNVERIFIED
    dependency: str | None = Field(
        default=None, description="What part of the decision this assumption underpins."
    )
    failure_consequence: str | None = Field(
        default=None, description="What happens to the decision if this assumption is false."
    )
    reason: str | None = None
    created_at: datetime
    updated_at: datetime


class BlindspotEvidenceStatus(StrEnum):
    """How a stored blindspot stands against evidence actually submitted for
    its decision. Mirrors `app.agents.schemas.BlindspotEvidenceStatus`.

    UNKNOWN is the pre-analysis default for blindspots created outside the
    agent pipeline; the Blindspot Hunter always assigns one of the other
    four explicitly.
    """

    UNKNOWN = "unknown"
    ALREADY_SUPPORTED = "already_supported"
    PARTIALLY_ADDRESSED = "partially_addressed"
    CONTRADICTED = "contradicted"
    NOT_ADDRESSED = "not_addressed"


class Blindspot(BaseModel):
    """A stored blindspot for a decision.

    Populated by the Blindspot Hunter (see `app.agents.blindspot_hunter`
    and `AnalysisOrchestrator`), one row per `BlindspotFinding` it returns.
    `category`, `evidence_status`, `related_assumption_ids`,
    `why_it_matters`, and `evidence_gap` are new in this step; `confidence`
    moved from a coarse string to a 0.0-1.0 float to match the agent's own
    schema, mirroring the same change made to `Assumption` previously.
    """

    id: UUID
    decision_id: UUID
    question: str
    category: str | None = None
    importance: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_status: BlindspotEvidenceStatus = BlindspotEvidenceStatus.UNKNOWN
    related_assumption_ids: list[str] = Field(default_factory=list)
    why_it_matters: str | None = None
    evidence_gap: str | None = None
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


class EvidenceFinding(BaseModel):
    """A stored mapping between one real piece of evidence and the specific
    assumption/blindspot claim(s) it bears on.

    Populated by the Evidence Agent (see `app.agents.evidence_agent` and
    `AnalysisOrchestrator`), one row per `EvidenceFinding` (the agent's own
    schema, `app.agents.schemas.EvidenceFinding`) it returns. Persisted
    under `SK=EVIDENCE_FINDING#<finding_id>`, separate from the original
    `Evidence` record (`SK=EVIDENCE#<evidence_id>`) it references - the
    Evidence Agent's analysis never overwrites the source it analyzed.
    """

    id: UUID
    decision_id: UUID
    evidence_id: UUID
    claim: str
    support_level: str | None = None
    credibility: str | None = None
    related_assumption_ids: list[str] = Field(default_factory=list)
    related_blindspot_ids: list[str] = Field(default_factory=list)
    explanation: str | None = None
    excerpt: str | None = None
    created_at: datetime


class Challenge(BaseModel):
    """A stored challenge (attack on the decision) for a decision.

    Populated by the Devil's Advocate (see `app.agents.devils_advocate` and
    `AnalysisOrchestrator`), one row per `Challenge` (the agent's own
    schema, `app.agents.schemas.Challenge`) it returns. Persisted under
    `SK=CHALLENGE#<challenge_id>`.
    """

    id: UUID
    decision_id: UUID
    claim: str
    attack: str
    severity: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    related_assumption_ids: list[str] = Field(default_factory=list)
    related_blindspot_ids: list[str] = Field(default_factory=list)
    related_evidence_finding_ids: list[str] = Field(default_factory=list)
    failure_mechanism: str | None = None
    evidence_basis: str | None = None
    created_at: datetime


class RegretScenario(BaseModel):
    """A stored regret scenario for a decision.

    Populated by the Regret Simulator (see `app.agents.regret_simulator`
    and `AnalysisOrchestrator`), one row per `RegretScenario` (the agent's
    own schema, `app.agents.schemas.RegretScenario`) it returns. Persisted
    under `SK=REGRET_SCENARIO#<scenario_id>` - `id` here is the real,
    persisted id assigned by the repository, distinct from the agent's own
    response-scoped `id` label (see the agent schema's docstring).
    """

    id: UUID
    decision_id: UUID
    title: str
    failure_condition: str
    probability_band: str | None = None
    impact: str | None = None
    regret_level: str | None = None
    trigger_variable: str | None = None
    trigger_direction: str | None = None
    provisional_threshold: str | None = None
    consequence: str | None = None
    related_assumption_ids: list[str] = Field(default_factory=list)
    related_challenge_ids: list[str] = Field(default_factory=list)
    evidence_basis: str | None = None
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
    """A stored threshold (tipping point) for a decision.

    Populated by the Threshold Engine (see `app.agents.threshold_engine`
    and `AnalysisOrchestrator`), one row per `Threshold` (the agent's own
    schema, `app.agents.schemas.Threshold`) it returns. Persisted under
    `SK=THRESHOLD#<threshold_id>` - `id` here is the real, persisted id
    assigned by the repository, distinct from the agent's own
    response-scoped `id` label (see the agent schema's docstring).

    Replaces the earlier placeholder shape (name/metric/current_value) with
    the full field set the Threshold Engine actually produces.
    """

    id: UUID
    decision_id: UUID
    variable: str
    threshold_type: str | None = None
    direction: str | None = None
    threshold_value: str | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    unit: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    derivation: str | None = None
    consequence: str | None = None
    related_regret_scenario_ids: list[str] = Field(default_factory=list)
    related_assumption_ids: list[str] = Field(default_factory=list)
    evidence_basis: str | None = None
    validation_status: str | None = None
    calculation_formula: str | None = None
    calculation_inputs: dict[str, float] | None = None
    calculation_provenance: str | None = None
    created_at: datetime


class Experiment(BaseModel):
    """A stored, recommended experiment for a decision.

    Populated by the Experiment Planner (see `app.agents.experiment_planner`
    and `AnalysisOrchestrator`), one row per `Experiment` (the agent's own
    schema, `app.agents.schemas.Experiment`) it returns. Persisted under
    `SK=EXPERIMENT#<experiment_id>` - `id` here is the real, persisted id
    assigned by the repository, distinct from the agent's own
    response-scoped `id` label (see the agent schema's docstring).

    Replaces the earlier placeholder shape (title/hypothesis/progress) with
    the full field set the Experiment Planner actually produces.
    `GSI2PK`/`GSI2SK` (see `EvidenceRepository.get_by_id` for the same
    pattern) let `GET /api/v1/experiments/{experiment_id}` resolve an
    experiment by its own id alone, without knowing its parent decision.
    """

    id: UUID
    decision_id: UUID
    title: str
    objective: str | None = None
    hypothesis: str
    target_threshold_id: str | None = None
    variable_to_test: str | None = None
    experiment_type: str | None = None
    steps: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    failure_criteria: list[str] = Field(default_factory=list)
    duration_days: int | None = None
    estimated_cost: float | None = None
    currency: str | None = None
    evidence_to_collect: list[str] = Field(default_factory=list)
    decision_rule: str | None = None
    expected_information_gain: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    feasibility: str | None = None
    reversibility: str | None = None
    related_assumption_ids: list[str] = Field(default_factory=list)
    related_regret_scenario_ids: list[str] = Field(default_factory=list)
    status: ExperimentStatus = ExperimentStatus.RECOMMENDED
    created_at: datetime
    updated_at: datetime


class ExperimentOutcome(StrEnum):
    """The user-declared outcome of running an experiment.

    This is an observation supplied by the user, not an AI interpretation -
    see `ExperimentResult` docstring. `ReEvaluationService` treats it as a
    secondary signal, preferring the deterministic threshold comparison
    (see `app.services.threshold_comparison`) whenever real measured
    values are available, and falling back to this declared outcome only
    when no numeric comparison can be made.
    """

    SUCCESS = "success"
    FAILURE = "failure"
    INCONCLUSIVE = "inconclusive"
    PARTIAL = "partial"


class ExperimentResult(BaseModel):
    """A stored, user-submitted observation of what actually happened when
    an experiment was run.

    This is deliberately a record of OBSERVED reality, not an AI
    interpretation of it - `outcome`, `summary`, `observations`, and
    `measured_values` are exactly what the user reported. Any
    interpretation (whether a measured value met a threshold, what it
    means for an assumption) lives in the separate `ReEvaluation` record
    that references this one - the two are never merged into a single
    entity, so "what was observed" always stays distinguishable from "what
    we concluded from it." Persisted under
    `SK=EXPERIMENT_RESULT#<experiment_id>#<result_id>`, scoped by
    experiment id within the decision partition so results can be listed
    either per-experiment or per-decision without a second index.
    """

    id: UUID
    decision_id: UUID
    experiment_id: UUID
    outcome: ExperimentOutcome
    summary: str
    observations: list[str] = Field(default_factory=list)
    measured_values: dict[str, str | float | int | bool] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="Real, already-uploaded Evidence ids the user attached to this result. "
        "Validated against the decision's actual evidence before persistence - never a "
        "fabricated id.",
    )
    notes: str | None = None
    completed_at: datetime


class ThresholdComparisonStatus(StrEnum):
    """The deterministic outcome of comparing an experiment's observed
    value against a threshold's recorded value - computed in plain Python
    by `app.services.threshold_comparison`, never by an LLM.

    ABOVE/BELOW describe the raw numeric relationship when no clear
    required direction lets it be scored as MET/MISSED. WITHIN_RANGE/
    OUTSIDE_RANGE apply to RANGE-type thresholds. INCONCLUSIVE means a
    comparison was attempted but the threshold/direction combination
    doesn't support a clear required-vs-not judgment. UNKNOWN means no
    comparison could be attempted at all (missing/malformed/non-numeric
    value, or the threshold itself has no comparable value).
    """

    ABOVE = "above"
    BELOW = "below"
    WITHIN_RANGE = "within_range"
    OUTSIDE_RANGE = "outside_range"
    MET = "met"
    MISSED = "missed"
    INCONCLUSIVE = "inconclusive"
    UNKNOWN = "unknown"


class ThresholdComparison(BaseModel):
    """One threshold's deterministic comparison result for a single
    experiment result. Never mutates the original `Threshold` record - see
    the module-level "never automatically change the original threshold"
    principle; this is a new, separate assessment that references the
    threshold by id, preserving history rather than overwriting it.
    """

    threshold_id: str
    variable: str
    observed_value: str | None = None
    threshold_value: str | None = None
    status: ThresholdComparisonStatus
    explanation: str


class AssumptionReevaluationStatus(StrEnum):
    """How an assumption's standing changes in light of new experiment
    evidence. Never automatically "false" - CONTRADICTED is used only when
    the experiment genuinely establishes that, not merely when evidence is
    unfavorable."""

    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONTRADICTED = "contradicted"
    STILL_UNCERTAIN = "still_uncertain"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class AssumptionReevaluation(BaseModel):
    """One assumption's deterministic re-evaluation for a single experiment
    result. Never mutates the original `Assumption` record - a new,
    separate assessment referencing it by id."""

    assumption_id: str
    previous_status: str | None = None
    new_status: AssumptionReevaluationStatus
    explanation: str


class RegretScenarioReevaluationStatus(StrEnum):
    """How a regret scenario's standing changes in light of new experiment
    evidence."""

    PLAUSIBLE = "plausible"
    EVIDENCE_STRENGTHENED = "evidence_strengthened"
    EVIDENCE_WEAKENED = "evidence_weakened"
    STILL_UNCERTAIN = "still_uncertain"


class RegretScenarioReevaluation(BaseModel):
    """One regret scenario's deterministic re-evaluation for a single
    experiment result. Never mutates the original `RegretScenario` record -
    a new, separate assessment referencing it by id."""

    regret_scenario_id: str
    previous_status: str | None = None
    new_status: RegretScenarioReevaluationStatus
    explanation: str


class DecisionAssessmentStatus(StrEnum):
    """Whether an experiment made the original decision more or less
    defensible. Deliberately NOT a buy/sell/invest/do-not-invest verdict -
    REGRET ENGINE validates decisions, it does not make them."""

    STRENGTHENED = "strengthened"
    WEAKENED = "weakened"
    UNCHANGED = "unchanged"
    INCONCLUSIVE = "inconclusive"
    REQUIRES_MORE_EVIDENCE = "requires_more_evidence"


class DecisionAssessment(BaseModel):
    """A structured judgment of whether an experiment strengthened or
    weakened the original decision's defensibility - never a final verdict
    on the decision itself.

    `confidence` reflects how much the underlying comparison data actually
    supports this specific assessment (i.e. how deterministic/complete the
    inputs were - real measured values matched against a real numeric
    threshold score higher than a declared-outcome fallback with no
    numeric comparison at all). It is NEVER a probability that the
    decision will succeed or fail - see the module-level "never present
    confidence as probability" principle carried over from the Threshold
    Engine.
    """

    status: DecisionAssessmentStatus
    confidence: float = Field(..., ge=0.0, le=1.0)
    summary: str
    changed_assumptions: list[str] = Field(default_factory=list)
    affected_thresholds: list[str] = Field(default_factory=list)
    affected_regret_scenarios: list[str] = Field(default_factory=list)
    recommended_next_step: str
    evidence_basis: list[str] = Field(default_factory=list)


class ReEvaluation(BaseModel):
    """A stored record of what REGRET ENGINE learned by comparing one
    experiment's observed result against the original analysis.

    This is the append-only history record: it never overwrites the
    original `AnalysisRun`, `Threshold`, `Assumption`, or `RegretScenario`
    records it references - every re-evaluation is a new entity, so a
    decision's timeline (`Analysis -> Experiment -> Result ->
    Re-evaluation -> Experiment -> Result -> Re-evaluation -> ...`) stays
    fully reconstructable. Persisted under `SK=REEVALUATION#<id>`.
    Produced deterministically by `app.services.re_evaluation_service` -
    no LLM call is involved in computing any of these fields.
    """

    id: UUID
    decision_id: UUID
    experiment_id: UUID
    experiment_result_id: UUID
    previous_assessment: str
    new_assessment: str
    threshold_comparisons: list[ThresholdComparison] = Field(default_factory=list)
    assumption_reevaluations: list[AssumptionReevaluation] = Field(default_factory=list)
    regret_scenario_reevaluations: list[RegretScenarioReevaluation] = Field(default_factory=list)
    decision_assessment: DecisionAssessment
    changed_thresholds: list[str] = Field(default_factory=list)
    changed_assumptions: list[str] = Field(default_factory=list)
    changed_regret_scenarios: list[str] = Field(default_factory=list)
    key_learning: str
    recommended_next_step: str
    created_at: datetime


class ExternalEvidence(BaseModel):
    """A stored mapping between one real external research result and the
    specific assumption/blindspot/threshold claim(s) it bears on.

    Populated by the Research Agent (see `app.agents.research_agent` and
    `AnalysisOrchestrator`), one row per `ExternalEvidence` (the agent's
    own schema, `app.agents.schemas.ExternalEvidence`) it returns.
    Persisted under `SK=EXTERNAL_EVIDENCE#<evidence_id>` - a distinct key
    space from user-uploaded `SK=EVIDENCE#<evidence_id>` records (owned by
    `EvidenceRepository`), so external research is never confused with,
    and never overwrites, evidence the user actually provided. `source_url`
    and `source_name` are copied from the underlying `ResearchResult` at
    persistence time so this record stays traceable to a real source even
    if the raw research record is ever pruned.
    """

    id: UUID
    decision_id: UUID
    research_result_id: UUID
    claim: str
    source_url: str
    source_name: str
    support_level: str | None = None
    credibility: str | None = None
    related_assumption_ids: list[str] = Field(default_factory=list)
    related_blindspot_ids: list[str] = Field(default_factory=list)
    related_threshold_ids: list[str] = Field(default_factory=list)
    explanation: str | None = None
    excerpt: str | None = None
    published_at: datetime | None = None
    retrieved_at: datetime
    created_at: datetime


class AgentRunStatus(StrEnum):
    """Per-agent status within one analysis run, for future frontend display
    (e.g. "Decision Analyzer: completed", "Assumption Hunter: running").

    UNAVAILABLE is distinct from FAILED and is used only by the (optional)
    Research Agent stage: it means the external research provider itself
    could not be reached (disabled, misconfigured, or failing after
    retries) - never that the stage produced an error the way a real
    agent/model failure would. An UNAVAILABLE research stage never fails
    the surrounding analysis; the rest of the pipeline proceeds using
    whatever evidence already exists.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"


class AnalysisRun(BaseModel):
    id: UUID
    decision_id: UUID
    status: AnalysisRunStatus = AnalysisRunStatus.QUEUED
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    # Structured agent output for this run, keyed by agent id (e.g.
    # "decision_analyzer", "assumption_hunter"), each value a plain dict
    # dump of that agent's own schema. A generic dict-of-dicts rather than
    # a fixed set of typed fields so this schema doesn't need to change as
    # more agents contribute to a run later.
    result: dict[str, object] | None = None
    # Per-agent lifecycle status, keyed the same way as `result`. Lets a
    # future frontend show "Decision Analyzer: completed / Assumption
    # Hunter: running" without polling anything beyond this one record.
    agent_statuses: dict[str, AgentRunStatus] | None = None
