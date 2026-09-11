"""Value-of-Information scoring (REGRET ENGINE 2.0, Step 20).

Answers: "of everything still uncertain about this decision, which
uncertainty is most worth spending effort to resolve BEFORE committing?"

This is deliberately NOT "which risk is scariest." A regret scenario can
be severe and yet already well-understood (little left to learn); a mild
uncertainty can be cheap to resolve and swing the decision a lot. This
module scores PRACTICAL VALUE TO RESOLVE, not raw risk - see
`compute_item` below for the worked distinction, and
`backend/tests/test_value_of_information.py` for the regression tests
that pin it down (`test_high_risk_low_uncertainty_scores_low`,
`test_low_cost_high_impact_outranks_high_cost_high_impact`).

No LLM call happens anywhere in this module - every input is already a
structured field on an existing, already-persisted entity (`Assumption`,
`Blindspot`, `Threshold`, `RegretScenario`, `Experiment`) or on Step 19's
`HistoricalContext`. This mirrors the project's existing "deterministic
Python over LLM for factual/numeric derivation" principle, applied here
to prioritization instead of threshold arithmetic.

===============================================================================
THE SCORING METHODOLOGY (methodology_version = "voi-v1"), stated in full
===============================================================================

For one uncertainty (an Assumption or a Blindspot):

1. Three "information" components are each mapped from a real, existing
   ordinal field onto a normalized value in (0, 1] - never 0.0 exactly,
   so one weak factor meaningfully lowers the result without silently
   erasing the other two entirely (see `_normalize_band`):

   - potential_decision_impact (ImpactLevel: low/medium/high/severe)
   - decision_sensitivity (DecisionSensitivity: negligible..critical)
   - uncertainty_level (UncertaintyLevel: low..very_high)

   `information_value_raw = impact_norm * sensitivity_norm * uncertainty_norm`

   This is intentionally a PRODUCT, not an average: it means information
   value can only be genuinely high when the decision is both sensitive
   to this variable AND meaningfully uncertain about it AND the downside
   if wrong is material. A well-understood variable (low uncertainty)
   caps the product low even if its potential impact is severe - this is
   exactly the "high risk does not automatically mean high value to
   resolve" distinction the spec requires.

   If ANY of the three inputs is unavailable (`None`/`UNKNOWN`),
   `information_value` is `UNKNOWN` - never invented from the other two.

2. `information_value_raw` (bounded in this scheme to roughly
   [0.0156, 1.0]) is bucketed into a `ValueBand` via fixed, documented
   cutoffs (`_INFORMATION_VALUE_BANDS`). These cutoffs are an explicit,
   interpretable heuristic - NOT a statistically calibrated probability
   distribution, and the docstring on `ValueBand` says so.

3. `practical_value` adjusts `information_value_raw` for the real cost of
   actually resolving the uncertainty - cost, feasibility, and
   reversibility each contribute a multiplier in (0, 1], sourced only
   from an already-recommended `Experiment` that targets a related
   threshold (never fabricated for an uncertainty with no experiment):

   `practical_value_raw = information_value_raw * cost_multiplier * feasibility_multiplier
   * reversibility_multiplier`

   A cheap, feasible, reversible test barely discounts the information
   value; an expensive, hard, irreversible one discounts it heavily. This
   is what lets a low-cost, high-impact test outrank a high-cost,
   high-impact one even when both have identical `information_value`.

   `practical_value` is bucketed with the SAME cutoffs as step 2 - and is
   `UNKNOWN` whenever `information_value` is `UNKNOWN`.

4. Ranking (`priority`) sorts by `practical_value_raw` descending, tying
   on `information_value_raw` descending, then on `uncertainty_id` for a
   fully deterministic order. `UNKNOWN`-valued items always sort last.

5. Historical relevance (Step 19) is deliberately NOT a multiplier in
   this formula - see `_historical_relevance`. It is surfaced as its own
   field and used ONLY as a final, last-resort tiebreaker between two
   items whose `practical_value_raw` are within `_TIE_EPSILON` of each
   other. Current evidence and the deterministic formula above always
   take priority over history - mirroring Step 19's own evidence
   hierarchy.

`confidence` on each item is the fraction of the six inputs that
scoring formula actually consulted with a REAL (non-unknown/non-null)
value - never a probability that the uncertainty will resolve favorably.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.agents.schemas import (
    ExperimentType,
    Feasibility,
    ImpactLevel,
    Reversibility,
    SeverityLevel,
)
from app.agents.value_of_information_schemas import (
    CostBand,
    DecisionSensitivity,
    EvidenceStrength,
    HistoricalRelevance,
    ThresholdLinkStatus,
    UncertaintyLevel,
    ValueBand,
    ValueOfInformationAnalysis,
    ValueOfInformationItem,
)
from app.memory.similarity_schemas import HistoricalContext
from app.schemas.decision import DecisionResponse
from app.schemas.decision_resources import (
    Assumption,
    Blindspot,
    Experiment,
    RegretScenario,
    Threshold,
)

# A tiny floor instead of a literal 0.0 for any single missing/weak
# ordinal component - see module docstring step 1. Chosen small enough
# that a genuinely negligible factor still dominates the product, but
# never exactly annihilates the other two factors' information content.
_FLOOR = 0.05

_IMPACT_ORDER = [ImpactLevel.LOW, ImpactLevel.MEDIUM, ImpactLevel.HIGH, ImpactLevel.SEVERE]
_SENSITIVITY_ORDER = [
    DecisionSensitivity.NEGLIGIBLE,
    DecisionSensitivity.LOW,
    DecisionSensitivity.MODERATE,
    DecisionSensitivity.HIGH,
    DecisionSensitivity.CRITICAL,
]
_UNCERTAINTY_ORDER = [
    UncertaintyLevel.LOW,
    UncertaintyLevel.MEDIUM,
    UncertaintyLevel.HIGH,
    UncertaintyLevel.VERY_HIGH,
]
_SEVERITY_ORDER = [
    SeverityLevel.LOW, SeverityLevel.MEDIUM, SeverityLevel.HIGH, SeverityLevel.CRITICAL
]

# Fixed, documented cutoffs mapping a raw product in (0, 1] to a
# ValueBand - an explicit, interpretable heuristic bucketing, never a
# statistically calibrated probability. Ordered low to high; the first
# cutoff a raw value is `<=` determines its band.
_INFORMATION_VALUE_BANDS: list[tuple[float, ValueBand]] = [
    (0.08, ValueBand.VERY_LOW),
    (0.20, ValueBand.LOW),
    (0.40, ValueBand.MEDIUM),
    (0.65, ValueBand.HIGH),
    (1.01, ValueBand.VERY_HIGH),  # anything up to and including 1.0
]

# Multipliers applied to information_value_raw to produce
# practical_value_raw - see module docstring step 3. Each is in (0, 1];
# UNKNOWN/missing inputs get a mild, documented neutral-ish penalty
# (never 1.0 - an untested cost/feasibility/reversibility is itself a
# reason for slightly lower confidence in acting on this uncertainty
# right now) and never the harsh LOW penalty (missing data should not be
# treated as if it were confirmed to be expensive/infeasible/irreversible).
_COST_MULTIPLIER: dict[CostBand, float] = {
    CostBand.LOW: 1.0,
    CostBand.MEDIUM: 0.75,
    CostBand.HIGH: 0.45,
    CostBand.UNKNOWN: 0.8,
}
_FEASIBILITY_MULTIPLIER: dict[Feasibility | None, float] = {
    Feasibility.HIGH: 1.0,
    Feasibility.MEDIUM: 0.8,
    Feasibility.LOW: 0.5,
    None: 0.85,
}
_REVERSIBILITY_MULTIPLIER: dict[Reversibility | None, float] = {
    Reversibility.HIGH: 1.0,
    Reversibility.MEDIUM: 0.8,
    Reversibility.LOW: 0.55,
    None: 0.85,
}

# Simple, documented heuristic: the typical relative cost/effort tier of
# each experiment type, used only when a targeting Experiment exists but
# has no real estimated_cost to compare against the decision's own
# budget (see `_cost_band`). Not a fabricated currency figure - a
# qualitative tier grounded in what each experiment type generally
# requires to execute.
_EXPERIMENT_TYPE_COST_BAND: dict[ExperimentType, CostBand] = {
    ExperimentType.SURVEY: CostBand.LOW,
    ExperimentType.INTERVIEW: CostBand.LOW,
    ExperimentType.LANDING_PAGE: CostBand.LOW,
    ExperimentType.MANUAL_PROCESS: CostBand.LOW,
    ExperimentType.BENCHMARK: CostBand.LOW,
    ExperimentType.PREORDER: CostBand.MEDIUM,
    ExperimentType.A_B_TEST: CostBand.MEDIUM,
    ExperimentType.PROTOTYPE: CostBand.MEDIUM,
    ExperimentType.SIMULATION: CostBand.MEDIUM,
    ExperimentType.FINANCIAL_MODEL: CostBand.MEDIUM,
    ExperimentType.PILOT: CostBand.HIGH,
    ExperimentType.OTHER: CostBand.UNKNOWN,
}

# Ratio of estimated_cost to the decision's own stated budget, below
# which a real, currency-consistent cost is considered LOW/MEDIUM/HIGH -
# see `_cost_band`. Documented heuristic, not a statistical model.
_COST_RATIO_LOW_MAX = 0.05
_COST_RATIO_MEDIUM_MAX = 0.20

# How close two items' practical_value_raw must be for historical
# relevance to be allowed to break the tie between them - see module
# docstring step 5. Deliberately small: history must never flip a
# meaningfully different score, only decide between near-identical ones.
_TIE_EPSILON = 0.01

_HISTORICAL_RELEVANCE_ORDER = [
    HistoricalRelevance.NONE,
    HistoricalRelevance.LOW,
    HistoricalRelevance.MEDIUM,
    HistoricalRelevance.HIGH,
]

_VALUE_BAND_ORDER = [
    ValueBand.VERY_LOW,
    ValueBand.LOW,
    ValueBand.MEDIUM,
    ValueBand.HIGH,
    ValueBand.VERY_HIGH,
]


def _normalize_band(value, order: list) -> float | None:
    """Map a known ordinal enum value to a normalized float in (FLOOR, 1.0].

    Returns `None` if `value` isn't in `order` (covers both `None` and an
    explicit UNKNOWN member) - callers treat `None` as "this component
    cannot be scored," never substituting a default.
    """
    if value not in order:
        return None
    index = order.index(value)
    return _FLOOR + (1.0 - _FLOOR) * (index + 1) / len(order)


def _band_from_raw(raw: float) -> ValueBand:
    for cutoff, band in _INFORMATION_VALUE_BANDS:
        if raw <= cutoff:
            return band
    return ValueBand.VERY_HIGH  # unreachable given the final 1.01 cutoff, kept as a safe fallback


def _uncertainty_level(assumption_or_blindspot) -> UncertaintyLevel:
    """Deterministically derive how uncertain this specific variable is
    today, from the item's own `confidence` float when present (a
    0.0-1.0 float already means "how confident are we this holds" - its
    inverse IS uncertainty), falling back to `evidence_status` only when
    no numeric confidence was recorded. Never fabricated from anything
    else.
    """
    confidence = getattr(assumption_or_blindspot, "confidence", None)
    if confidence is not None:
        if confidence < 0.25:
            return UncertaintyLevel.VERY_HIGH
        if confidence < 0.5:
            return UncertaintyLevel.HIGH
        if confidence < 0.75:
            return UncertaintyLevel.MEDIUM
        return UncertaintyLevel.LOW

    status = getattr(assumption_or_blindspot, "evidence_status", None)
    status_value = getattr(status, "value", status)
    if status_value in {"already_supported", "supported"}:
        return UncertaintyLevel.LOW
    if status_value == "contradicted":
        return UncertaintyLevel.MEDIUM
    if status_value == "partially_addressed":
        return UncertaintyLevel.HIGH
    if status_value == "not_addressed":
        return UncertaintyLevel.VERY_HIGH
    return UncertaintyLevel.UNKNOWN


def _evidence_strength(assumption_or_blindspot) -> EvidenceStrength:
    """How much real, already-submitted evidence bears on this variable,
    from `evidence_status` alone - independent of `confidence`, and
    independent of whether that evidence is favorable. See
    `EvidenceStrength`'s own docstring: contradicting evidence still
    counts as evidence.
    """
    status = getattr(assumption_or_blindspot, "evidence_status", None)
    status_value = getattr(status, "value", status)
    if status_value in {"supported", "already_supported", "contradicted"}:
        return EvidenceStrength.STRONG
    if status_value == "partially_addressed":
        return EvidenceStrength.MODERATE
    if status_value == "not_addressed":
        return EvidenceStrength.NONE
    return EvidenceStrength.UNKNOWN


def _importance_to_impact(importance: str | None) -> ImpactLevel | None:
    value = (importance or "").strip().lower()
    if value == "critical":
        return ImpactLevel.SEVERE
    if value == "high":
        return ImpactLevel.HIGH
    if value in {"medium", "moderate"}:
        return ImpactLevel.MEDIUM
    if value == "low":
        return ImpactLevel.LOW
    return None


@dataclass(frozen=True)
class _LinkedEntities:
    """Real, already-persisted entities related to one uncertainty -
    found only by following actual `related_*_ids` cross-references
    already recorded by upstream agents, never guessed by text matching."""

    threshold: Threshold | None
    regret_scenario: RegretScenario | None
    experiment: Experiment | None


def _find_linked_entities(
    uncertainty_id: str,
    thresholds: list[Threshold],
    regret_scenarios: list[RegretScenario],
    experiments: list[Experiment],
) -> _LinkedEntities:
    threshold = next(
        (t for t in thresholds if uncertainty_id in t.related_assumption_ids), None
    )
    regret_scenario = next(
        (r for r in regret_scenarios if uncertainty_id in r.related_assumption_ids), None
    )
    if threshold is None and regret_scenario is not None:
        # A regret scenario may itself be the thing a threshold formalizes -
        # follow that real, already-recorded link too.
        threshold = next(
            (
                t
                for t in thresholds
                if str(regret_scenario.id) in t.related_regret_scenario_ids
            ),
            None,
        )
    experiment = None
    if threshold is not None:
        experiment = next(
            (e for e in experiments if e.target_threshold_id == str(threshold.id)), None
        )
    return _LinkedEntities(
        threshold=threshold, regret_scenario=regret_scenario, experiment=experiment
    )


def _decision_sensitivity(
    importance: str | None, threshold: Threshold | None, regret_scenario: RegretScenario | None
) -> DecisionSensitivity:
    """"If this variable changes, how much could the decision assessment
    change?" - derived only from real, already-recorded relationships
    (a verified calculated threshold, a regret scenario's own severity,
    or the upstream agent's own importance rating). Never a fabricated
    numeric slope - see module docstring and the spec's "do not fabricate
    mathematical relationships when inputs are missing" rule.
    """
    sensitivity = DecisionSensitivity.UNKNOWN

    if threshold is not None:
        if (
            threshold.validation_status == "validated"
            and threshold.derivation == "calculated_from_evidence"
        ):
            # A real, independently-verified deterministic calculation
            # (see app.agents.threshold_calculations) directly ties this
            # variable to the decision's own economics.
            sensitivity = DecisionSensitivity.HIGH
        elif threshold.validation_status == "provisional":
            sensitivity = DecisionSensitivity.MODERATE

    if regret_scenario is not None and regret_scenario.regret_level in {"critical", "high"}:
        sensitivity = _max_sensitivity(sensitivity, DecisionSensitivity.HIGH)

    importance_value = (importance or "").strip().lower()
    if importance_value == "critical":
        sensitivity = _max_sensitivity(sensitivity, DecisionSensitivity.HIGH)
    elif importance_value == "high":
        sensitivity = _max_sensitivity(sensitivity, DecisionSensitivity.MODERATE)

    return sensitivity


def _max_sensitivity(a: DecisionSensitivity, b: DecisionSensitivity) -> DecisionSensitivity:
    order = [
        DecisionSensitivity.UNKNOWN,
        DecisionSensitivity.NEGLIGIBLE,
        DecisionSensitivity.LOW,
        DecisionSensitivity.MODERATE,
        DecisionSensitivity.HIGH,
        DecisionSensitivity.CRITICAL,
    ]
    # UNKNOWN never "wins" over a real value - treat it as the lowest rank.
    a_rank = order.index(a) if a != DecisionSensitivity.UNKNOWN else -1
    b_rank = order.index(b) if b != DecisionSensitivity.UNKNOWN else -1
    return a if a_rank >= b_rank else b


def _cost_band(experiment: Experiment | None, decision_budget: float | None) -> CostBand:
    if experiment is None:
        return CostBand.UNKNOWN
    if experiment.estimated_cost is not None and decision_budget and decision_budget > 0:
        ratio = experiment.estimated_cost / decision_budget
        if ratio <= _COST_RATIO_LOW_MAX:
            return CostBand.LOW
        if ratio <= _COST_RATIO_MEDIUM_MAX:
            return CostBand.MEDIUM
        return CostBand.HIGH
    if experiment.experiment_type is not None:
        try:
            experiment_type = ExperimentType(experiment.experiment_type)
        except ValueError:
            return CostBand.UNKNOWN
        return _EXPERIMENT_TYPE_COST_BAND.get(experiment_type, CostBand.UNKNOWN)
    return CostBand.UNKNOWN


def _historical_relevance(
    threshold: Threshold | None, historical_context: HistoricalContext | None
) -> tuple[HistoricalRelevance, int]:
    """How much the SAME user's own past-decision learnings (Step 19)
    touch this specific variable - matched only by an exact,
    case-insensitive comparison against the linked threshold's own
    `variable` name, never by fuzzy/semantic guessing. Returns
    `(NONE, 0)` whenever there is no linked threshold at all, since there
    is then no real variable name to match against.
    """
    if threshold is None or historical_context is None or not historical_context.found:
        return HistoricalRelevance.NONE, 0

    variable = threshold.variable.strip().lower()
    if not variable:
        return HistoricalRelevance.NONE, 0

    count = sum(
        1
        for insight in historical_context.relevant_learnings
        if variable in insight.statement.lower()
    )
    if count == 0:
        return HistoricalRelevance.NONE, 0
    if count == 1:
        return HistoricalRelevance.LOW, count
    if count == 2:
        return HistoricalRelevance.MEDIUM, count
    return HistoricalRelevance.HIGH, count


def _rationale(
    title: str,
    information_value: ValueBand,
    practical_value: ValueBand,
    decision_sensitivity: DecisionSensitivity,
    uncertainty_level: UncertaintyLevel,
    current_evidence_strength: EvidenceStrength,
    potential_decision_impact: ImpactLevel | None,
    cost_band: CostBand,
    feasibility: Feasibility | None,
    reversibility: Reversibility | None,
    threshold_status: ThresholdLinkStatus,
) -> str:
    """Plain-English explanation built ONLY from this item's own recorded
    fields - never free-form LLM prose, never a claim not directly
    traceable to one of the arguments above."""
    if information_value == ValueBand.UNKNOWN:
        return (
            f"'{title}' cannot yet be scored: at least one of decision impact, decision "
            "sensitivity, or current uncertainty has not been established for it."
        )

    clauses = [
        f"the decision's assessment is {decision_sensitivity.value.replace('_', ' ')} in its "
        "sensitivity to this variable",
        f"current uncertainty about it is {uncertainty_level.value.replace('_', ' ')} "
        f"(evidence on file is {current_evidence_strength.value})",
    ]
    if potential_decision_impact is not None:
        clauses.append(
            f"a wrong assumption here would have {potential_decision_impact.value} impact"
        )

    cost_clause = (
        f"the cost to test it is {cost_band.value}"
        if cost_band != CostBand.UNKNOWN
        else "no test has been costed for it yet"
    )
    feasibility_clause = (
        f"feasibility is {feasibility.value}" if feasibility else "feasibility is unrated"
    )
    reversibility_clause = (
        f"reversibility is {reversibility.value}" if reversibility else "reversibility is unrated"
    )

    threshold_clause = (
        "it already connects to a recorded threshold"
        if threshold_status == ThresholdLinkStatus.LINKED
        else "no threshold has been established for it yet"
    )

    return (
        f"'{title}' has {information_value.value.replace('_', ' ')} information value because "
        + "; ".join(clauses)
        + f". Practical value is {practical_value.value.replace('_', ' ')} because "
        + f"{cost_clause}, {feasibility_clause}, and {reversibility_clause}. "
        + f"{threshold_clause.capitalize()}."
    )


def compute_item(
    uncertainty,
    kind: str,
    thresholds: list[Threshold],
    regret_scenarios: list[RegretScenario],
    experiments: list[Experiment],
    decision_budget: float | None,
    historical_context: HistoricalContext | None,
) -> tuple[ValueOfInformationItem, tuple[float, float]]:
    """Score exactly one uncertainty (an `Assumption` or `Blindspot`).

    Returns `(item, (information_value_raw, practical_value_raw))` - the
    raw floats are needed by `compute_analysis`'s ranking/tiebreak logic
    but are deliberately NOT stored on `ValueOfInformationItem` itself
    (only the qualitative bands are persisted/returned), per the "do not
    present a raw float as a calibrated probability" rule.

    `kind` is `"assumption"` or `"blindspot"` - it determines which of
    `related_assumption_ids`/`related_blindspot_ids` carries
    `uncertainty_id`, per this module's own convention (see
    `ValueOfInformationItem`'s docstring).
    """
    uncertainty_id = str(uncertainty.id)
    title = uncertainty.statement if kind == "assumption" else uncertainty.question
    description = title
    importance = getattr(uncertainty, "importance", None)

    linked = _find_linked_entities(uncertainty_id, thresholds, regret_scenarios, experiments)

    regret_impact_values = [i.value for i in ImpactLevel]
    potential_decision_impact = (
        ImpactLevel(linked.regret_scenario.impact)
        if linked.regret_scenario is not None
        and linked.regret_scenario.impact in regret_impact_values
        else _importance_to_impact(importance)
    )
    decision_sensitivity = _decision_sensitivity(
        importance, linked.threshold, linked.regret_scenario
    )
    uncertainty_level = _uncertainty_level(uncertainty)
    current_evidence_strength = _evidence_strength(uncertainty)
    regret_severity = (
        SeverityLevel(linked.regret_scenario.regret_level)
        if linked.regret_scenario is not None
        and linked.regret_scenario.regret_level in [s.value for s in SeverityLevel]
        else None
    )

    cost_band = _cost_band(linked.experiment, decision_budget)
    feasibility_values = [f.value for f in Feasibility]
    feasibility = (
        Feasibility(linked.experiment.feasibility)
        if linked.experiment is not None and linked.experiment.feasibility in feasibility_values
        else None
    )
    reversibility = (
        Reversibility(linked.experiment.reversibility)
        if linked.experiment is not None
        and linked.experiment.reversibility in [r.value for r in Reversibility]
        else None
    )
    duration = linked.experiment.duration_days if linked.experiment is not None else None

    threshold_status = (
        ThresholdLinkStatus.LINKED
        if linked.threshold is not None
        else ThresholdLinkStatus.NOT_ESTABLISHED
    )
    historical_relevance, prior_learning_count = _historical_relevance(
        linked.threshold, historical_context
    )

    impact_norm = _normalize_band(potential_decision_impact, _IMPACT_ORDER)
    sensitivity_norm = _normalize_band(decision_sensitivity, _SENSITIVITY_ORDER)
    uncertainty_norm = _normalize_band(uncertainty_level, _UNCERTAINTY_ORDER)

    known_component_count = sum(
        1
        for value in (
            potential_decision_impact,
            decision_sensitivity if decision_sensitivity != DecisionSensitivity.UNKNOWN else None,
            uncertainty_level if uncertainty_level != UncertaintyLevel.UNKNOWN else None,
            cost_band if cost_band != CostBand.UNKNOWN else None,
            feasibility,
            reversibility,
        )
        if value is not None
    )
    confidence = round(known_component_count / 6, 4)

    if impact_norm is None or sensitivity_norm is None or uncertainty_norm is None:
        information_value = ValueBand.UNKNOWN
        practical_value = ValueBand.UNKNOWN
        information_value_raw = 0.0
        practical_value_raw = 0.0
    else:
        information_value_raw = impact_norm * sensitivity_norm * uncertainty_norm
        information_value = _band_from_raw(information_value_raw)

        practical_value_raw = (
            information_value_raw
            * _COST_MULTIPLIER[cost_band]
            * _FEASIBILITY_MULTIPLIER[feasibility]
            * _REVERSIBILITY_MULTIPLIER[reversibility]
        )
        practical_value = _band_from_raw(practical_value_raw)

    rationale = _rationale(
        title,
        information_value,
        practical_value,
        decision_sensitivity,
        uncertainty_level,
        current_evidence_strength,
        potential_decision_impact,
        cost_band,
        feasibility,
        reversibility,
        threshold_status,
    )

    return ValueOfInformationItem(
        uncertainty_id=uncertainty_id,
        title=title,
        description=description,
        related_assumption_ids=[uncertainty_id] if kind == "assumption" else [],
        related_blindspot_ids=[uncertainty_id] if kind == "blindspot" else [],
        related_threshold_ids=[str(linked.threshold.id)] if linked.threshold else [],
        related_regret_scenario_ids=(
            [str(linked.regret_scenario.id)] if linked.regret_scenario else []
        ),
        related_experiment_id=str(linked.experiment.id) if linked.experiment else None,
        potential_decision_impact=potential_decision_impact,
        decision_sensitivity=decision_sensitivity,
        regret_severity=regret_severity,
        current_evidence_strength=current_evidence_strength,
        uncertainty_level=uncertainty_level,
        estimated_test_cost=cost_band,
        estimated_test_duration_days=duration,
        feasibility=feasibility,
        reversibility=reversibility,
        historical_relevance=historical_relevance,
        prior_learning_count=prior_learning_count,
        threshold_status=threshold_status,
        information_value=information_value,
        practical_value=practical_value,
        priority=1,  # placeholder; overwritten by compute_analysis after ranking every item
        rationale=rationale,
        confidence=confidence,
    ), (information_value_raw, practical_value_raw)


def compute_analysis(
    decision: DecisionResponse,
    assumptions: list[Assumption],
    blindspots: list[Blindspot],
    thresholds: list[Threshold],
    regret_scenarios: list[RegretScenario],
    experiments: list[Experiment],
    historical_context: HistoricalContext | None = None,
) -> ValueOfInformationAnalysis:
    """Score and rank every uncertainty (assumption + blindspot) for one
    decision, deterministically. Never raises for missing/thin upstream
    data - an uncertainty with nothing else recorded about it simply
    scores `UNKNOWN` and sorts last; see `compute_item`.
    """
    scored: list[tuple[ValueOfInformationItem, tuple[float, float]]] = []
    for assumption in assumptions:
        scored.append(
            compute_item(
                assumption, "assumption", thresholds, regret_scenarios, experiments,
                decision.budget, historical_context,
            )
        )
    for blindspot in blindspots:
        scored.append(
            compute_item(
                blindspot, "blindspot", thresholds, regret_scenarios, experiments,
                decision.budget, historical_context,
            )
        )

    def _historical_rank(item: ValueOfInformationItem) -> int:
        return _HISTORICAL_RELEVANCE_ORDER.index(item.historical_relevance)

    def _sort_key(entry: tuple[ValueOfInformationItem, tuple[float, float]]):
        item, (information_raw, practical_raw) = entry
        return (-practical_raw, -information_raw, item.uncertainty_id)

    # Primary deterministic sort by the documented formula.
    scored.sort(key=_sort_key)

    # Historical relevance only breaks ties between items whose
    # practical_value_raw are within _TIE_EPSILON of each other - see
    # module docstring step 5. Applied as a stable, localized re-sort
    # over contiguous near-tied groups rather than a global secondary
    # sort key, so it can never influence items that are not genuinely
    # close in score.
    _apply_historical_tiebreak(scored)

    ranked_items = [item for item, _ in scored]
    for index, item in enumerate(ranked_items, start=1):
        item.priority = index

    primary = ranked_items[0] if ranked_items else None
    primary_uncertainty_id = primary.uncertainty_id if primary else None
    primary_threshold_id = (
        primary.related_threshold_ids[0] if primary and primary.related_threshold_ids else None
    )
    why_this_is_primary = primary.rationale if primary else None

    summary = (
        f"'{primary.title}' is the highest-priority uncertainty to resolve before committing."
        if primary
        else "No assumptions or blindspots have been recorded for this decision yet."
    )

    return ValueOfInformationAnalysis(
        analysis_id=uuid4(),
        decision_id=decision.id,
        ranked_uncertainties=ranked_items,
        primary_uncertainty_id=primary_uncertainty_id,
        primary_threshold_id=primary_threshold_id,
        why_this_is_primary=why_this_is_primary,
        summary=summary,
        created_at=datetime.now(UTC),
    )


def _apply_historical_tiebreak(
    scored: list[tuple[ValueOfInformationItem, tuple[float, float]]],
) -> None:
    """Re-order contiguous runs of near-tied items (by practical_value_raw,
    within `_TIE_EPSILON`) so that, within each such run only, higher
    historical relevance sorts first. Never reorders items whose scores
    differ by more than the epsilon - history can only decide between
    otherwise-equal candidates, never override a real score difference.
    """
    index = 0
    while index < len(scored):
        run_end = index + 1
        while (
            run_end < len(scored)
            and abs(scored[run_end][1][1] - scored[index][1][1]) <= _TIE_EPSILON
        ):
            run_end += 1
        if run_end - index > 1:
            run = scored[index:run_end]
            run.sort(
                key=lambda entry: (
                    -_HISTORICAL_RELEVANCE_ORDER.index(entry[0].historical_relevance),
                    entry[0].uncertainty_id,
                )
            )
            scored[index:run_end] = run
        index = run_end
