"""Tests for the Experiment Planner agent module itself.

Focused on the parts that don't require invoking a real model: prompt
construction and the structured schemas. No Bedrock call happens anywhere
in this file.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.agents.experiment_planner import build_experiment_planner_prompt
from app.agents.schemas import (
    DecisionAnalysis,
    Experiment,
    ExperimentPlan,
    ExperimentType,
    Feasibility,
    InformationGain,
    Reversibility,
)
from app.schemas.decision_resources import Assumption as StoredAssumption
from app.schemas.decision_resources import AssumptionSource as StoredAssumptionSource
from app.schemas.decision_resources import Blindspot as StoredBlindspot
from app.schemas.decision_resources import BlindspotEvidenceStatus, EvidenceStatus
from app.schemas.decision_resources import Challenge as StoredChallenge
from app.schemas.decision_resources import EvidenceFinding as StoredEvidenceFinding
from app.schemas.decision_resources import RegretScenario as StoredRegretScenario
from app.schemas.decision_resources import Threshold as StoredThreshold


def _sample_decision_analysis() -> DecisionAnalysis:
    return DecisionAnalysis(
        decision_summary="Whether to open a second bakery location downtown.",
        decision_type="market expansion",
        goal="Increase revenue by expanding to a second physical location.",
        constraints=["Limited capital"],
        success_criteria=["Second location breaks even within 12 months"],
        key_variables=["Foot traffic downtown"],
    )


def _sample_stored_assumption() -> StoredAssumption:
    return StoredAssumption(
        id=uuid4(),
        decision_id=uuid4(),
        statement="Customers will order at least twice per month.",
        source=StoredAssumptionSource.IMPLICIT,
        importance="critical",
        confidence=0.45,
        evidence_status=EvidenceStatus.NOT_ADDRESSED,
        dependency="Business profitability",
        failure_consequence="Revenue may remain below the required operating margin.",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _sample_stored_blindspot() -> StoredBlindspot:
    return StoredBlindspot(
        id=uuid4(),
        decision_id=uuid4(),
        question="What happens to unit economics if repeat orders fall below 20%?",
        category="untested_assumption",
        importance="critical",
        confidence=0.7,
        evidence_status=BlindspotEvidenceStatus.NOT_ADDRESSED,
        related_assumption_ids=[],
        why_it_matters="Repeat order rate drives whether the location breaks even.",
        created_at=datetime.now(UTC),
    )


def _sample_stored_evidence_finding() -> StoredEvidenceFinding:
    return StoredEvidenceFinding(
        id=uuid4(),
        decision_id=uuid4(),
        evidence_id=uuid4(),
        claim="Downtown foot traffic supports a second location.",
        support_level="supports",
        credibility="medium",
        related_assumption_ids=[],
        related_blindspot_ids=[],
        explanation="Foot traffic rose year over year per the submitted report.",
        excerpt="Downtown foot traffic rose 12% year over year.",
        created_at=datetime.now(UTC),
    )


def _sample_stored_challenge() -> StoredChallenge:
    return StoredChallenge(
        id=uuid4(),
        decision_id=uuid4(),
        claim="Repeat customers will be high enough to sustain the business.",
        attack="The evidence only establishes initial demand, not repeat behavior.",
        severity="critical",
        confidence=0.7,
        related_assumption_ids=[],
        related_blindspot_ids=[],
        related_evidence_finding_ids=[],
        failure_mechanism="If repeat ordering stays low, unit economics no longer hold.",
        evidence_basis="No submitted evidence addresses repeat-purchase behavior.",
        created_at=datetime.now(UTC),
    )


def _sample_stored_regret_scenario() -> StoredRegretScenario:
    return StoredRegretScenario(
        id=uuid4(),
        decision_id=uuid4(),
        title="Adoption failure",
        failure_condition="Repeat-order rate remains below sustainable levels.",
        probability_band="unknown",
        impact="severe",
        regret_level="high",
        trigger_variable="Repeat-order rate",
        trigger_direction="below",
        consequence="Full capital commitment occurs before demand quality is validated.",
        related_assumption_ids=[],
        related_challenge_ids=[],
        evidence_basis="No repeat-purchase evidence was submitted for this decision.",
        created_at=datetime.now(UTC),
    )


def _sample_stored_threshold() -> StoredThreshold:
    return StoredThreshold(
        id=uuid4(),
        decision_id=uuid4(),
        variable="Repeat-order rate",
        threshold_type="unknown",
        direction="below",
        threshold_value=None,
        confidence=0.6,
        derivation="unknown",
        consequence="The projected unit economics no longer hold if repeat orders stay too low.",
        related_assumption_ids=[],
        related_regret_scenario_ids=[],
        evidence_basis="No repeat-purchase evidence was submitted for this decision.",
        validation_status="unknown",
        created_at=datetime.now(UTC),
    )


def _sample_experiment(target_threshold_id: str = "threshold-1") -> Experiment:
    return Experiment(
        id="experiment-1",
        title="14-day limited delivery pilot",
        objective="Validate repeat customer behavior before full capital commitment.",
        hypothesis=(
            "Customers who make an initial purchase will reorder at a rate sufficient to "
            "support the economic model."
        ),
        target_threshold_id=target_threshold_id,
        variable_to_test="Repeat-order rate",
        experiment_type=ExperimentType.PILOT,
        steps=["Run a small delivery pilot for 14 days.", "Track first and second orders."],
        success_criteria=["Repeat-order rate reaches or exceeds the target threshold."],
        failure_criteria=["Repeat-order rate remains below the target threshold."],
        duration_days=14,
        evidence_to_collect=["first orders", "second orders"],
        decision_rule="If the threshold is met, reassess. If missed, do not commit yet.",
        expected_information_gain=InformationGain.HIGH,
        confidence=0.7,
        feasibility=Feasibility.HIGH,
        reversibility=Reversibility.HIGH,
    )


# --- 1, 2, 3: consumes Threshold Analysis / Regret Simulation / assumptions -


def test_prompt_is_built_from_all_upstream_structured_output() -> None:
    """The prompt must be built from the structured DecisionAnalysis plus
    the already-persisted assumptions/blindspots/evidence findings/
    challenges/regret scenarios/thresholds, never from raw decision text."""
    analysis = _sample_decision_analysis()
    assumption = _sample_stored_assumption()
    blindspot = _sample_stored_blindspot()
    finding = _sample_stored_evidence_finding()
    challenge = _sample_stored_challenge()
    scenario = _sample_stored_regret_scenario()
    threshold = _sample_stored_threshold()

    prompt = build_experiment_planner_prompt(
        analysis, [assumption], [blindspot], [finding], [challenge], [scenario], [threshold]
    )

    assert analysis.decision_summary in prompt
    assert str(threshold.id) in prompt
    assert threshold.variable in prompt
    assert str(assumption.id) in prompt
    assert str(scenario.id) in prompt

    import inspect

    from app.agents.experiment_planner import build_experiment_planner_prompt as fn

    signature = inspect.signature(fn)
    assert list(signature.parameters) == [
        "decision_analysis",
        "assumptions",
        "blindspots",
        "evidence_findings",
        "challenges",
        "regret_scenarios",
        "thresholds",
    ]
    assert "decision" not in signature.parameters


def test_prompt_states_absence_of_thresholds_and_forbids_fabricating_one() -> None:
    analysis = _sample_decision_analysis()

    prompt = build_experiment_planner_prompt(analysis, [], [], [], [], [], [])

    assert "No thresholds have been recorded" in prompt
    assert "do not fabricate one" in prompt.lower()


# --- 4: produces valid ExperimentPlan ---------------------------------------


def test_experiment_schema_accepts_valid_data() -> None:
    experiment = _sample_experiment()

    plan = ExperimentPlan(
        experiments=[experiment], recommended_experiment_id="experiment-1", summary="x"
    )

    assert len(plan.experiments) == 1
    assert plan.experiments[0].experiment_type is ExperimentType.PILOT


def test_experiment_plan_can_have_empty_experiments() -> None:
    plan = ExperimentPlan(experiments=[], summary="Nothing to test yet.")

    assert plan.experiments == []
    assert plan.recommended_experiment_id is None


def test_experiment_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValidationError):
        Experiment(
            id="experiment-1",
            title="x",
            objective="x",
            hypothesis="x",
            target_threshold_id="threshold-1",
            variable_to_test="x",
            experiment_type=ExperimentType.SURVEY,
            decision_rule="x",
            expected_information_gain=InformationGain.LOW,
            confidence=1.5,  # out of the 0.0-1.0 range
            feasibility=Feasibility.LOW,
            reversibility=Reversibility.HIGH,
        )


# --- 5: every recommended experiment targets a meaningful uncertainty ------


def test_experiment_targets_a_real_threshold_id() -> None:
    threshold = _sample_stored_threshold()
    experiment = _sample_experiment(target_threshold_id=str(threshold.id))

    assert experiment.target_threshold_id == str(threshold.id)
    assert experiment.variable_to_test == threshold.variable


# --- 6: experiments reference real threshold ids ----------------------------


def test_system_prompt_requires_target_threshold_id_to_be_real() -> None:
    from app.agents.experiment_planner import SYSTEM_PROMPT

    assert "target_threshold_id" in SYSTEM_PROMPT
    assert "never invent one" in SYSTEM_PROMPT.lower()


# --- 7, 8: success/failure criteria are observable --------------------------


def test_experiment_success_and_failure_criteria_are_lists_of_observable_statements() -> None:
    experiment = _sample_experiment()

    assert experiment.success_criteria == [
        "Repeat-order rate reaches or exceeds the target threshold."
    ]
    assert experiment.failure_criteria == [
        "Repeat-order rate remains below the target threshold."
    ]


def test_system_prompt_forbids_vague_success_criteria() -> None:
    from app.agents.experiment_planner import SYSTEM_PROMPT

    assert "customers like the product" in SYSTEM_PROMPT.lower()
    assert "observable" in SYSTEM_PROMPT.lower()


# --- 9: decision rule exists --------------------------------------------------


def test_experiment_decision_rule_triggers_reevaluation_not_a_verdict() -> None:
    experiment = _sample_experiment()

    assert experiment.decision_rule
    lowered = experiment.decision_rule.lower()
    assert "the decision is good" not in lowered
    assert "the decision is bad" not in lowered


def test_system_prompt_forbids_unconditional_verdicts() -> None:
    from app.agents.experiment_planner import SYSTEM_PROMPT

    assert "never write" in SYSTEM_PROMPT.lower()


# --- 10, 11: no fabricated costs or durations --------------------------------


def test_experiment_cost_and_duration_can_be_null() -> None:
    experiment = _sample_experiment()
    unset = experiment.model_copy(update={"estimated_cost": None, "duration_days": None})

    assert unset.estimated_cost is None
    assert unset.duration_days is None


def test_system_prompt_forbids_fabricating_cost_or_duration() -> None:
    from app.agents.experiment_planner import SYSTEM_PROMPT

    assert "NEVER FABRICATE A COST OR DURATION" in SYSTEM_PROMPT


# --- 12: no fabricated statistics --------------------------------------------


def test_system_prompt_forbids_fabricating_statistics() -> None:
    from app.agents.experiment_planner import SYSTEM_PROMPT

    assert "never invent facts, statistics, costs, or durations" in SYSTEM_PROMPT.lower()


def test_system_prompt_forbids_generic_advice() -> None:
    from app.agents.experiment_planner import SYSTEM_PROMPT

    lowered = SYSTEM_PROMPT.lower()
    assert "talk to customers" in lowered
    assert "generic advice" in lowered


# --- 13: unknown values remain explicitly unknown ----------------------------


def test_experiment_can_represent_unknown_cost_and_duration_together() -> None:
    experiment = _sample_experiment().model_copy(
        update={"estimated_cost": None, "duration_days": None, "currency": None}
    )

    assert experiment.estimated_cost is None
    assert experiment.duration_days is None
    assert experiment.currency is None


# --- 14: high-impact uncertainty gets prioritized ----------------------------


def test_system_prompt_ranks_by_information_value_and_reversibility_not_cost_alone() -> None:
    from app.agents.experiment_planner import SYSTEM_PROMPT

    lowered = SYSTEM_PROMPT.lower()
    assert "not necessarily the lowest estimated_cost" in lowered


# --- 15: irreversible actions avoided when smaller tests exist --------------


def test_experiment_prefers_high_reversibility() -> None:
    experiment = _sample_experiment()

    assert experiment.reversibility is Reversibility.HIGH


def test_system_prompt_prefers_cheapest_credible_test() -> None:
    from app.agents.experiment_planner import SYSTEM_PROMPT

    assert "CHEAPEST CREDIBLE TEST" in SYSTEM_PROMPT
    assert "never recommend building the complete product" in SYSTEM_PROMPT.lower()
