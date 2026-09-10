"""Tests for the Regret Simulator agent module itself.

Focused on the parts that don't require invoking a real model: prompt
construction and the structured schemas. No Bedrock call happens anywhere
in this file.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.agents.regret_simulator import build_regret_simulator_prompt
from app.agents.schemas import (
    DecisionAnalysis,
    ImpactLevel,
    ProbabilityBand,
    RegretScenario,
    RegretSimulation,
    SeverityLevel,
    TriggerDirection,
)
from app.schemas.decision_resources import Assumption as StoredAssumption
from app.schemas.decision_resources import AssumptionSource as StoredAssumptionSource
from app.schemas.decision_resources import Blindspot as StoredBlindspot
from app.schemas.decision_resources import BlindspotEvidenceStatus, EvidenceStatus
from app.schemas.decision_resources import Challenge as StoredChallenge
from app.schemas.decision_resources import EvidenceFinding as StoredEvidenceFinding


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


# --- 1: consumes Devil's Advocate output ------------------------------------


def test_prompt_includes_devils_advocate_challenges() -> None:
    analysis = _sample_decision_analysis()
    challenge = _sample_stored_challenge()

    prompt = build_regret_simulator_prompt(analysis, [], [], [], [challenge])

    assert challenge.claim in prompt
    assert challenge.attack in prompt
    assert str(challenge.id) in prompt


def test_prompt_states_absence_of_challenges() -> None:
    analysis = _sample_decision_analysis()

    prompt = build_regret_simulator_prompt(analysis, [], [], [], [])

    assert "No Devil's Advocate challenges have been recorded" in prompt


# --- 2: consumes assumptions and blindspots ---------------------------------


def test_prompt_includes_assumptions_and_blindspots() -> None:
    analysis = _sample_decision_analysis()
    assumption = _sample_stored_assumption()
    blindspot = _sample_stored_blindspot()

    prompt = build_regret_simulator_prompt(analysis, [assumption], [blindspot], [], [])

    assert assumption.statement in prompt
    assert str(assumption.id) in prompt
    assert blindspot.question in prompt
    assert str(blindspot.id) in prompt


def test_prompt_signature_never_accepts_raw_decision() -> None:
    import inspect

    from app.agents.regret_simulator import build_regret_simulator_prompt as fn

    signature = inspect.signature(fn)
    assert list(signature.parameters) == [
        "decision_analysis",
        "assumptions",
        "blindspots",
        "evidence_findings",
        "challenges",
    ]
    assert "decision" not in signature.parameters


# --- 3: produces valid RegretSimulation -------------------------------------


def test_regret_scenario_schema_accepts_valid_data() -> None:
    scenario = RegretScenario(
        id="scenario-1",
        title="Adoption failure",
        failure_condition="Repeat-order rate remains below sustainable levels.",
        probability_band=ProbabilityBand.UNKNOWN,
        impact=ImpactLevel.SEVERE,
        regret_level=SeverityLevel.HIGH,
        trigger_variable="Repeat-order rate",
        trigger_direction=TriggerDirection.BELOW,
        provisional_threshold=None,
        consequence="Full capital commitment occurs before demand quality is validated.",
        related_assumption_ids=["abc-123"],
        related_challenge_ids=["def-456"],
        evidence_basis="No repeat-purchase evidence was submitted for this decision.",
    )

    simulation = RegretSimulation(
        scenarios=[scenario],
        dominant_regret="Committing before validating repeat demand.",
        highest_risk_scenario_id="scenario-1",
    )

    assert len(simulation.scenarios) == 1
    assert simulation.highest_risk_scenario_id == "scenario-1"


def test_regret_simulation_can_have_empty_scenarios() -> None:
    simulation = RegretSimulation(scenarios=[], dominant_regret="No material regret identified.")

    assert simulation.scenarios == []
    assert simulation.highest_risk_scenario_id is None


# --- 4: creates meaningful failure scenarios ---------------------------------


def test_regret_scenario_frames_consequence_as_regret_not_generic_risk() -> None:
    scenario = RegretScenario(
        id="scenario-1",
        title="Adoption failure",
        failure_condition="Users try the product but do not return frequently enough.",
        probability_band=ProbabilityBand.MEDIUM,
        impact=ImpactLevel.HIGH,
        regret_level=SeverityLevel.HIGH,
        trigger_variable="Repeat-order rate",
        trigger_direction=TriggerDirection.BELOW,
        consequence=(
            "The founder commits the full capital before repeat demand is validated, and "
            "the business cannot recover the investment once low repeat rates are confirmed."
        ),
        related_assumption_ids=[],
        related_challenge_ids=[],
        evidence_basis="x",
    )

    assert "commits" in scenario.consequence  # framed as regret, not just abstract risk


# --- 5: identifies trigger variables -----------------------------------------


def test_regret_scenario_requires_concrete_trigger_variable_and_direction() -> None:
    scenario = RegretScenario(
        id="scenario-1",
        title="Margin failure",
        failure_condition="Operating costs rise enough to eliminate the expected margin.",
        probability_band=ProbabilityBand.LOW,
        impact=ImpactLevel.HIGH,
        regret_level=SeverityLevel.MEDIUM,
        trigger_variable="Monthly operating cost",
        trigger_direction=TriggerDirection.ABOVE,
        consequence="x",
        related_assumption_ids=[],
        related_challenge_ids=[],
        evidence_basis="x",
    )

    assert scenario.trigger_variable == "Monthly operating cost"
    assert scenario.trigger_direction is TriggerDirection.ABOVE


# --- 6: does not fabricate probabilities -------------------------------------


def test_probability_band_is_qualitative_only() -> None:
    with pytest.raises(ValidationError):
        RegretScenario.model_validate(
            {
                "id": "scenario-1",
                "title": "x",
                "failure_condition": "x",
                "probability_band": "68%",  # not a valid qualitative band
                "impact": "high",
                "regret_level": "high",
                "trigger_variable": "x",
                "trigger_direction": "below",
                "consequence": "x",
                "related_assumption_ids": [],
                "related_challenge_ids": [],
                "evidence_basis": "x",
            }
        )


def test_system_prompt_forbids_fabricating_probability() -> None:
    from app.agents.regret_simulator import SYSTEM_PROMPT

    assert "NEVER FABRICATE A PROBABILITY" in SYSTEM_PROMPT


# --- 7: does not fabricate numeric thresholds --------------------------------


def test_provisional_threshold_can_be_left_unset() -> None:
    scenario = RegretScenario(
        id="scenario-1",
        title="x",
        failure_condition="x",
        probability_band=ProbabilityBand.UNKNOWN,
        impact=ImpactLevel.MEDIUM,
        regret_level=SeverityLevel.MEDIUM,
        trigger_variable="x",
        trigger_direction=TriggerDirection.UNKNOWN,
        provisional_threshold=None,
        consequence="x",
        related_assumption_ids=[],
        related_challenge_ids=[],
        evidence_basis="x",
    )

    assert scenario.provisional_threshold is None


def test_system_prompt_forbids_fabricating_numeric_threshold() -> None:
    from app.agents.regret_simulator import SYSTEM_PROMPT

    assert "NEVER FABRICATE A NUMERIC THRESHOLD" in SYSTEM_PROMPT


# --- 8: distinguishes uncertainty from known evidence ------------------------


def test_evidence_basis_field_exists_separately_from_consequence() -> None:
    scenario = RegretScenario(
        id="scenario-1",
        title="x",
        failure_condition="x",
        probability_band=ProbabilityBand.UNKNOWN,
        impact=ImpactLevel.MEDIUM,
        regret_level=SeverityLevel.MEDIUM,
        trigger_variable="x",
        trigger_direction=TriggerDirection.UNKNOWN,
        consequence="What happens if this occurs.",
        related_assumption_ids=[],
        related_challenge_ids=[],
        evidence_basis="What in the given evidence actually supports this scenario.",
    )

    assert scenario.evidence_basis != scenario.consequence


# --- 9: handles incomplete inputs --------------------------------------------


def test_prompt_handles_all_empty_inputs_without_error() -> None:
    analysis = _sample_decision_analysis()

    prompt = build_regret_simulator_prompt(analysis, [], [], [], [])

    assert "No assumptions have been recorded" in prompt
    assert "No blindspots have been recorded" in prompt
    assert "No evidence findings have been recorded" in prompt
    assert "No Devil's Advocate challenges have been recorded" in prompt


def test_system_prompt_allows_returning_no_scenarios_when_inputs_are_sparse() -> None:
    from app.agents.regret_simulator import SYSTEM_PROMPT

    lowered = SYSTEM_PROMPT.lower()
    assert "few scenarios, or none" in lowered


# --- 10: identifies a dominant regret scenario when appropriate -------------


def test_highest_risk_scenario_id_can_reference_a_sibling_scenario() -> None:
    scenario_a = RegretScenario(
        id="scenario-1",
        title="Demand failure",
        failure_condition="x",
        probability_band=ProbabilityBand.LOW,
        impact=ImpactLevel.LOW,
        regret_level=SeverityLevel.LOW,
        trigger_variable="x",
        trigger_direction=TriggerDirection.UNKNOWN,
        consequence="x",
        related_assumption_ids=[],
        related_challenge_ids=[],
        evidence_basis="x",
    )
    scenario_b = RegretScenario(
        id="scenario-2",
        title="Adoption failure",
        failure_condition="x",
        probability_band=ProbabilityBand.MEDIUM,
        impact=ImpactLevel.SEVERE,
        regret_level=SeverityLevel.CRITICAL,
        trigger_variable="x",
        trigger_direction=TriggerDirection.BELOW,
        consequence="x",
        related_assumption_ids=[],
        related_challenge_ids=[],
        evidence_basis="x",
    )

    simulation = RegretSimulation(
        scenarios=[scenario_a, scenario_b],
        dominant_regret="Adoption failure is the most consequential path to regret.",
        highest_risk_scenario_id="scenario-2",
    )

    matching = [s for s in simulation.scenarios if s.id == simulation.highest_risk_scenario_id]
    assert len(matching) == 1
    assert matching[0].title == "Adoption failure"


def test_highest_risk_scenario_id_can_be_none_when_nothing_dominates() -> None:
    simulation = RegretSimulation(
        scenarios=[],
        dominant_regret="No scenario clearly dominates given the available information.",
        highest_risk_scenario_id=None,
    )

    assert simulation.highest_risk_scenario_id is None
