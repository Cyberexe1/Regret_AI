"""Tests for the read-only analysis child-entity routes added for frontend
integration (Step 13): assumptions, blindspots, evidence findings,
challenges, regret scenarios, thresholds, and re-evaluations.

Mirrors the mocked-pipeline pattern from `test_experiment_results_api.py`
so a full, real set of persisted entities exists to read back. No real
Bedrock call ever happens - every agent call site is patched.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.schemas import (
    Assumption,
    AssumptionAnalysis,
    AssumptionEvidenceStatus,
    AssumptionFinding,
    AssumptionSource,
    BlindspotAnalysis,
    BlindspotCategory,
    BlindspotEvidenceStatus,
    BlindspotFinding,
    Challenge,
    ConfidenceLevel,
    DecisionAnalysis,
    DevilAdvocateAnalysis,
    EvidenceAnalysis,
    Experiment,
    ExperimentPlan,
    ExperimentPlanStatus,
    ExperimentType,
    Feasibility,
    ImpactLevel,
    ImportanceLevel,
    InformationClassification,
    InformationGain,
    ProbabilityBand,
    RegretScenario,
    RegretSimulation,
    Reversibility,
    SeverityLevel,
    Threshold,
    ThresholdAnalysis,
    ThresholdDerivation,
    ThresholdDirection,
    ThresholdType,
    ThresholdValidationStatus,
    TriggerDirection,
)

DECISION_PAYLOAD = {
    "title": "Open a cloud kitchen",
    "description": "Considering a capital investment in a cloud kitchen.",
}


def _create_decision(client: TestClient) -> str:
    response = client.post("/api/v1/decisions", json=DECISION_PAYLOAD)
    assert response.status_code == 201
    return response.json()["id"]


def _sample_analysis() -> DecisionAnalysis:
    return DecisionAnalysis(
        decision_summary="Whether to open a cloud kitchen.",
        decision_type="market entry",
        goal="Validate demand before full capital commitment.",
        constraints=["Limited capital"],
        success_criteria=["Breaks even within 12 months"],
        key_variables=["Repeat-order rate"],
        initial_assumptions=[
            Assumption(
                statement="Repeat customers will sustain unit economics.",
                importance=ImportanceLevel.HIGH,
                confidence=ConfidenceLevel.MEDIUM,
                classification=InformationClassification.ASSUMPTION,
                reason="No repeat-purchase evidence was submitted.",
            )
        ],
        unknowns=["Actual repeat-order rate was not provided."],
    )


def _sample_assumption_analysis() -> AssumptionAnalysis:
    return AssumptionAnalysis(
        assumptions=[
            AssumptionFinding(
                statement="Repeat customers will sustain unit economics.",
                source=AssumptionSource.IMPLICIT,
                importance=ImportanceLevel.CRITICAL,
                confidence=0.4,
                evidence_status=AssumptionEvidenceStatus.NOT_ADDRESSED,
                dependency="Business profitability",
                failure_consequence="Revenue falls short of required margin.",
            )
        ]
    )


def _sample_blindspot_analysis() -> BlindspotAnalysis:
    return BlindspotAnalysis(
        blindspots=[
            BlindspotFinding(
                question="What happens if repeat orders fall below 24%?",
                category=BlindspotCategory.UNTESTED_ASSUMPTION,
                importance=ImportanceLevel.CRITICAL,
                confidence=0.7,
                evidence_status=BlindspotEvidenceStatus.NOT_ADDRESSED,
                related_assumption_ids=[],
                why_it_matters="Repeat order rate drives whether the kitchen breaks even.",
            )
        ]
    )


def _sample_devil_advocate_analysis() -> DevilAdvocateAnalysis:
    return DevilAdvocateAnalysis(
        overall_challenge="The business case assumes repeat customers without validating them.",
        challenges=[
            Challenge(
                claim="Repeat customers will sustain unit economics.",
                attack="Only initial demand has been established, not repeat behavior.",
                severity=SeverityLevel.CRITICAL,
                confidence=0.7,
                failure_mechanism="If repeat ordering stays low, unit economics fail.",
                evidence_basis="No submitted evidence addresses repeat-purchase behavior.",
            )
        ],
    )


def _sample_regret_simulation() -> RegretSimulation:
    return RegretSimulation(
        scenarios=[
            RegretScenario(
                id="scenario-1",
                title="Adoption failure",
                failure_condition="Repeat-order rate remains below sustainable levels.",
                probability_band=ProbabilityBand.UNKNOWN,
                impact=ImpactLevel.SEVERE,
                regret_level=SeverityLevel.HIGH,
                trigger_variable="Repeat-order rate",
                trigger_direction=TriggerDirection.BELOW,
                consequence="Full capital commitment before demand is validated.",
                evidence_basis="No repeat-purchase evidence was submitted.",
            )
        ],
        dominant_regret="Committing before validating repeat demand.",
        highest_risk_scenario_id="scenario-1",
    )


def _sample_threshold_analysis() -> ThresholdAnalysis:
    return ThresholdAnalysis(
        thresholds=[
            Threshold(
                id="threshold-1",
                variable="Repeat-order rate",
                threshold_type=ThresholdType.NUMERIC,
                direction=ThresholdDirection.BELOW,
                threshold_value="24",
                unit="%",
                confidence=0.7,
                derivation=ThresholdDerivation.DERIVED_FROM_EXISTING_ANALYSIS,
                consequence="Unit economics no longer hold below this level.",
                evidence_basis="Derived from the regret simulator's provisional threshold.",
                validation_status=ThresholdValidationStatus.VALIDATED,
            )
        ],
        primary_threshold_id="threshold-1",
        summary="Repeat-order rate must stay at or above 24%.",
    )


async def _experiment_plan_side_effect(
    decision_analysis, assumptions, blindspots, evidence_findings, challenges, regret_scenarios,
    thresholds,
):
    target_id = str(thresholds[0].id) if thresholds else "threshold-1"
    return ExperimentPlan(
        experiments=[
            Experiment(
                id="experiment-1",
                title="14-day limited delivery pilot",
                objective="Validate repeat customer behavior before full commitment.",
                hypothesis="Customers will reorder at a sufficient rate.",
                target_threshold_id=target_id,
                variable_to_test="Repeat-order rate",
                experiment_type=ExperimentType.PILOT,
                steps=["Run a small delivery pilot for 14 days."],
                success_criteria=["Repeat-order rate reaches or exceeds the target threshold."],
                failure_criteria=["Repeat-order rate remains below the target threshold."],
                duration_days=14,
                evidence_to_collect=["first orders", "second orders"],
                decision_rule="If met, reassess. If missed, do not commit yet.",
                expected_information_gain=InformationGain.HIGH,
                confidence=0.7,
                feasibility=Feasibility.HIGH,
                reversibility=Reversibility.HIGH,
                status=ExperimentPlanStatus.RECOMMENDED,
            )
        ],
        recommended_experiment_id="experiment-1",
        summary="Run a 14-day pilot before committing the full investment.",
    )


@pytest.fixture(autouse=True)
def mock_pipeline():
    """Patch every agent call site so the full pipeline runs without any
    real Bedrock call, producing a decision with persisted assumptions,
    blindspots, evidence findings, challenges, regret scenarios,
    thresholds, and one experiment."""
    with (
        patch(
            "app.agents.orchestrator.run_decision_analyzer",
            new=AsyncMock(return_value=_sample_analysis()),
        ),
        patch(
            "app.agents.orchestrator.run_assumption_hunter",
            new=AsyncMock(return_value=_sample_assumption_analysis()),
        ),
        patch(
            "app.agents.orchestrator.run_blindspot_hunter",
            new=AsyncMock(return_value=_sample_blindspot_analysis()),
        ),
        patch(
            "app.agents.orchestrator.run_evidence_agent",
            new=AsyncMock(return_value=EvidenceAnalysis(findings=[])),
        ),
        patch(
            "app.agents.orchestrator.run_devils_advocate",
            new=AsyncMock(return_value=_sample_devil_advocate_analysis()),
        ),
        patch(
            "app.agents.orchestrator.run_regret_simulator",
            new=AsyncMock(return_value=_sample_regret_simulation()),
        ),
        patch(
            "app.agents.orchestrator.run_threshold_engine",
            new=AsyncMock(return_value=_sample_threshold_analysis()),
        ),
        patch(
            "app.agents.orchestrator.run_experiment_planner",
            new=AsyncMock(side_effect=_experiment_plan_side_effect),
        ),
    ):
        yield


def _analyzed_decision(client: TestClient) -> str:
    decision_id = _create_decision(client)
    response = client.post(f"/api/v1/decisions/{decision_id}/analyze")
    assert response.json()["status"] == "completed"
    return decision_id


# --- Happy path: every entity is readable after a completed analysis ----------


def test_list_assumptions_returns_persisted_assumptions(client: TestClient) -> None:
    decision_id = _analyzed_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/assumptions")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["statement"] == "Repeat customers will sustain unit economics."
    assert body[0]["decision_id"] == decision_id


def test_list_blindspots_returns_persisted_blindspots(client: TestClient) -> None:
    decision_id = _analyzed_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/blindspots")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert "repeat orders" in body[0]["question"]


def test_list_evidence_findings_empty_when_no_findings(client: TestClient) -> None:
    decision_id = _analyzed_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/evidence-findings")

    assert response.status_code == 200
    assert response.json() == []


def test_list_challenges_returns_persisted_challenges(client: TestClient) -> None:
    decision_id = _analyzed_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/challenges")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["claim"] == "Repeat customers will sustain unit economics."


def test_list_regret_scenarios_returns_persisted_scenarios(client: TestClient) -> None:
    decision_id = _analyzed_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/regret-scenarios")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Adoption failure"
    # Fresh, real persisted id - never the agent's response-scoped "scenario-1" label.
    assert body[0]["id"] != "scenario-1"


def test_list_thresholds_returns_persisted_thresholds(client: TestClient) -> None:
    decision_id = _analyzed_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/thresholds")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["variable"] == "Repeat-order rate"
    assert body[0]["validation_status"] == "validated"
    assert body[0]["threshold_value"] == "24"


def test_list_reevaluations_empty_before_any_experiment_result(client: TestClient) -> None:
    decision_id = _analyzed_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/reevaluations")

    assert response.status_code == 200
    assert response.json() == []


def test_list_reevaluations_returns_result_after_submission(client: TestClient) -> None:
    decision_id = _analyzed_decision(client)
    experiments = client.get(f"/api/v1/decisions/{decision_id}/experiments").json()
    experiment_id = experiments[0]["id"]

    client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={
            "outcome": "failure",
            "summary": "18 of 100 customers reordered.",
            "measured_values": {"Repeat-order rate": 18},
        },
    )

    response = client.get(f"/api/v1/decisions/{decision_id}/reevaluations")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["decision_assessment"]["status"] == "weakened"


# --- Empty states and ownership -------------------------------------------------


def test_list_assumptions_empty_for_decision_with_no_analysis(client: TestClient) -> None:
    decision_id = _create_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/assumptions")

    assert response.status_code == 200
    assert response.json() == []


def test_list_assumptions_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/decisions/00000000-0000-0000-0000-000000000000/assumptions")

    assert response.status_code == 404


def test_list_thresholds_requires_ownership(client: TestClient) -> None:
    decision_id = _analyzed_decision(client)

    from app.dependencies.auth import get_current_user_id
    from app.main import app

    app.dependency_overrides[get_current_user_id] = lambda: "someone-else"
    try:
        response = client.get(f"/api/v1/decisions/{decision_id}/thresholds")
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)

    assert response.status_code == 404
