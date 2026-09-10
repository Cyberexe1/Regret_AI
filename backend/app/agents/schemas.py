"""Structured output schemas for the agent pipeline.

Every agent's output is validated against its schema here before it's ever
persisted or returned - if a model's response doesn't conform, that's an
application-level error (see `app.agents.orchestrator`), never
silently-accepted malformed data.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class InformationClassification(StrEnum):
    """Every claim the Decision Analyzer makes must be labeled as one of these.

    This is the mechanism that keeps the analyzer honest about what it
    actually knows versus what it's guessing - see the system prompt in
    `app.agents.decision_analyzer`.
    """

    FACT = "fact"
    ASSUMPTION = "assumption"
    UNKNOWN = "unknown"


class ImportanceLevel(StrEnum):
    """Shared importance scale used by both the Decision Analyzer and the
    Assumption Hunter. CRITICAL is reserved for assumptions the decision
    cannot survive being wrong about."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


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


class AssumptionSource(StrEnum):
    """Whether the decision owner stated the assumption outright or is
    relying on it without ever saying so."""

    EXPLICIT = "explicit"
    IMPLICIT = "implicit"


class AssumptionEvidenceStatus(StrEnum):
    """How the assumption stands against evidence actually submitted for
    this decision - never against outside knowledge the model wasn't given.

    NOT_ADDRESSED covers both "evidence was submitted but says nothing
    about this" and "no evidence was submitted at all" for this decision -
    it never means "proven false"; that's CONTRADICTED. This is a distinct
    third state, deliberately not collapsed into an "unsupported" bucket,
    so the model is never nudged toward treating silence as refutation.
    """

    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    NOT_ADDRESSED = "not_addressed"


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


class AssumptionFinding(BaseModel):
    """One assumption the decision depends on, as identified by the Assumption Hunter.

    An assumption can be both EXPLICIT and CRITICAL, or IMPLICIT and
    UNSUPPORTED, etc. - `source` and `evidence_status` are independent
    axes, not a single forced classification, so both can be set without
    losing information.
    """

    statement: str = Field(
        ...,
        description="The assumption, stated plainly, e.g. 'Customers will order twice per month.'",
    )
    source: AssumptionSource = Field(
        ...,
        description="Whether stated outright (EXPLICIT) or relied on silently (IMPLICIT).",
    )
    importance: ImportanceLevel = Field(
        ..., description="How much the decision's outcome depends on this assumption holding true."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How confident the hunter is that this assumption holds, from 0.0 to 1.0.",
    )
    evidence_status: AssumptionEvidenceStatus = Field(
        ...,
        description="Whether submitted evidence supports, contradicts, or never addresses this.",
    )
    dependency: str = Field(
        ..., description="What part of the decision (goal, constraint, criterion) this underpins."
    )
    failure_consequence: str = Field(
        ..., description="What happens to the decision if this assumption turns out to be false."
    )


class AssumptionAnalysis(BaseModel):
    """Structured output of the Assumption Hunter.

    Consumes the Decision Analyzer's `DecisionAnalysis` (goal, constraints,
    success criteria, key variables) rather than re-reading the raw
    decision - see `app.agents.assumption_hunter`.
    """

    assumptions: list[AssumptionFinding] = Field(
        default_factory=list,
        description="Every assumption identified as underpinning this decision.",
    )


class BlindspotCategory(StrEnum):
    """Controlled vocabulary for what kind of gap a blindspot represents.

    Deliberately includes OTHER - the Blindspot Hunter should not be forced
    to mislabel something that genuinely doesn't fit one of the named
    categories.
    """

    MISSING_EVIDENCE = "missing_evidence"
    UNTESTED_ASSUMPTION = "untested_assumption"
    HIDDEN_DEPENDENCY = "hidden_dependency"
    CONSTRAINT = "constraint"
    STAKEHOLDER = "stakeholder"
    MARKET = "market"
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    TECHNICAL = "technical"
    TIMING = "timing"
    BEHAVIOR = "behavior"
    EDGE_CASE = "edge_case"
    SECOND_ORDER_EFFECT = "second_order_effect"
    CONTRADICTION = "contradiction"
    OTHER = "other"


class BlindspotEvidenceStatus(StrEnum):
    """How a blindspot stands against evidence actually submitted for this
    decision.

    Distinct from `AssumptionEvidenceStatus`: a blindspot is a *question*,
    not a claim, so "the evidence already answers this" (ALREADY_SUPPORTED)
    and "the evidence answers part of it" (PARTIALLY_ADDRESSED) are
    meaningful states here that don't apply to a single assumption's
    supported/contradicted/not_addressed axis.
    """

    ALREADY_SUPPORTED = "already_supported"
    PARTIALLY_ADDRESSED = "partially_addressed"
    CONTRADICTED = "contradicted"
    NOT_ADDRESSED = "not_addressed"


class BlindspotFinding(BaseModel):
    """One important question the decision-maker has not adequately
    answered, as identified by the Blindspot Hunter.

    No `id` field here, by the same convention as `AssumptionFinding`: an
    id is assigned by `DecisionRepository` only once this is persisted, so
    the agent's own structured output never has to invent one.
    `related_assumption_ids` must only ever contain ids the agent was
    actually given (persisted `Assumption` records) - the orchestrator
    drops any it doesn't recognize before persisting, see
    `app.agents.orchestrator`.
    """

    question: str = Field(
        ...,
        description=(
            "A concrete, specific question the decision doesn't yet answer, e.g. "
            "'What happens to unit economics if repeat orders fall below 20%?' - "
            "never generic filler like 'consider market conditions.'"
        ),
    )
    category: BlindspotCategory = Field(
        ..., description="What kind of gap this is. Use OTHER if nothing else genuinely fits."
    )
    importance: ImportanceLevel = Field(
        ..., description="How much this could materially change the decision if left unanswered."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How confident the hunter is that this is a real, material gap.",
    )
    evidence_status: BlindspotEvidenceStatus = Field(
        ...,
        description="Whether the evidence given already answers this, partly answers it, "
        "contradicts something related to it, or never addresses it at all.",
    )
    related_assumption_ids: list[str] = Field(
        default_factory=list,
        description="Ids of persisted assumptions this blindspot relates to, if any.",
    )
    why_it_matters: str = Field(
        ..., description="Why this question could materially change the decision if unanswered."
    )
    evidence_gap: str | None = Field(
        default=None,
        description="What evidence is missing that would resolve this, if applicable.",
    )


class BlindspotAnalysis(BaseModel):
    """Structured output of the Blindspot Hunter.

    Consumes the Decision Analyzer's `DecisionAnalysis` and the persisted
    `Assumption` records from the Assumption Hunter - never re-derives its
    own understanding of the decision from scratch. See
    `app.agents.blindspot_hunter`.
    """

    blindspots: list[BlindspotFinding] = Field(
        default_factory=list,
        description="Important questions/gaps the decision has not adequately addressed.",
    )


class EvidenceSupportLevel(StrEnum):
    """What a specific piece of evidence does to a specific claim.

    IRRELEVANT is distinct from INSUFFICIENT: irrelevant means the evidence
    has nothing to do with the claim; insufficient means it's related but
    doesn't go far enough to support or contradict it.
    """

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    INSUFFICIENT = "insufficient"
    IRRELEVANT = "irrelevant"


class EvidenceCredibility(StrEnum):
    """The Evidence Agent's own judgment of how much weight to give a
    source, based only on what's visible in the evidence record itself
    (e.g. its stated source type) - never fabricated attributes about the
    source that weren't provided."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class EvidenceFinding(BaseModel):
    """One mapping between a real piece of submitted evidence and a
    specific assumption/blindspot claim, as identified by the Evidence
    Agent.

    No `id` field, by the same convention as `AssumptionFinding` and
    `BlindspotFinding` - assigned at persistence. `evidence_id` MUST be the
    real id of an `Evidence` record the agent was actually given; the
    orchestrator drops any finding whose `evidence_id` (or whose
    `related_assumption_ids`/`related_blindspot_ids` entries) it doesn't
    recognize before persisting - see `app.agents.orchestrator`.
    """

    evidence_id: str = Field(
        ..., description="The real id of the Evidence record this finding is about."
    )
    claim: str = Field(
        ..., description="The specific assumption/blindspot claim this evidence bears on."
    )
    support_level: EvidenceSupportLevel = Field(
        ..., description="Whether this evidence supports, contradicts, is insufficient for, "
        "or is irrelevant to the claim."
    )
    credibility: EvidenceCredibility = Field(
        ..., description="How much weight to give this source, based only on what was provided."
    )
    related_assumption_ids: list[str] = Field(
        default_factory=list, description="Ids of persisted assumptions this finding bears on."
    )
    related_blindspot_ids: list[str] = Field(
        default_factory=list, description="Ids of persisted blindspots this finding bears on."
    )
    explanation: str = Field(
        ...,
        description="What the agent infers from the evidence for this claim - kept separate "
        "from the excerpt, which is what the evidence itself actually says.",
    )
    excerpt: str | None = Field(
        default=None,
        description="A short, direct quote of only the relevant portion of the evidence. "
        "Never the entire document.",
    )


class EvidenceAnalysis(BaseModel):
    """Structured output of the Evidence Agent.

    Consumes the Decision Analyzer's, Assumption Hunter's, and Blindspot
    Hunter's structured results plus already-uploaded evidence - never
    performs external research and never re-analyzes the decision from
    scratch. See `app.agents.evidence_agent`.
    """

    findings: list[EvidenceFinding] = Field(
        default_factory=list,
        description="Every mapping found between submitted evidence and assumptions/blindspots.",
    )


class SeverityLevel(StrEnum):
    """Shared low/medium/high/critical scale used by the Devil's Advocate
    (`Challenge.severity`) and the Regret Simulator (`RegretScenario.regret_level`).

    Deliberately qualitative, never a numeric score - see the module
    docstring's "no fake probabilities/scores" principle, which governs
    both agents defined from here down.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImpactLevel(StrEnum):
    """How bad the consequence of a regret scenario would be if it
    materialized. SEVERE is reserved for consequences that are hard or
    impossible to walk back from (e.g. capital already fully committed)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SEVERE = "severe"


class ProbabilityBand(StrEnum):
    """Qualitative likelihood band for a regret scenario.

    Never a numeric percentage - the Regret Simulator must not fabricate
    false precision. UNKNOWN is a first-class, expected value: when the
    supplied evidence genuinely doesn't support even a qualitative
    low/medium/high judgment, UNKNOWN is the honest answer, not a guess.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class TriggerDirection(StrEnum):
    """How a regret scenario's trigger variable would have to move to
    reach its failure condition."""

    BELOW = "below"
    ABOVE = "above"
    CHANGES = "changes"
    FAILS = "fails"
    UNKNOWN = "unknown"


class Challenge(BaseModel):
    """One concrete, evidence-grounded attack on the decision, as
    identified by the Devil's Advocate.

    No `id` field, by the same convention as `BlindspotFinding` and
    `EvidenceFinding` - assigned at persistence. Every
    `related_assumption_ids`/`related_blindspot_ids`/
    `related_evidence_finding_ids` entry must be an id the agent was
    actually given (a persisted `Assumption`/`Blindspot`/`EvidenceFinding`
    record); the orchestrator drops any it doesn't recognize before
    persisting, exactly as it already does for the Blindspot Hunter and
    Evidence Agent - see `app.agents.orchestrator`.
    """

    claim: str = Field(
        ..., description="The specific part of the decision or its reasoning being attacked."
    )
    attack: str = Field(
        ...,
        description=(
            "The concrete counter-argument itself, e.g. 'The decision depends on reaching "
            "25% repeat orders, but the supplied evidence only establishes initial demand.' "
            "Never generic filler like 'competition could be a problem.'"
        ),
    )
    severity: SeverityLevel = Field(
        ..., description="How much this challenge could change the decision if it holds."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How confident the agent is that this challenge is real, from 0.0 to 1.0 - "
        "not how likely the underlying failure is, just how well-grounded the attack itself is.",
    )
    related_assumption_ids: list[str] = Field(
        default_factory=list, description="Ids of persisted assumptions this challenge attacks."
    )
    related_blindspot_ids: list[str] = Field(
        default_factory=list,
        description="Ids of persisted blindspots this challenge relates to, if any.",
    )
    related_evidence_finding_ids: list[str] = Field(
        default_factory=list,
        description="Ids of persisted evidence findings this challenge's evidence_basis draws on.",
    )
    failure_mechanism: str = Field(
        ...,
        description="The causal chain: if the claim being attacked is wrong, what specifically "
        "breaks and why - not just that something could go wrong.",
    )
    evidence_basis: str = Field(
        ...,
        description="What in the given evidence/assumptions/blindspots actually supports this "
        "challenge. Must distinguish supported claim from inference from open uncertainty - "
        "never presented as settled fact if it is not.",
    )


class DevilAdvocateAnalysis(BaseModel):
    """Structured output of the Devil's Advocate.

    Consumes the Decision Analyzer's, Assumption Hunter's, Blindspot
    Hunter's, and Evidence Agent's structured results - never independently
    redoes the decision analysis. See `app.agents.devils_advocate`.
    """

    overall_challenge: str = Field(
        ...,
        description="One or two sentences summarizing the single strongest case that this "
        "decision could be wrong, synthesized from the individual challenges below.",
    )
    challenges: list[Challenge] = Field(
        default_factory=list,
        description="Every concrete, evidence-grounded attack identified against the decision.",
    )


class RegretScenario(BaseModel):
    """One plausible failure future for the decision, as identified by the
    Regret Simulator.

    Unlike `Challenge`/`BlindspotFinding`/`EvidenceFinding`, this DOES carry
    an `id` - but it is a label scoped only to one `RegretSimulation`
    response, not a persistence-assigned id. It exists purely so
    `RegretSimulation.highest_risk_scenario_id` can point at one of its own
    sibling scenarios before any of them have been written to DynamoDB (the
    repository layer assigns each scenario its own real, separate id once
    persisted - see `DecisionRepository.create_regret_scenarios`).
    `related_challenge_ids` DOES reference real, already-persisted
    `Challenge` ids, since challenges are persisted before this agent runs.
    """

    id: str = Field(
        ...,
        description="A label unique within this response only, e.g. 'scenario-1' - used solely "
        "so highest_risk_scenario_id can reference a sibling scenario in the same response.",
    )
    title: str = Field(..., description="Short name for the failure future, e.g. 'Demand failure'.")
    failure_condition: str = Field(
        ..., description="The specific condition that would have to hold for this to be a regret."
    )
    probability_band: ProbabilityBand = Field(
        ...,
        description="Qualitative likelihood only - never a fabricated numeric probability.",
    )
    impact: ImpactLevel = Field(
        ..., description="How bad the consequence would be if this scenario materialized."
    )
    regret_level: SeverityLevel = Field(
        ...,
        description="How much this scenario, if it happened, would make committing now look "
        "like the wrong choice in hindsight - considered together with impact and "
        "irreversibility, not probability alone.",
    )
    trigger_variable: str = Field(
        ..., description="The specific, concrete variable whose movement would trigger this."
    )
    trigger_direction: TriggerDirection = Field(
        ..., description="How the trigger variable would have to move to reach failure."
    )
    provisional_threshold: str | None = Field(
        default=None,
        description="A tentative tipping point ONLY if it can be derived from the supplied "
        "information, e.g. 'below approximately 20% repeat orders.' Never an invented number - "
        "leave unset (or state the condition qualitatively) if no number can be derived. The "
        "dedicated Threshold Engine (not implemented yet) will later formalize this.",
    )
    consequence: str = Field(
        ...,
        description="What actually happens to the decision-maker if this scenario occurs - "
        "framed as regret (a choice that looks wrong in hindsight), not just as a risk.",
    )
    related_assumption_ids: list[str] = Field(
        default_factory=list, description="Ids of persisted assumptions this scenario depends on."
    )
    related_challenge_ids: list[str] = Field(
        default_factory=list,
        description="Ids of persisted Devil's Advocate challenges this scenario builds on.",
    )
    evidence_basis: str = Field(
        ...,
        description="What in the given evidence/assumptions/challenges actually supports this "
        "scenario - distinguishing known evidence from inference and open uncertainty.",
    )


class RegretSimulation(BaseModel):
    """Structured output of the Regret Simulator.

    Consumes the Decision Analyzer's, Assumption Hunter's, Blindspot
    Hunter's, Evidence Agent's, and Devil's Advocate's structured results -
    never independently redoes the decision analysis. See
    `app.agents.regret_simulator`.
    """

    scenarios: list[RegretScenario] = Field(
        default_factory=list,
        description="Plausible failure futures that could materially change the decision.",
    )
    dominant_regret: str = Field(
        ...,
        description="One or two sentences on the single most important regret this decision "
        "risks, synthesized across the scenarios below.",
    )
    highest_risk_scenario_id: str | None = Field(
        default=None,
        description="The `id` of whichever entry in `scenarios` represents the highest-priority "
        "regret (by likelihood, impact, and irreversibility together, not a computed score). "
        "Null only if no single scenario clearly dominates.",
    )


class ThresholdType(StrEnum):
    """What kind of tipping point a threshold represents.

    The Threshold Engine must not force every threshold into a number -
    QUALITATIVE, BINARY, and TIME_BASED are first-class, equally valid
    outcomes when a numeric value can't be honestly derived. UNKNOWN
    covers the case where even the type itself can't be established from
    what was given.
    """

    NUMERIC = "numeric"
    RANGE = "range"
    QUALITATIVE = "qualitative"
    BINARY = "binary"
    TIME_BASED = "time_based"
    UNKNOWN = "unknown"


class ThresholdDirection(StrEnum):
    """Which way the trigger variable has to move to cross the threshold."""

    ABOVE = "above"
    BELOW = "below"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    OUTSIDE_RANGE = "outside_range"
    INSIDE_RANGE = "inside_range"
    FAILS = "fails"
    UNKNOWN = "unknown"


class ThresholdDerivation(StrEnum):
    """Where a threshold's value actually came from - the mechanism that
    keeps the engine honest about precision it does or doesn't have.

    Priority order when multiple sources are available (strongest first):
    an explicit user-provided constraint (DERIVED_FROM_USER_INPUT), a
    deterministic calculation from supplied numbers
    (CALCULATED_FROM_EVIDENCE), a provisional threshold already surfaced by
    the Regret Simulator and validated here (DERIVED_FROM_EXISTING_ANALYSIS),
    a qualitative condition when no reliable number can be derived
    (QUALITATIVE), and UNKNOWN only when even a qualitative condition
    cannot be honestly established.
    """

    DERIVED_FROM_USER_INPUT = "derived_from_user_input"
    CALCULATED_FROM_EVIDENCE = "calculated_from_evidence"
    DERIVED_FROM_EXISTING_ANALYSIS = "derived_from_existing_analysis"
    QUALITATIVE = "qualitative"
    UNKNOWN = "unknown"


class ThresholdValidationStatus(StrEnum):
    """How much to trust a threshold's value.

    VALIDATED: directly supported by an explicit user constraint or a
    deterministic calculation from reliable supplied numbers.
    PROVISIONAL: a useful inferred tipping point that still needs
    real-world validation (e.g. via an experiment).
    UNKNOWN: insufficient evidence exists to establish a meaningful
    threshold at all - this is the honest answer, not a placeholder for a
    failure to try.
    """

    VALIDATED = "validated"
    PROVISIONAL = "provisional"
    UNKNOWN = "unknown"


class Threshold(BaseModel):
    """One tipping point at which the decision stops being attractive,
    viable, or safe, as identified by the Threshold Engine.

    Unlike most other agent schemas in this pipeline, this DOES carry an
    `id` - exactly like `RegretScenario` - but it is a label scoped only to
    one `ThresholdAnalysis` response, not a persistence-assigned id. It
    exists purely so `ThresholdAnalysis.primary_threshold_id` can point at
    one of its own sibling thresholds before any of them have been written
    to DynamoDB (the repository layer assigns each threshold its own real,
    separate id once persisted - see `DecisionRepository.create_thresholds`).
    `related_regret_scenario_ids`/`related_assumption_ids` DO reference
    real, already-persisted ids, since regret scenarios and assumptions
    are persisted before this agent runs.

    `confidence` is confidence THAT THIS THRESHOLD IS MEANINGFUL (i.e. that
    crossing it actually matters), never a probability that the underlying
    failure will occur - the two must not be conflated. See the system
    prompt in `app.agents.threshold_engine` for the same distinction spelled
    out for the model.
    """

    id: str = Field(
        ...,
        description="A label unique within this response only, e.g. 'threshold-1' - used "
        "solely so primary_threshold_id can reference a sibling threshold in the same response.",
    )
    variable: str = Field(
        ..., description="The specific variable that could cross a tipping point, e.g. "
        "'repeat-order rate' or 'monthly operating cost.'"
    )
    threshold_type: ThresholdType = Field(
        ..., description="NUMERIC, RANGE, QUALITATIVE, BINARY, or TIME_BASED - never force a "
        "number where one can't be honestly derived."
    )
    direction: ThresholdDirection = Field(
        ..., description="Which way the variable has to move to cross the tipping point."
    )
    threshold_value: str | None = Field(
        default=None,
        description="The tipping point itself, as a short string (e.g. '24%', '₹1.8 lakh', "
        "'two enterprise customers'). Null when threshold_type is QUALITATIVE/BINARY/UNKNOWN "
        "or when no defensible value could be derived - never a number invented to look precise.",
    )
    lower_bound: float | None = Field(
        default=None, description="Lower bound of a safe RANGE, if threshold_type is RANGE."
    )
    upper_bound: float | None = Field(
        default=None, description="Upper bound of a safe RANGE, if threshold_type is RANGE."
    )
    unit: str | None = Field(
        default=None, description="Unit for threshold_value/bounds, e.g. '%', 'INR', 'days'."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence that this threshold is MEANINGFUL (well-derived and relevant) - "
        "NOT the probability that the decision will actually cross it. Never conflate the two.",
    )
    derivation: ThresholdDerivation = Field(
        ..., description="Where this threshold's value actually came from - see the enum's "
        "priority order. Determines how much precision is honestly justified."
    )
    consequence: str = Field(
        ..., description="What happens to the decision if this threshold is crossed."
    )
    related_regret_scenario_ids: list[str] = Field(
        default_factory=list,
        description="Ids of persisted regret scenarios this threshold formalizes/relates to.",
    )
    related_assumption_ids: list[str] = Field(
        default_factory=list, description="Ids of persisted assumptions this threshold depends on."
    )
    evidence_basis: str = Field(
        ...,
        description="What in the given evidence/assumptions/scenarios actually supports this "
        "threshold - distinguishing known evidence from inference and open uncertainty.",
    )
    validation_status: ThresholdValidationStatus = Field(
        ..., description="VALIDATED, PROVISIONAL, or UNKNOWN - never presented as more certain "
        "than the derivation actually supports."
    )
    calculation_formula: str | None = Field(
        default=None,
        description="If derivation is CALCULATED_FROM_EVIDENCE, the name of a known formula "
        "(e.g. 'break_even_customers') this value was computed with - never free-form arithmetic "
        "text. Must be a formula name `app.agents.threshold_calculations` actually recognizes; "
        "the engine independently recomputes and verifies the result deterministically in Python "
        "rather than trusting the model's own arithmetic - see `app.agents.threshold_engine`.",
    )
    calculation_inputs: dict[str, float] | None = Field(
        default=None,
        description="The named numeric inputs (e.g. {'fixed_cost': 100000, "
        "'contribution_per_customer': 5000}) the calculation_formula was computed from - taken "
        "only from figures actually present in the decision/evidence, never invented.",
    )
    calculation_provenance: str | None = Field(
        default=None,
        description="A concise, human-readable explanation of how a calculated value was "
        "derived, e.g. 'Derived from monthly fixed cost and contribution per customer supplied "
        "by the user.' Never a chain-of-thought transcript - one sentence of provenance only.",
    )


class ThresholdAnalysis(BaseModel):
    """Structured output of the Threshold Engine.

    Consumes the Decision Analyzer's, Assumption Hunter's, Blindspot
    Hunter's, Evidence Agent's, Devil's Advocate's, and Regret Simulator's
    structured results - never independently redoes the decision analysis.
    See `app.agents.threshold_engine`.
    """

    thresholds: list[Threshold] = Field(
        default_factory=list,
        description="Every tipping point identified at which the decision stops being "
        "attractive, viable, or safe.",
    )
    primary_threshold_id: str | None = Field(
        default=None,
        description="The `id` of whichever entry in `thresholds` matters most to this decision "
        "(by impact, irreversibility, dependency, evidence quality, and decision sensitivity "
        "together - not a computed score). Null only if no single threshold clearly dominates.",
    )
    summary: str = Field(
        ...,
        description="One or two sentences on the single most important condition under which "
        "this decision stops being attractive, viable, or safe.",
    )


class ExperimentType(StrEnum):
    """The simplest kind of real-world test capable of resolving a given
    uncertainty. The Experiment Planner must pick the smallest one that
    could actually work - never default to building the full product when
    a cheaper test would do."""

    PILOT = "pilot"
    PROTOTYPE = "prototype"
    SURVEY = "survey"
    INTERVIEW = "interview"
    PREORDER = "preorder"
    LANDING_PAGE = "landing_page"
    MANUAL_PROCESS = "manual_process"
    SIMULATION = "simulation"
    BENCHMARK = "benchmark"
    A_B_TEST = "a_b_test"
    FINANCIAL_MODEL = "financial_model"
    OTHER = "other"


class InformationGain(StrEnum):
    """Qualitative estimate of how much an experiment would reduce the
    critical uncertainty it targets. Deliberately not a numeric score -
    see the module-level "no fake probabilities/scores" principle."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Feasibility(StrEnum):
    """How practical an experiment actually is to run given real-world
    constraints (time, access, skill, tooling) - independent of how
    valuable its information would be."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Reversibility(StrEnum):
    """How easily the commitment an experiment requires can be undone.
    HIGH reversibility (e.g. a landing page) is strongly preferred over
    LOW reversibility (e.g. signing a lease) whenever both could test the
    same uncertainty."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ExperimentPlanStatus(StrEnum):
    """Lifecycle state of one recommended experiment.

    The Experiment Planner always creates experiments as RECOMMENDED -
    later API endpoints (not agent logic) move an experiment through
    PLANNED/ACTIVE/COMPLETED/CANCELLED as the user actually acts on it.
    """

    RECOMMENDED = "recommended"
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Experiment(BaseModel):
    """One concrete, low-commitment real-world test that could meaningfully
    reduce uncertainty around a specific threshold, as identified by the
    Experiment Planner.

    Unlike most other agent schemas in this pipeline, this DOES carry an
    `id` - exactly like `RegretScenario`/`Threshold` - but it is a label
    scoped only to one `ExperimentPlan` response, not a persistence-
    assigned id. It exists purely so `ExperimentPlan.recommended_experiment_id`
    can point at one of its own sibling experiments before any of them have
    been written to DynamoDB (the repository layer assigns each experiment
    its own real, separate id once persisted - see
    `DecisionRepository.create_experiments`). `target_threshold_id` and
    `related_assumption_ids`/`related_regret_scenario_ids` DO reference
    real, already-persisted ids, since thresholds/assumptions/regret
    scenarios are persisted before this agent runs.
    """

    id: str = Field(
        ...,
        description="A label unique within this response only, e.g. 'experiment-1' - used "
        "solely so recommended_experiment_id can reference a sibling experiment in the same "
        "response.",
    )
    title: str = Field(
        ..., description="Short, concrete name, e.g. '14-day limited delivery pilot' - never "
        "generic advice like 'talk to customers.'"
    )
    objective: str = Field(
        ..., description="What this experiment is meant to find out, in one sentence."
    )
    hypothesis: str = Field(
        ..., description="The specific, falsifiable belief being tested, e.g. 'Customers who "
        "make an initial purchase will reorder at a rate sufficient to support the economic "
        "model.'"
    )
    target_threshold_id: str = Field(
        ...,
        description="The id of the persisted Threshold this experiment is designed to validate. "
        "Every recommended experiment should target a real threshold - never float disconnected "
        "from the threshold analysis.",
    )
    variable_to_test: str = Field(
        ..., description="The specific variable this experiment will measure, matching the "
        "target threshold's variable, e.g. 'repeat-order rate.'"
    )
    experiment_type: ExperimentType = Field(
        ..., description="The simplest kind of test capable of resolving this uncertainty."
    )
    steps: list[str] = Field(
        default_factory=list,
        description="Concrete, ordered steps to run the experiment - what to actually do, not "
        "vague guidance.",
    )
    success_criteria: list[str] = Field(
        default_factory=list,
        description="Observable conditions that count as success, e.g. 'At least 20 of the "
        "first 80 customers place a second order within the test period.' Never vague statements "
        "like 'customers like the product.' If no numeric target can be justified, state the "
        "condition relative to the target threshold instead of inventing a number.",
    )
    failure_criteria: list[str] = Field(
        default_factory=list,
        description="Observable conditions that indicate the assumption is not sufficiently "
        "validated - framed as a trigger for re-evaluation, never as an automatic 'the decision "
        "is bad.'",
    )
    duration_days: int | None = Field(
        default=None,
        description="Recommended timebox in days, based on the expected observation cycle, "
        "customer behavior cycle, decision urgency, and experiment complexity. Null (with the "
        "reasoning captured in `objective`/`steps`) if no meaningful duration can be justified - "
        "never an arbitrary invented number.",
    )
    estimated_cost: float | None = Field(
        default=None,
        description="Estimated cost, ONLY if it can be derived from information actually given. "
        "Null otherwise - never a plausible-sounding invented figure.",
    )
    currency: str | None = Field(
        default=None, description="Currency for estimated_cost, e.g. 'INR', if set."
    )
    evidence_to_collect: list[str] = Field(
        default_factory=list,
        description="What concrete evidence this experiment will generate, e.g. 'repeat orders', "
        "'time to reorder', 'acquisition cost' - specific enough to be uploadable back into "
        "REGRET ENGINE as real evidence later.",
    )
    decision_rule: str = Field(
        ...,
        description="What happens next depending on the outcome, e.g. 'If the threshold is met, "
        "reassess the full investment. If missed, do not commit yet. If inconclusive, extend or "
        "redesign the experiment.' Must trigger re-evaluation, never an unconditional final "
        "decision.",
    )
    expected_information_gain: InformationGain = Field(
        ..., description="How much this experiment would reduce the critical uncertainty it "
        "targets - qualitative only."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence that this experiment is well-designed and actually targets the "
        "critical uncertainty - NOT a probability that the experiment will succeed.",
    )
    feasibility: Feasibility = Field(
        ..., description="How practical this experiment is to actually run."
    )
    reversibility: Reversibility = Field(
        ..., description="How easily the commitment this experiment requires can be undone. "
        "Prefer HIGH reversibility experiments over committing to something irreversible."
    )
    related_assumption_ids: list[str] = Field(
        default_factory=list, description="Ids of persisted assumptions this experiment tests."
    )
    related_regret_scenario_ids: list[str] = Field(
        default_factory=list,
        description="Ids of persisted regret scenarios this experiment could help avoid.",
    )
    status: ExperimentPlanStatus = Field(
        default=ExperimentPlanStatus.RECOMMENDED,
        description="Always RECOMMENDED when the Experiment Planner creates this - later "
        "lifecycle transitions happen through API endpoints, not agent logic.",
    )


class ExperimentPlan(BaseModel):
    """Structured output of the Experiment Planner.

    Consumes the Decision Analyzer's, Assumption Hunter's, Blindspot
    Hunter's, Evidence Agent's, Devil's Advocate's, Regret Simulator's, and
    Threshold Engine's structured results - never independently redoes the
    decision analysis and never recommends the final decision, only
    validation. See `app.agents.experiment_planner`.
    """

    experiments: list[Experiment] = Field(
        default_factory=list,
        description="Every concrete, low-commitment experiment identified that could "
        "meaningfully reduce uncertainty around a critical threshold.",
    )
    recommended_experiment_id: str | None = Field(
        default=None,
        description="The `id` of whichever entry in `experiments` represents the best "
        "combination of high information value and low commitment - not necessarily the "
        "cheapest. Null only if no single experiment clearly stands out.",
    )
    summary: str = Field(
        ...,
        description="One or two sentences on the cheapest credible real-world test available "
        "before making the full commitment.",
    )


class ExternalEvidenceSupportLevel(StrEnum):
    """What one external source does to a specific claim.

    CONTEXTUAL is distinct from the Evidence Agent's own vocabulary
    (supports/contradicts/insufficient/irrelevant) - external, generic
    industry/market information very often provides useful context without
    actually validating or refuting a decision-specific claim (e.g.
    "industry repeat-purchase rates vary widely by category" neither
    supports nor contradicts THIS business's specific 24% threshold). See
    the module-level "do not turn generic industry data into proof of a
    specific business outcome" principle.
    """

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    CONTEXTUAL = "contextual"
    INSUFFICIENT = "insufficient"


class ExternalEvidence(BaseModel):
    """One mapping between a real external research result and a specific
    assumption/blindspot/threshold claim, as identified by the Research
    Agent.

    No `id` field, by the same convention as `EvidenceFinding` - assigned
    at persistence. `research_result_id` MUST be the real id of a
    `ResearchResult` the agent was actually given (from an actual search
    response) - the orchestrator drops any finding whose
    `research_result_id` (or whose `related_assumption_ids`/
    `related_blindspot_ids`/`related_threshold_ids` entries) it doesn't
    recognize before persisting, exactly like the Evidence Agent's own
    fabrication guard.
    """

    research_result_id: str = Field(
        ..., description="The real id of the ResearchResult this finding is about."
    )
    claim: str = Field(
        ..., description="The specific assumption/blindspot/threshold claim this source bears on."
    )
    support_level: ExternalEvidenceSupportLevel = Field(
        ...,
        description="Whether this source supports, contradicts, merely provides context for, "
        "or is insufficient to say anything about the claim. Never assume generic industry "
        "data proves a decision-specific outcome - prefer CONTEXTUAL over SUPPORTS/CONTRADICTS "
        "unless the source genuinely speaks to this specific decision's claim.",
    )
    credibility: EvidenceCredibility = Field(
        ..., description="How much weight to give this source, based only on what was provided."
    )
    related_assumption_ids: list[str] = Field(
        default_factory=list, description="Ids of persisted assumptions this finding bears on."
    )
    related_blindspot_ids: list[str] = Field(
        default_factory=list, description="Ids of persisted blindspots this finding bears on."
    )
    related_threshold_ids: list[str] = Field(
        default_factory=list, description="Ids of persisted thresholds this finding bears on."
    )
    explanation: str = Field(
        ...,
        description="What the agent infers from the source for this claim - kept separate from "
        "the excerpt, which is what the source itself actually says. Must distinguish 'what the "
        "source says' from 'what we infer' and must never claim the source addresses something "
        "it does not actually mention.",
    )
    excerpt: str | None = Field(
        default=None,
        description="A short, direct quote of only the relevant portion of the source's snippet. "
        "Never longer than the snippet actually retrieved, and never a full page dump.",
    )


class ResearchAnalysis(BaseModel):
    """Structured output of the Research Agent.

    Consumes the Decision Analyzer's, Assumption Hunter's, Blindspot
    Hunter's, Threshold Engine's, and Regret Simulator's structured
    results to decide WHAT to research, then maps real search results
    (never fabricated) onto the claims that motivated the search. See
    `app.agents.research_agent`.
    """

    queries: list[str] = Field(
        default_factory=list,
        description="The targeted queries actually issued, each aimed at a specific critical "
        "uncertainty - never a broad, generic query like 'cloud kitchen market.'",
    )
    findings: list[ExternalEvidence] = Field(
        default_factory=list,
        description="Every mapping found between real external search results and "
        "assumptions/blindspots/thresholds.",
    )
    unresolved_questions: list[str] = Field(
        default_factory=list,
        description="Critical uncertainties that research could not resolve, either because "
        "no relevant source was found or because research was skipped/unavailable.",
    )
    summary: str = Field(
        ...,
        description="One or two sentences on what external research did or did not add to "
        "this decision's understanding.",
    )
