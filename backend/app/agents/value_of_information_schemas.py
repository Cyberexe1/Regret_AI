"""Value-of-Information data model (REGRET ENGINE 2.0, Step 20).

Answers a different question than everything upstream of it in the
pipeline. The Assumption Hunter/Blindspot Hunter find WHAT is uncertain.
The Devil's Advocate/Regret Simulator find WHY it could go wrong. The
Threshold Engine finds WHERE the tipping point is. This module answers:
"of everything still uncertain, which uncertainty is most worth spending
effort to resolve BEFORE committing?"

That is explicitly NOT the same question as "which risk is scariest" -
see `app.services.value_of_information.compute_item_scores` for the
worked distinction between HIGH RISK and HIGH PRACTICAL VALUE TO RESOLVE.

Everything here is deterministic, computed from already-persisted,
already-structured data (`Assumption`, `Blindspot`, `Threshold`,
`RegretScenario`, `Experiment`, `HistoricalContext`) - no LLM call is
involved anywhere in this feature. Every score is a documented, bounded
combination of ordinal bands, never a fabricated statistical probability
- see the module docstring in `app.services.value_of_information` for
the exact formula.

No existing concept is duplicated: `ImpactLevel`/`SeverityLevel`/
`Feasibility`/`Reversibility` from `app.agents.schemas` are reused
directly wherever their meaning already matches (as `X | None`, since
`None` is this module's own explicit "unknown" - never invented).
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.agents.schemas import Feasibility, ImpactLevel, Reversibility, SeverityLevel

# Version tag for the deterministic methodology itself - bumped only if the
# scoring formula in `app.services.value_of_information` changes in a way
# that would make two analyses computed under different versions not
# directly comparable. Lets a future step tell "recomputed under a newer
# methodology" apart from "recomputed with newer data, same methodology".
METHODOLOGY_VERSION = "voi-v1"


class DecisionSensitivity(StrEnum):
    """"If this variable changes, how much could the decision assessment
    change?" - independent of how likely the variable is to actually be
    wrong (that's `UncertaintyLevel`) and independent of how bad it would
    be if wrong (that's `potential_decision_impact`). A variable can be
    highly uncertain but low-sensitivity (the decision barely depends on
    it), or well-understood but high-sensitivity (a small remaining error
    band still swings the outcome a lot).

    UNKNOWN is the honest answer when no numeric relationship or
    documented reasoning connects the variable to the decision's economics
    - never fabricated (see spec: "do not fabricate mathematical
    relationships when inputs are missing").
    """

    NEGLIGIBLE = "negligible"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class UncertaintyLevel(StrEnum):
    """How much is genuinely unknown about this specific variable today.

    Deliberately distinct from `EvidenceStrength` in vocabulary even
    though the two are computed as inverses of each other in this
    version's methodology (see `app.services.value_of_information`) -
    kept as separate fields so a future methodology version could compute
    them independently without a schema change.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    UNKNOWN = "unknown"


class EvidenceStrength(StrEnum):
    """How much real, already-submitted evidence currently exists that
    bears on this specific uncertainty - regardless of whether that
    evidence is favorable or unfavorable. Contradicting evidence is still
    evidence: it reduces how unknown something is, even though it may be
    bad news for the decision.
    """

    NONE = "none"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    UNKNOWN = "unknown"


class CostBand(StrEnum):
    """Qualitative cost-to-test band. Never a fabricated currency figure -
    a real number is only ever carried through from an already-persisted
    `Experiment.estimated_cost`, itself only ever set by the Experiment
    Planner when it could be derived from real information (see
    `app.agents.schemas.Experiment`)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class HistoricalRelevance(StrEnum):
    """Whether the SAME user's own past decisions (Step 19) suggest this
    variable is worth extra attention - e.g. it previously caused a
    validation failure. This is a secondary, lower-priority signal - see
    `app.services.value_of_information`'s explicit "historical context
    never overrides current evidence" rule, mirroring Step 19's own
    evidence hierarchy.
    """

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ValueBand(StrEnum):
    """Final output band for `information_value`/`practical_value`.

    Deliberately five qualitative levels, never a raw float presented as
    if it were a calibrated probability or a scientific measurement - see
    `app.services.value_of_information` module docstring for the exact,
    documented formula that produces this band from bounded, normalized
    ordinal inputs.
    """

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    UNKNOWN = "unknown"


class ThresholdLinkStatus(StrEnum):
    """Whether this uncertainty already connects to a real, persisted
    `Threshold` - see spec: "If no threshold exists: do NOT invent one."
    """

    LINKED = "linked"
    NOT_ESTABLISHED = "not_established"


class ValueOfInformationItem(BaseModel):
    """One uncertainty (an `Assumption` or a `Blindspot`), scored for how
    much practical value resolving it would add before committing to the
    decision.

    `uncertainty_id` is the id of the real, already-persisted `Assumption`
    or `Blindspot` this item is about - exactly one of
    `related_assumption_ids`/`related_blindspot_ids` will contain it
    (whichever kind it is); the other stays empty for that item. This
    mirrors the project's existing "reference real ids, never invent one"
    convention used throughout `app.schemas.decision_resources`.
    """

    uncertainty_id: str = Field(
        ..., description="The real, persisted Assumption or Blindspot id this item is about."
    )
    title: str = Field(..., description="Short, human-readable label for this uncertainty.")
    description: str = Field(
        ..., description="The uncertainty itself, in the source Assumption/Blindspot's own words."
    )
    related_assumption_ids: list[str] = Field(default_factory=list)
    related_blindspot_ids: list[str] = Field(default_factory=list)
    related_threshold_ids: list[str] = Field(default_factory=list)
    related_regret_scenario_ids: list[str] = Field(default_factory=list)
    related_experiment_id: str | None = Field(
        default=None,
        description="The id of an already-recommended Experiment that targets a related "
        "threshold, if one exists - the source of estimated_test_cost/duration/feasibility/"
        "reversibility below when set. Null if no experiment has been recommended yet for "
        "this uncertainty's threshold.",
    )

    # --- Impact-related -------------------------------------------------------
    potential_decision_impact: ImpactLevel | None = Field(
        default=None,
        description="How bad it would be if this uncertainty resolved unfavorably. `None` "
        "means unknown - never guessed.",
    )
    decision_sensitivity: DecisionSensitivity = Field(
        default=DecisionSensitivity.UNKNOWN,
        description="How much the decision's overall assessment would change if this "
        "variable turned out differently than currently believed.",
    )
    regret_severity: SeverityLevel | None = Field(
        default=None,
        description="The severity of the related regret scenario, if this uncertainty links "
        "to one (via related_regret_scenario_ids). `None` if no related regret scenario exists.",
    )

    # --- Evidence-related -------------------------------------------------------
    current_evidence_strength: EvidenceStrength = Field(default=EvidenceStrength.UNKNOWN)
    uncertainty_level: UncertaintyLevel = Field(default=UncertaintyLevel.UNKNOWN)

    # --- Testing-related ---------------------------------------------------------
    estimated_test_cost: CostBand = Field(default=CostBand.UNKNOWN)
    estimated_test_duration_days: int | None = Field(
        default=None,
        description="Copied unchanged from a related Experiment's own estimated duration, if "
        "one exists. Never a fabricated number.",
    )
    feasibility: Feasibility | None = Field(default=None)
    reversibility: Reversibility | None = Field(default=None)

    # --- Historical/context-related --------------------------------------------
    historical_relevance: HistoricalRelevance = Field(default=HistoricalRelevance.NONE)
    prior_learning_count: int = Field(
        default=0, ge=0,
        description="How many of the same user's own past-decision learnings (Step 19) "
        "relate to this specific uncertainty.",
    )

    # --- Threshold linkage --------------------------------------------------------
    threshold_status: ThresholdLinkStatus = Field(default=ThresholdLinkStatus.NOT_ESTABLISHED)

    # --- Final -------------------------------------------------------------------
    information_value: ValueBand = Field(
        ..., description="How much resolving this uncertainty could change the decision, "
        "before considering cost/feasibility - see the documented formula.",
    )
    practical_value: ValueBand = Field(
        ..., description="information_value adjusted for the real cost/feasibility/"
        "reversibility of actually testing it. A high-information-value uncertainty that is "
        "very expensive to test can rank below a lower-information-value one that is cheap "
        "and fast to test - this field, not information_value, is what ranking is based on.",
    )
    priority: int = Field(
        ..., description="1-based rank within this analysis, by practical_value.", ge=1
    )
    rationale: str = Field(
        ..., description="Plain-English explanation built only from this item's own recorded "
        "fields - never free-form LLM prose, never a claim not backed by a specific field above.",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="How much of this item's score rests on real, comparable inputs rather "
        "than 'unknown' fallbacks - NEVER a probability that the uncertainty will resolve "
        "favorably or that the decision will succeed.",
    )


class ValueOfInformationAnalysis(BaseModel):
    """The full, ranked Value-of-Information analysis for one decision.

    Persisted under `SK=VOI#<analysis_id>` (see
    `app.repositories.value_of_information_repository`), append-only like
    `AnalysisRun`/`ReEvaluation` - a later recompute (e.g. after an
    experiment result changes the evidence) creates a NEW analysis, never
    overwrites this one, so a decision's full prioritization history stays
    reconstructable.
    """

    analysis_id: UUID
    decision_id: UUID
    ranked_uncertainties: list[ValueOfInformationItem] = Field(default_factory=list)
    primary_uncertainty_id: str | None = Field(
        default=None,
        description="The uncertainty_id of whichever item in ranked_uncertainties has the "
        "highest practical_value - the strongest candidate for experimentation. Null only if "
        "ranked_uncertainties is empty.",
    )
    primary_threshold_id: str | None = Field(
        default=None,
        description="The related threshold id of the primary uncertainty, if one exists - "
        "copied from that item's related_threshold_ids. Null if the primary uncertainty has "
        "no established threshold yet.",
    )
    why_this_is_primary: str | None = Field(
        default=None,
        description="Plain-English explanation for why the primary uncertainty was chosen, "
        "built only from its own recorded fields - mirrors that item's own rationale.",
    )
    summary: str = Field(
        ..., description="One or two sentences on which uncertainty is most worth resolving "
        "before committing, and why.",
    )
    methodology_version: str = Field(default=METHODOLOGY_VERSION)
    created_at: datetime
    superseded_by_analysis_id: UUID | None = Field(
        default=None,
        description="Set on an older analysis once a newer one has been computed for the same "
        "decision (see re-evaluation integration) - the older record is never deleted or "
        "overwritten, only marked superseded, so it remains part of the decision's history.",
    )
