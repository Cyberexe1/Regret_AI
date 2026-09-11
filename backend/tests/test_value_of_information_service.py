"""Tests for the deterministic Value-of-Information scoring formula
(REGRET ENGINE 2.0, Step 20) - `app.services.value_of_information_service`.

No LLM/Strands invocation happens anywhere in this file - VOI scoring is
entirely deterministic Python over plain Pydantic objects, so these tests
construct `Assumption`/`Blindspot`/`Threshold`/`RegretScenario`/
`Experiment` instances directly rather than going through the API or a
real repository.
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.agents.value_of_information_schemas import (
    CostBand,
    DecisionSensitivity,
    HistoricalRelevance,
    ThresholdLinkStatus,
    UncertaintyLevel,
    ValueBand,
)
from app.memory.similarity_schemas import HistoricalContext, HistoricalInsight, SimilarityScore
from app.schemas.decision import DecisionResponse, DecisionStatus
from app.schemas.decision_resources import (
    Assumption,
    AssumptionSource,
    Blindspot,
    BlindspotEvidenceStatus,
    EvidenceStatus,
    Experiment,
    ExperimentStatus,
    RegretScenario,
    Threshold,
)
from app.services.value_of_information_service import compute_analysis, compute_item

NOW = datetime.now(UTC)


def _decision(**overrides) -> DecisionResponse:
    payload = {
        "id": uuid4(),
        "title": "Open a cloud kitchen",
        "description": "Considering a Rs 5 lakh investment.",
        "budget": 500000.0,
        "status": DecisionStatus.DRAFT,
        "created_at": NOW,
        "updated_at": NOW,
    }
    payload.update(overrides)
    return DecisionResponse(**payload)


def _assumption(**overrides) -> Assumption:
    payload = {
        "id": uuid4(),
        "decision_id": uuid4(),
        "statement": "Repeat customers will sustain unit economics.",
        "source": AssumptionSource.IMPLICIT,
        "importance": "critical",
        "confidence": 0.3,
        "evidence_status": EvidenceStatus.NOT_ADDRESSED,
        "created_at": NOW,
        "updated_at": NOW,
    }
    payload.update(overrides)
    return Assumption(**payload)


def _blindspot(**overrides) -> Blindspot:
    payload = {
        "id": uuid4(),
        "decision_id": uuid4(),
        "question": "What happens if repeat orders fall below target?",
        "importance": "medium",
        "confidence": 0.5,
        "evidence_status": BlindspotEvidenceStatus.NOT_ADDRESSED,
        "created_at": NOW,
    }
    payload.update(overrides)
    return Blindspot(**payload)


def _regret_scenario(related_assumption_ids: list[str], **overrides) -> RegretScenario:
    payload = {
        "id": uuid4(),
        "decision_id": uuid4(),
        "title": "Adoption failure",
        "failure_condition": "Repeat-order rate remains below sustainable levels.",
        "regret_level": "critical",
        "impact": "severe",
        "related_assumption_ids": related_assumption_ids,
        "created_at": NOW,
    }
    payload.update(overrides)
    return RegretScenario(**payload)


def _threshold(
    related_assumption_ids: list[str], related_regret_scenario_ids: list[str], **overrides
) -> Threshold:
    payload = {
        "id": uuid4(),
        "decision_id": uuid4(),
        "variable": "Repeat-order rate",
        "validation_status": "validated",
        "derivation": "calculated_from_evidence",
        "related_assumption_ids": related_assumption_ids,
        "related_regret_scenario_ids": related_regret_scenario_ids,
        "created_at": NOW,
    }
    payload.update(overrides)
    return Threshold(**payload)


def _experiment(target_threshold_id: str, **overrides) -> Experiment:
    payload = {
        "id": uuid4(),
        "decision_id": uuid4(),
        "title": "Pilot",
        "hypothesis": "x",
        "target_threshold_id": target_threshold_id,
        "decision_rule": "x",
        "status": ExperimentStatus.RECOMMENDED,
        "created_at": NOW,
        "updated_at": NOW,
    }
    payload.update(overrides)
    return Experiment(**payload)


# --- Core distinction: HIGH RISK != HIGH VOI ---------------------------------


def test_high_risk_but_already_understood_scores_lower_than_genuinely_uncertain() -> None:
    """A well-understood (high-confidence) critical-impact assumption must
    score LOWER information_value than an equally critical-impact
    assumption that is genuinely uncertain - risk alone is not value."""
    decision = _decision()

    a_understood = _assumption(
        importance="critical", confidence=0.95, evidence_status=EvidenceStatus.SUPPORTED
    )
    s1 = _regret_scenario([str(a_understood.id)], regret_level="critical", impact="severe")
    t1 = _threshold([str(a_understood.id)], [str(s1.id)])

    a_unknown = _assumption(
        importance="critical", confidence=0.05, evidence_status=EvidenceStatus.NOT_ADDRESSED
    )
    s2 = _regret_scenario([str(a_unknown.id)], regret_level="critical", impact="severe")
    t2 = _threshold([str(a_unknown.id)], [str(s2.id)])

    analysis = compute_analysis(
        decision, [a_understood, a_unknown], [], [t1, t2], [s1, s2], []
    )

    understood_item = next(
        i for i in analysis.ranked_uncertainties if i.uncertainty_id == str(a_understood.id)
    )
    unknown_item = next(
        i for i in analysis.ranked_uncertainties if i.uncertainty_id == str(a_unknown.id)
    )

    band_order = [
        ValueBand.VERY_LOW, ValueBand.LOW, ValueBand.MEDIUM, ValueBand.HIGH, ValueBand.VERY_HIGH
    ]
    assert band_order.index(unknown_item.information_value) > band_order.index(
        understood_item.information_value
    )
    assert analysis.primary_uncertainty_id == str(a_unknown.id)


def test_low_cost_high_impact_outranks_high_cost_high_impact() -> None:
    """Two uncertainties with IDENTICAL information value: the one with a
    cheap, feasible, reversible test must rank #1; the one with an
    expensive, infeasible, irreversible test must rank #2."""
    decision = _decision()

    a1 = _assumption(importance="critical", confidence=0.1)
    s1 = _regret_scenario([str(a1.id)], regret_level="critical", impact="severe")
    t1 = _threshold([str(a1.id)], [str(s1.id)], variable="cheap-variable")
    e1 = _experiment(str(t1.id), feasibility="high", reversibility="high", estimated_cost=5000.0)

    a2 = _assumption(importance="critical", confidence=0.1)
    s2 = _regret_scenario([str(a2.id)], regret_level="critical", impact="severe")
    t2 = _threshold([str(a2.id)], [str(s2.id)], variable="expensive-variable")
    e2 = _experiment(str(t2.id), feasibility="low", reversibility="low", estimated_cost=250000.0)

    analysis = compute_analysis(decision, [a1, a2], [], [t1, t2], [s1, s2], [e1, e2])

    cheap_item = next(i for i in analysis.ranked_uncertainties if i.uncertainty_id == str(a1.id))
    expensive_item = next(
        i for i in analysis.ranked_uncertainties if i.uncertainty_id == str(a2.id)
    )

    assert cheap_item.information_value == expensive_item.information_value  # same info value
    assert cheap_item.priority < expensive_item.priority  # cheap ranks first
    assert cheap_item.estimated_test_cost == CostBand.LOW
    assert expensive_item.estimated_test_cost == CostBand.HIGH
    assert analysis.primary_uncertainty_id == str(a1.id)


# --- Impact + uncertainty combinations ---------------------------------------


def test_high_impact_high_uncertainty_scores_high() -> None:
    decision = _decision()
    a = _assumption(importance="critical", confidence=0.05)
    s = _regret_scenario([str(a.id)], regret_level="critical", impact="severe")
    t = _threshold([str(a.id)], [str(s.id)])

    item, _ = compute_item(a, "assumption", [t], [s], [], decision.budget, None)

    assert item.information_value in (ValueBand.HIGH, ValueBand.VERY_HIGH)


def test_low_impact_high_uncertainty_scores_lower_than_high_impact_high_uncertainty() -> None:
    decision = _decision()
    a_low = _assumption(importance="low", confidence=0.05)
    a_high = _assumption(importance="critical", confidence=0.05)
    s_high = _regret_scenario([str(a_high.id)], regret_level="critical", impact="severe")
    t_high = _threshold([str(a_high.id)], [str(s_high.id)])

    low_item, low_raw = compute_item(a_low, "assumption", [], [], [], decision.budget, None)
    high_item, high_raw = compute_item(
        a_high, "assumption", [t_high], [s_high], [], decision.budget, None
    )

    assert high_raw[0] > low_raw[0]


# --- Cost / feasibility / reversibility --------------------------------------


def test_high_feasibility_scores_higher_practical_value_than_low_feasibility() -> None:
    decision = _decision()
    a1 = _assumption(confidence=0.1, importance="critical")
    s1 = _regret_scenario([str(a1.id)], regret_level="critical", impact="severe")
    t1 = _threshold([str(a1.id)], [str(s1.id)])
    e_high = _experiment(str(t1.id), feasibility="high", reversibility="medium")
    e_low = _experiment(str(t1.id), feasibility="low", reversibility="medium")

    item_high, raw_high = compute_item(
        a1, "assumption", [t1], [s1], [e_high], decision.budget, None
    )
    item_low, raw_low = compute_item(a1, "assumption", [t1], [s1], [e_low], decision.budget, None)

    assert raw_high[1] > raw_low[1]


def test_high_reversibility_scores_higher_practical_value_than_low_reversibility() -> None:
    decision = _decision()
    a1 = _assumption(confidence=0.1, importance="critical")
    s1 = _regret_scenario([str(a1.id)], regret_level="critical", impact="severe")
    t1 = _threshold([str(a1.id)], [str(s1.id)])
    e_reversible = _experiment(str(t1.id), feasibility="medium", reversibility="high")
    e_irreversible = _experiment(str(t1.id), feasibility="medium", reversibility="low")

    _, raw_reversible = compute_item(
        a1, "assumption", [t1], [s1], [e_reversible], decision.budget, None
    )
    _, raw_irreversible = compute_item(
        a1, "assumption", [t1], [s1], [e_irreversible], decision.budget, None
    )

    assert raw_reversible[1] > raw_irreversible[1]


# --- Missing inputs -> UNKNOWN, never fabricated -----------------------------


def test_missing_impact_and_sensitivity_and_uncertainty_returns_unknown_band() -> None:
    """An assumption with no importance, no confidence, no evidence_status
    signal, no linked threshold/regret scenario must score UNKNOWN, never
    a fabricated default."""
    decision = _decision()
    a = Assumption(
        id=uuid4(), decision_id=uuid4(), statement="x", source=None, importance=None,
        confidence=None, evidence_status=EvidenceStatus.UNVERIFIED, created_at=NOW, updated_at=NOW,
    )

    item, raw = compute_item(a, "assumption", [], [], [], decision.budget, None)

    assert item.information_value == ValueBand.UNKNOWN
    assert item.practical_value == ValueBand.UNKNOWN
    assert raw == (0.0, 0.0)


def test_missing_experiment_cost_and_duration_scores_cost_band_unknown_not_fabricated() -> None:
    decision = _decision()
    a = _assumption(confidence=0.1, importance="high")
    s = _regret_scenario([str(a.id)], regret_level="high", impact="high")
    t = _threshold([str(a.id)], [str(s.id)])
    # No experiment recommended at all for this threshold.

    item, _ = compute_item(a, "assumption", [t], [s], [], decision.budget, None)

    assert item.estimated_test_cost == CostBand.UNKNOWN
    assert item.estimated_test_duration_days is None
    assert item.feasibility is None
    assert item.reversibility is None


def test_missing_threshold_marks_not_established_never_invents_one() -> None:
    decision = _decision()
    a = _assumption(confidence=0.1, importance="high")

    item, _ = compute_item(a, "assumption", [], [], [], decision.budget, None)

    assert item.threshold_status == ThresholdLinkStatus.NOT_ESTABLISHED
    assert item.related_threshold_ids == []


def test_missing_evidence_status_and_confidence_defaults_uncertainty_to_unknown() -> None:
    decision = _decision()
    # No confidence set at all, and evidence_status is the pre-analysis
    # default (unverified) - neither numeric nor categorical signal exists.
    a = Assumption(
        id=uuid4(), decision_id=uuid4(), statement="x", confidence=None,
        evidence_status=EvidenceStatus.UNVERIFIED, created_at=NOW, updated_at=NOW,
    )

    item, _ = compute_item(a, "assumption", [], [], [], decision.budget, None)

    assert item.uncertainty_level == UncertaintyLevel.UNKNOWN


# --- Decision sensitivity: never fabricated ----------------------------------


def test_decision_sensitivity_unknown_when_no_threshold_regret_scenario_or_importance() -> None:
    decision = _decision()
    a = Assumption(
        id=uuid4(), decision_id=uuid4(), statement="x", importance=None, confidence=0.5,
        evidence_status=EvidenceStatus.NOT_ADDRESSED, created_at=NOW, updated_at=NOW,
    )

    item, _ = compute_item(a, "assumption", [], [], [], decision.budget, None)

    assert item.decision_sensitivity == DecisionSensitivity.UNKNOWN


def test_decision_sensitivity_high_from_validated_calculated_threshold() -> None:
    decision = _decision()
    a = _assumption(importance=None, confidence=0.4)
    t = _threshold(
        [str(a.id)], [], validation_status="validated", derivation="calculated_from_evidence"
    )

    item, _ = compute_item(a, "assumption", [t], [], [], decision.budget, None)

    assert item.decision_sensitivity == DecisionSensitivity.HIGH


# --- Historical relevance: tiebreaker only, never overriding current evidence ---


def _historical_context_mentioning(variable: str, count: int) -> HistoricalContext:
    insights = [
        HistoricalInsight(
            insight_id=uuid4(), source_decision_id=uuid4(), source_memory_id=uuid4(),
            learning_id=uuid4(), statement=f"Observed {variable} failed validation.",
            relevance_score=0.7, relevance_reason="x", learning_type="threshold_failed",
            source_type="re_evaluation", created_at=NOW,
        )
        for _ in range(count)
    ]
    score = SimilarityScore(
        decision_id=uuid4(), score=0.7, matched_features=["x"], explanation="x", confidence=0.7
    )
    return HistoricalContext(
        found=True,
        relevant_decisions=[score],
        relevant_decisions_count=1,
        relevant_learnings=insights,
    )


def test_historical_relevance_reflects_repeated_past_failures() -> None:
    decision = _decision()
    a = _assumption(confidence=0.3, importance="high")
    t = _threshold([str(a.id)], [], variable="Customer retention")
    context = _historical_context_mentioning("customer retention", count=3)

    item, _ = compute_item(a, "assumption", [t], [], [], decision.budget, context)

    assert item.historical_relevance == HistoricalRelevance.HIGH
    assert item.prior_learning_count == 3


def test_historical_relevance_none_when_variable_never_mentioned() -> None:
    decision = _decision()
    a = _assumption(confidence=0.3, importance="high")
    t = _threshold([str(a.id)], [], variable="Kitchen utilization")
    context = _historical_context_mentioning("customer retention", count=3)

    item, _ = compute_item(a, "assumption", [t], [], [], decision.budget, context)

    assert item.historical_relevance == HistoricalRelevance.NONE
    assert item.prior_learning_count == 0


def test_current_evidence_outranks_historical_relevance_when_scores_differ() -> None:
    """Two uncertainties with meaningfully DIFFERENT practical_value must
    never be reordered by historical relevance - history only breaks
    near-ties (see module docstring step 5)."""
    decision = _decision()

    a_strong_current = _assumption(importance="critical", confidence=0.05)
    s1 = _regret_scenario([str(a_strong_current.id)], regret_level="critical", impact="severe")
    t1 = _threshold([str(a_strong_current.id)], [str(s1.id)], variable="no-history-variable")

    a_weak_current = _assumption(importance="low", confidence=0.6)
    t2 = _threshold([str(a_weak_current.id)], [], variable="lots-of-history-variable")

    context = _historical_context_mentioning("lots-of-history-variable", count=5)

    analysis = compute_analysis(
        decision, [a_strong_current, a_weak_current], [], [t1, t2], [s1], [], context
    )

    assert analysis.primary_uncertainty_id == str(a_strong_current.id)


def test_historical_relevance_breaks_a_genuine_near_tie() -> None:
    """When two items score identically on the deterministic formula,
    higher historical relevance should be preferred as a tiebreaker."""
    decision = _decision()

    a1 = _assumption(importance="high", confidence=0.2)
    s1 = _regret_scenario([str(a1.id)], regret_level="high", impact="high")
    t1 = _threshold([str(a1.id)], [str(s1.id)], variable="variable-with-history")

    a2 = _assumption(importance="high", confidence=0.2)
    s2 = _regret_scenario([str(a2.id)], regret_level="high", impact="high")
    t2 = _threshold([str(a2.id)], [str(s2.id)], variable="variable-without-history")

    context = _historical_context_mentioning("variable-with-history", count=3)

    analysis = compute_analysis(decision, [a1, a2], [], [t1, t2], [s1, s2], [], context)

    assert analysis.ranked_uncertainties[0].uncertainty_id == str(a1.id)


# --- Boundary / invalid values -----------------------------------------------


def test_score_never_raises_for_empty_decision() -> None:
    decision = _decision()

    analysis = compute_analysis(decision, [], [], [], [], [])

    assert analysis.ranked_uncertainties == []
    assert analysis.primary_uncertainty_id is None
    assert analysis.primary_threshold_id is None


def test_score_never_raises_for_zero_budget() -> None:
    """A decision with budget=0 must not raise a division-by-zero when
    computing cost ratio against an experiment's estimated_cost."""
    decision = _decision(budget=0.0)
    a = _assumption(confidence=0.1, importance="critical")
    s = _regret_scenario([str(a.id)], regret_level="critical", impact="severe")
    t = _threshold([str(a.id)], [str(s.id)])
    e = _experiment(str(t.id), estimated_cost=1000.0)

    item, _ = compute_item(a, "assumption", [t], [s], [e], decision.budget, None)

    assert item.estimated_test_cost in (
        CostBand.LOW, CostBand.MEDIUM, CostBand.HIGH, CostBand.UNKNOWN
    )


def test_score_never_raises_for_none_budget() -> None:
    decision = _decision(budget=None)
    a = _assumption(confidence=0.1, importance="critical")
    s = _regret_scenario([str(a.id)], regret_level="critical", impact="severe")
    t = _threshold([str(a.id)], [str(s.id)])
    e = _experiment(str(t.id), estimated_cost=1000.0, experiment_type="survey")

    item, _ = compute_item(a, "assumption", [t], [s], [e], decision.budget, None)

    # Falls back to the experiment_type cost tier since no budget exists
    # to compute a ratio against.
    assert item.estimated_test_cost == CostBand.LOW


def test_confidence_field_is_bounded_zero_to_one() -> None:
    decision = _decision()
    a = _assumption(confidence=0.1, importance="critical")

    item, _ = compute_item(a, "assumption", [], [], [], decision.budget, None)

    assert 0.0 <= item.confidence <= 1.0


def test_priority_is_1_based_and_sequential() -> None:
    decision = _decision()
    a1 = _assumption(confidence=0.1, importance="critical")
    a2 = _assumption(confidence=0.6, importance="low")

    analysis = compute_analysis(decision, [a1, a2], [], [], [], [])

    priorities = sorted(item.priority for item in analysis.ranked_uncertainties)
    assert priorities == list(range(1, len(analysis.ranked_uncertainties) + 1))


def test_ranking_includes_both_assumptions_and_blindspots() -> None:
    decision = _decision()
    a = _assumption(confidence=0.2, importance="high")
    b = _blindspot(confidence=0.3, importance="high")

    analysis = compute_analysis(decision, [a], [b], [], [], [])

    uncertainty_ids = {item.uncertainty_id for item in analysis.ranked_uncertainties}
    assert str(a.id) in uncertainty_ids
    assert str(b.id) in uncertainty_ids


def test_blindspot_related_ids_populate_related_blindspot_ids_not_assumption_ids() -> None:
    decision = _decision()
    b = _blindspot(confidence=0.3, importance="high")

    item, _ = compute_item(b, "blindspot", [], [], [], decision.budget, None)

    assert item.related_blindspot_ids == [str(b.id)]
    assert item.related_assumption_ids == []


# --- Rationale must be traceable to real fields ------------------------------


def test_rationale_for_unknown_item_explains_why_it_cannot_be_scored() -> None:
    decision = _decision()
    a = Assumption(
        id=uuid4(), decision_id=uuid4(), statement="Mystery assumption", importance=None,
        confidence=None, evidence_status=EvidenceStatus.UNVERIFIED, created_at=NOW, updated_at=NOW,
    )

    item, _ = compute_item(a, "assumption", [], [], [], decision.budget, None)

    assert "cannot yet be scored" in item.rationale
    assert "Mystery assumption" in item.rationale


def test_rationale_for_scored_item_mentions_cost_feasibility_and_threshold_status() -> None:
    decision = _decision()
    a = _assumption(confidence=0.1, importance="critical")
    s = _regret_scenario([str(a.id)], regret_level="critical", impact="severe")
    t = _threshold([str(a.id)], [str(s.id)])
    e = _experiment(str(t.id), feasibility="high", reversibility="high", estimated_cost=1000.0)

    item, _ = compute_item(a, "assumption", [t], [s], [e], decision.budget, None)

    assert "cost to test it is" in item.rationale
    assert "feasibility is" in item.rationale
    assert "connects to a recorded threshold" in item.rationale


# --- Primary uncertainty / threshold selection -------------------------------


def test_primary_threshold_id_copied_from_primary_uncertainty_link() -> None:
    decision = _decision()
    a = _assumption(confidence=0.1, importance="critical")
    s = _regret_scenario([str(a.id)], regret_level="critical", impact="severe")
    t = _threshold([str(a.id)], [str(s.id)])

    analysis = compute_analysis(decision, [a], [], [t], [s], [])

    assert analysis.primary_threshold_id == str(t.id)


def test_primary_threshold_id_is_none_when_primary_uncertainty_has_no_threshold() -> None:
    decision = _decision()
    a = _assumption(confidence=0.05, importance="critical")

    analysis = compute_analysis(decision, [a], [], [], [], [])

    assert analysis.primary_uncertainty_id == str(a.id)
    assert analysis.primary_threshold_id is None


def test_why_this_is_primary_matches_primary_items_own_rationale() -> None:
    decision = _decision()
    a = _assumption(confidence=0.1, importance="critical")

    analysis = compute_analysis(decision, [a], [], [], [], [])

    primary_item = analysis.ranked_uncertainties[0]
    assert analysis.why_this_is_primary == primary_item.rationale


def test_summary_reflects_no_uncertainties_recorded() -> None:
    decision = _decision()

    analysis = compute_analysis(decision, [], [], [], [], [])

    assert "no assumptions or blindspots" in analysis.summary.lower()


# --- methodology_version / determinism ---------------------------------------


def test_methodology_version_is_recorded_on_every_analysis() -> None:
    decision = _decision()
    analysis = compute_analysis(decision, [], [], [], [], [])

    assert analysis.methodology_version == "voi-v1"


def test_computation_is_fully_deterministic_across_repeated_calls() -> None:
    decision = _decision()
    a = _assumption(confidence=0.2, importance="high")
    s = _regret_scenario([str(a.id)], regret_level="high", impact="high")
    t = _threshold([str(a.id)], [str(s.id)])

    first = compute_analysis(decision, [a], [], [t], [s], [])
    second = compute_analysis(decision, [a], [], [t], [s], [])

    first_item = first.ranked_uncertainties[0]
    second_item = second.ranked_uncertainties[0]
    assert first_item.information_value == second_item.information_value
    assert first_item.practical_value == second_item.practical_value
    assert first_item.priority == second_item.priority
