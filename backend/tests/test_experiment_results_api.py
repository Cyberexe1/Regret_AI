"""API tests for experiment result submission/retrieval and the full
end-to-end validation loop.

Strands/LLM invocation for the analysis pipeline stages is mocked (see
`mock_decision_analyzer` etc. fixtures, mirrored from `test_analysis.py`)
so no real Bedrock call ever happens - the re-evaluation logic itself
(exercised through these endpoints) is fully deterministic Python and
needs no mocking.
"""

from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

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
    "description": "Considering a ₹5 lakh investment in a cloud kitchen.",
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
    real Bedrock call, producing a decision with one experiment targeting
    a real, validated threshold."""
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


def _analyzed_decision_and_experiment(client: TestClient) -> tuple[str, str]:
    decision_id = _create_decision(client)
    client.post(f"/api/v1/decisions/{decision_id}/analyze")
    experiments = client.get(f"/api/v1/decisions/{decision_id}/experiments").json()
    return decision_id, experiments[0]["id"]


# --- POST /experiments/{id}/results: valid submission ------------------------


def test_submit_experiment_result_success(client: TestClient) -> None:
    decision_id, experiment_id = _analyzed_decision_and_experiment(client)

    response = client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={
            "outcome": "failure",
            "summary": "18 of 100 customers reordered.",
            "observations": ["18 of 100 customers reordered."],
            "measured_values": {"Repeat-order rate": 18},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["experiment_id"] == experiment_id
    assert UUID(body["result_id"])
    assert UUID(body["reevaluation_id"])
    assert body["status"] == "completed"
    assert body["decision_assessment"] == "weakened"
    assert body["key_learning"]
    assert body["next_step"]


def test_submit_result_invalid_experiment_id_returns_404(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/experiments/{uuid4()}/results",
        json={"outcome": "success", "summary": "x"},
    )

    assert response.status_code == 404


def test_submit_result_requires_ownership(client: TestClient) -> None:
    decision_id, experiment_id = _analyzed_decision_and_experiment(client)

    from app.dependencies.auth import get_current_user_id
    from app.main import app

    app.dependency_overrides[get_current_user_id] = lambda: "someone-else"
    try:
        response = client.post(
            f"/api/v1/experiments/{experiment_id}/results",
            json={"outcome": "success", "summary": "x"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)

    assert response.status_code == 404


def test_submit_result_with_fabricated_evidence_id_returns_422(client: TestClient) -> None:
    _, experiment_id = _analyzed_decision_and_experiment(client)

    response = client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={
            "outcome": "success",
            "summary": "x",
            "evidence_ids": [str(uuid4())],
        },
    )

    assert response.status_code == 422


# --- Experiment becomes completed ---------------------------------------------


def test_experiment_status_becomes_completed_after_submission(client: TestClient) -> None:
    _, experiment_id = _analyzed_decision_and_experiment(client)

    client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={"outcome": "success", "summary": "x", "measured_values": {"Repeat-order rate": 30}},
    )

    response = client.get(f"/api/v1/experiments/{experiment_id}")
    assert response.json()["status"] == "completed"


def test_submitting_a_second_result_for_the_same_experiment_is_rejected(
    client: TestClient,
) -> None:
    """Concurrency protection (Step 12): once an experiment is completed,
    a second result submission (whether a genuine duplicate request or a
    concurrent race) must be rejected with 409, not silently accepted and
    never produce a second ReEvaluation record - see
    `ReEvaluationService.submit_result` and the conditional write in
    `DecisionRepository.update_experiment_status`."""
    _, experiment_id = _analyzed_decision_and_experiment(client)

    first = client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={
            "outcome": "success",
            "summary": "first",
            "measured_values": {"Repeat-order rate": 30},
        },
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={"outcome": "failure", "summary": "second"},
    )

    assert second.status_code == 409

    # Only the first result/re-evaluation exists - the rejected second
    # attempt never created anything.
    results = client.get(f"/api/v1/experiments/{experiment_id}/results").json()
    assert len(results) == 1
    assert results[0]["summary"] == "first"


# --- GET /experiments/{id}/results --------------------------------------------


def test_list_results_for_experiment(client: TestClient) -> None:
    _, experiment_id = _analyzed_decision_and_experiment(client)

    client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={"outcome": "failure", "summary": "x"},
    )

    response = client.get(f"/api/v1/experiments/{experiment_id}/results")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["outcome"] == "failure"


def test_list_results_for_decision(client: TestClient) -> None:
    decision_id, experiment_id = _analyzed_decision_and_experiment(client)

    client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={"outcome": "failure", "summary": "x"},
    )

    response = client.get(f"/api/v1/decisions/{decision_id}/experiment-results")

    assert response.status_code == 200
    assert len(response.json()) == 1


# --- End-to-end: Create -> Analyze -> Threshold -> Experiment -> Result -> ---
# --- Re-evaluate -> Retrieve Updated Assessment ------------------------------


def test_full_validation_loop_end_to_end(client: TestClient) -> None:
    decision_id, experiment_id = _analyzed_decision_and_experiment(client)

    # Threshold exists from analysis.
    thresholds = client.get(f"/api/v1/decisions/{decision_id}/experiments").json()
    assert thresholds[0]["target_threshold_id"]

    # Submit the experiment result.
    submit_response = client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={
            "outcome": "failure",
            "summary": "18 of 100 customers reordered within the pilot window.",
            "observations": ["18 of 100 first-time customers placed a second order."],
            "measured_values": {"Repeat-order rate": 18},
        },
    )
    assert submit_response.status_code == 201
    assert submit_response.json()["decision_assessment"] == "weakened"

    # The decision itself was never auto-approved/rejected.
    decision_response = client.get(f"/api/v1/decisions/{decision_id}")
    assert decision_response.json()["status"] == "needs_validation"

    # Retrieve the updated assessment via results listing.
    results = client.get(f"/api/v1/experiments/{experiment_id}/results").json()
    assert len(results) == 1
    assert results[0]["outcome"] == "failure"
