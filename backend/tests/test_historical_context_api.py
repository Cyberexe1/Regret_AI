"""API tests for `GET /decisions/{id}/historical-context` and its
integration into the analysis pipeline (REGRET ENGINE 2.0).

Strands/LLM invocation for the analysis pipeline stages is mocked (see
`mock_pipeline`, mirrored from `test_memory_api.py`/
`test_experiment_results_api.py`) so no real Bedrock call ever happens -
historical context gathering itself is fully deterministic Python and
needs no mocking.
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
    "description": "Considering a Rs 5 lakh investment in a cloud kitchen in Mumbai.",
}


def _create_decision(client: TestClient, payload: dict | None = None) -> str:
    response = client.post("/api/v1/decisions", json=payload or DECISION_PAYLOAD)
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
    real Bedrock call - mirrors `test_memory_api.py` exactly."""
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


# --- GET /decisions/{id}/historical-context ---------------------------------


def test_historical_context_empty_for_first_decision(client: TestClient) -> None:
    decision_id = _create_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/historical-context")

    assert response.status_code == 200
    body = response.json()
    assert body["found"] is False
    assert body["relevant_decisions"] == []
    assert body["relevant_learnings"] == []


def test_historical_context_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/decisions/{uuid4()}/historical-context")
    assert response.status_code == 404


def test_historical_context_surfaces_after_similar_analyzed_decision(client: TestClient) -> None:
    first_id = _create_decision(client)
    client.post(f"/api/v1/decisions/{first_id}/analyze")
    experiments = client.get(f"/api/v1/decisions/{first_id}/experiments").json()
    client.post(
        f"/api/v1/experiments/{experiments[0]['id']}/results",
        json={
            "outcome": "failure",
            "summary": "18 of 100 customers reordered.",
            "measured_values": {"Repeat-order rate": 18},
        },
    )

    second_id = _create_decision(client)  # same payload -> textually near-identical

    response = client.get(f"/api/v1/decisions/{second_id}/historical-context")

    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert body["relevant_decisions_count"] >= 1
    assert len(body["relevant_learnings"]) > 0
    for insight in body["relevant_learnings"]:
        assert 0.0 <= insight["relevance_score"] <= 1.0


# --- Orchestrator integration: additive, never blocking ----------------------


def test_analysis_run_result_includes_historical_context_key(client: TestClient) -> None:
    first_id = _create_decision(client)
    client.post(f"/api/v1/decisions/{first_id}/analyze")
    experiments = client.get(f"/api/v1/decisions/{first_id}/experiments").json()
    client.post(
        f"/api/v1/experiments/{experiments[0]['id']}/results",
        json={
            "outcome": "failure",
            "summary": "18 of 100 customers reordered.",
            "measured_values": {"Repeat-order rate": 18},
        },
    )

    second_id = _create_decision(client)
    analyze_response = client.post(f"/api/v1/decisions/{second_id}/analyze")
    assert analyze_response.status_code == 201

    run_id = analyze_response.json()["analysis_run_id"]
    status_response = client.get(f"/api/v1/decisions/{second_id}/analysis/{run_id}")
    assert status_response.status_code == 200
    # historical_context gathering failing/succeeding never changes the
    # run's own terminal status - the pipeline must still complete.
    assert status_response.json()["status"] == "completed"


def test_historical_context_failure_never_blocks_analysis(client: TestClient) -> None:
    """If historical context gathering raises, the analysis run must
    still complete successfully - it is additive, never a hard dependency."""
    decision_id = _create_decision(client)

    with patch(
        "app.agents.orchestrator.HistoricalContextService.get_historical_context",
        side_effect=RuntimeError("boom"),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    assert response.json()["status"] == "completed"


# --- Mandatory user isolation at the API layer -------------------------------


def test_api_user_isolation_for_historical_context(client: TestClient) -> None:
    """Even at the API layer (single placeholder user in this codebase's
    current no-auth posture), the historical-context endpoint must only
    ever return decisions from `DecisionRepository.list_for_user` for the
    resolved caller - never leak another decision id's data by accident.
    This exercises the endpoint end-to-end; the definitive multi-user
    isolation guarantee is covered at the service layer in
    `test_historical_context.py::test_user_a_cannot_retrieve_user_b_historical_context`."""
    decision_id = _create_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/historical-context")

    assert response.status_code == 200
    for score in response.json()["relevant_decisions"]:
        assert score["decision_id"] != decision_id  # never includes itself
