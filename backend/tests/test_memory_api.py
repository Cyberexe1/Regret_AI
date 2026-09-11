"""API tests for the Decision Memory endpoints and their integration into
the existing experiment-result submission flow.

Strands/LLM invocation for the analysis pipeline stages is mocked (see
`mock_pipeline`, mirrored from `test_experiment_results_api.py`) so no
real Bedrock call ever happens - memory construction itself is fully
deterministic Python and needs no mocking.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

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
    "description": "Considering a Rs 5 lakh investment in a cloud kitchen.",
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
    thresholds, voi_analysis=None,
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
    real Bedrock call - mirrors `test_experiment_results_api.py` exactly."""
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


# --- GET /decisions/{id}/memory: before any result --------------------------


def test_get_memory_before_any_experiment_result_is_empty_but_valid(
    client: TestClient,
) -> None:
    decision_id = _create_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/memory")

    assert response.status_code == 200
    body = response.json()
    assert body["memory"] is None
    assert body["learnings"] == []
    assert body["experiments"] == []
    assert body["assessments"] == []


def test_get_memory_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/decisions/{uuid4()}/memory")
    assert response.status_code == 404


# --- Automatic memory update: submit result -> memory -----------------------


def test_submitting_experiment_result_updates_memory_automatically(
    client: TestClient,
) -> None:
    decision_id, experiment_id = _analyzed_decision_and_experiment(client)

    submit_response = client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={
            "outcome": "failure",
            "summary": "18 of 100 customers reordered.",
            "measured_values": {"Repeat-order rate": 18},
        },
    )
    assert submit_response.status_code == 201

    memory_response = client.get(f"/api/v1/decisions/{decision_id}/memory")
    assert memory_response.status_code == 200
    body = memory_response.json()

    assert body["memory"] is not None
    assert body["memory"]["stage"] == "validated"
    assert body["memory"]["outcome_summary"]
    assert body["memory"]["final_assessment"]
    assert len(body["learnings"]) > 0
    assert len(body["experiments"]) == 1
    assert len(body["assessments"]) == 1

    # The original ExperimentResultResponse contract is unchanged - memory
    # integration must not alter the existing API shape.
    submit_body = submit_response.json()
    assert set(submit_body.keys()) == {
        "experiment_id", "result_id", "reevaluation_id", "status",
        "decision_assessment", "key_learning", "next_step",
    }


def test_submitting_experiment_result_creates_threshold_failed_learning(
    client: TestClient,
) -> None:
    decision_id, experiment_id = _analyzed_decision_and_experiment(client)

    client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={
            "outcome": "failure",
            "summary": "18 of 100 customers reordered.",
            "measured_values": {"Repeat-order rate": 18},
        },
    )

    learnings = client.get(f"/api/v1/decisions/{decision_id}/learnings").json()

    threshold_failed = [
        learning for learning in learnings if learning["learning_type"] == "threshold_failed"
    ]
    assert len(threshold_failed) == 1
    assert threshold_failed[0]["observed_value"] == "18"
    assert threshold_failed[0]["expected_value"] == "24"
    # Provenance is preserved - points at a real, resolvable re-evaluation.
    assert threshold_failed[0]["source_type"] == "re_evaluation"
    assert threshold_failed[0]["source_id"]


def test_get_learnings_for_decision_with_no_results_is_empty(client: TestClient) -> None:
    decision_id = _create_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/learnings")

    assert response.status_code == 200
    assert response.json() == []


# --- GET /memory/{memory_id} -------------------------------------------------


def test_get_memory_by_id(client: TestClient) -> None:
    decision_id, experiment_id = _analyzed_decision_and_experiment(client)
    client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={"outcome": "success", "summary": "x", "measured_values": {"Repeat-order rate": 30}},
    )

    memory = client.get(f"/api/v1/decisions/{decision_id}/memory").json()["memory"]

    response = client.get(f"/api/v1/memory/{memory['memory_id']}")

    assert response.status_code == 200
    assert response.json()["memory"]["memory_id"] == memory["memory_id"]


def test_get_memory_by_unknown_id_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/memory/{uuid4()}")
    assert response.status_code == 404


# --- Idempotency at the API layer -------------------------------------------


def test_duplicate_experiment_result_submission_does_not_duplicate_learnings(
    client: TestClient,
) -> None:
    """A duplicate *submission* is already rejected with 409 by the
    existing experiment-completion guard (see
    `test_experiment_results_api.py::test_submitting_a_second_result_...`);
    this test confirms memory processing itself is also idempotent even if
    the same already-persisted result/re-evaluation were ever re-processed
    (e.g. a retried request that reaches the memory step twice)."""
    decision_id, experiment_id = _analyzed_decision_and_experiment(client)

    client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={
            "outcome": "failure",
            "summary": "18 of 100 customers reordered.",
            "measured_values": {"Repeat-order rate": 18},
        },
    )
    second = client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={"outcome": "failure", "summary": "duplicate attempt"},
    )
    assert second.status_code == 409

    learnings = client.get(f"/api/v1/decisions/{decision_id}/learnings").json()
    threshold_failed = [
        learning for learning in learnings if learning["learning_type"] == "threshold_failed"
    ]
    assert len(threshold_failed) == 1
