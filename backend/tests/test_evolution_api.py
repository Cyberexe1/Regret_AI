"""API tests for the Decision Evolution & Causal Timeline routes
(REGRET ENGINE 2.0, Step 22):

    GET /decisions/{id}/evolution
    GET /decisions/{id}/evolution/{event_id}
    GET /decisions/{id}/evolution/{event_id}/delta

Strands/LLM invocation for the analysis pipeline stages is mocked (see
`mock_pipeline`, mirrored from `test_adaptive_api.py`) so no real Bedrock
call ever happens - evolution assembly itself is fully deterministic
Python and needs no mocking.
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
    "budget": 500000,
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
                confidence=0.1,
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
                importance=ImportanceLevel.LOW,
                confidence=0.6,
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
                regret_level=SeverityLevel.CRITICAL,
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
                derivation=ThresholdDerivation.CALCULATED_FROM_EVIDENCE,
                consequence="Unit economics no longer hold below this level.",
                evidence_basis="Derived from the regret simulator's provisional threshold.",
                validation_status=ThresholdValidationStatus.VALIDATED,
            )
        ],
        primary_threshold_id="threshold-1",
        summary="Repeat-order rate must stay at or above 24%.",
    )


async def _experiment_plan_side_effect(
    decision_analysis,
    assumptions,
    blindspots,
    evidence_findings,
    challenges,
    regret_scenarios,
    thresholds,
    voi_analysis=None,
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
                estimated_cost=5000,
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
    real Bedrock call - mirrors `test_adaptive_api.py` exactly."""
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


# --- GET /decisions/{id}/evolution --------------------------------------------


def test_get_evolution_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/decisions/{uuid4()}/evolution")
    assert response.status_code == 404


def test_get_evolution_for_a_bare_decision_returns_only_decision_created(
    client: TestClient,
) -> None:
    decision_id = _create_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/evolution")

    assert response.status_code == 200
    body = response.json()
    assert len(body["timeline"]) == 1
    assert body["timeline"][0]["event_type"] == "decision_created"
    assert body["decision_id"] == decision_id
    assert body["total_cycles"] == 0
    assert body["truncated"] is False


def test_get_evolution_after_analysis_includes_analysis_stage_events(client: TestClient) -> None:
    decision_id, _ = _analyzed_decision_and_experiment(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/evolution")

    assert response.status_code == 200
    types = {event["event_type"] for event in response.json()["timeline"]}
    assert "assumption_identified" in types
    assert "threshold_identified" in types
    assert "experiment_recommended" in types


def test_get_evolution_after_experiment_result_shows_assessment_change(client: TestClient) -> None:
    decision_id, experiment_id = _analyzed_decision_and_experiment(client)

    submit_response = client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={
            "outcome": "success",
            "summary": "35 of 100 customers reordered.",
            "measured_values": {"Repeat-order rate": 35},
        },
    )
    assert submit_response.status_code == 201

    response = client.get(f"/api/v1/decisions/{decision_id}/evolution")
    body = response.json()
    types = {event["event_type"] for event in body["timeline"]}

    assert "experiment_result" in types
    assert "re_evaluation" in types
    assert body["current_assessment"] != "insufficient_evidence"


# --- MANDATORY: supported -> weakened via the API -------------------------------


def test_mandatory_supported_to_weakened_transition_is_exposed_via_api(client: TestClient) -> None:
    """MANDATORY (spec section 23): when an experiment causes the
    decision's assessment to move from supported to weakened, the
    evolution API must expose the correct previous_state, new_state,
    source, and reason."""
    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    decision_id, experiment_id = _analyzed_decision_and_experiment(client)
    decision_repo = DecisionRepository()

    # First: a strong result strengthens the decision.
    first_submit = client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={
            "outcome": "success",
            "summary": "Strong initial signal.",
            "measured_values": {"Repeat-order rate": 35},
        },
    )
    assert first_submit.status_code == 201

    # Seed a second threshold + experiment targeting the same assumption
    # so a second real re-evaluation can move the assessment the other way.
    assumptions = decision_repo.list_assumptions(_UUID(decision_id))
    assumption_id = str(assumptions[0].id)
    threshold_2 = decision_repo.create_thresholds(
        _UUID(decision_id),
        [
            {
                "variable": "Repeat-order rate",
                "validation_status": "validated",
                "derivation": "calculated_from_evidence",
                "threshold_value": "24",
                "direction": "below",
                "related_assumption_ids": [assumption_id],
            }
        ],
    )[0]
    experiment_2 = decision_repo.create_experiments(
        _UUID(decision_id),
        [
            {
                "title": "Second repeat-order check",
                "hypothesis": "Repeat ordering holds over a longer window.",
                "target_threshold_id": str(threshold_2.id),
                "decision_rule": "x",
                "feasibility": "high",
                "reversibility": "high",
                "estimated_cost": 500,
            }
        ],
    )[0]

    second_submit = client.post(
        f"/api/v1/experiments/{experiment_2.id}/results",
        json={
            "outcome": "failure",
            "summary": "Repeat orders dropped sharply.",
            "measured_values": {"Repeat-order rate": 10},
        },
    )
    assert second_submit.status_code == 201
    reevaluation_id = second_submit.json()["reevaluation_id"]

    evolution = client.get(f"/api/v1/decisions/{decision_id}/evolution").json()
    assessment_changed_events = [
        e for e in evolution["timeline"] if e["event_type"] == "assessment_changed"
    ]
    matching = [e for e in assessment_changed_events if e["source_id"] == reevaluation_id]
    assert len(matching) == 1
    event = matching[0]

    assert event["previous_state"] is not None
    assert event["new_state"] is not None
    assert event["previous_state"] != event["new_state"]
    assert event["source_type"] == "re_evaluation"
    assert event["source_id"] == reevaluation_id
    assert event["reason"] is not None

    # Also confirmed via the dedicated event-detail endpoint.
    detail = client.get(f"/api/v1/decisions/{decision_id}/evolution/{event['event_id']}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["previous_state"] == event["previous_state"]
    assert detail_body["new_state"] == event["new_state"]

    # And via the decision-delta endpoint.
    delta = client.get(f"/api/v1/decisions/{decision_id}/evolution/{event['event_id']}/delta")
    assert delta.status_code == 200
    assert delta.json()["assessment_changed"] is True


# --- GET /decisions/{id}/evolution/{event_id} -----------------------------------


def test_get_evolution_event_unknown_event_id_returns_404(client: TestClient) -> None:
    decision_id = _create_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/evolution/not-a-real-event")

    assert response.status_code == 404


def test_get_evolution_event_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/decisions/{uuid4()}/evolution/some-event")
    assert response.status_code == 404


def test_get_evolution_event_returns_full_detail_for_a_real_event(client: TestClient) -> None:
    decision_id = _create_decision(client)
    evolution = client.get(f"/api/v1/decisions/{decision_id}/evolution").json()
    event_id = evolution["timeline"][0]["event_id"]

    response = client.get(f"/api/v1/decisions/{decision_id}/evolution/{event_id}")

    assert response.status_code == 200
    assert response.json()["event_id"] == event_id


# --- GET /decisions/{id}/evolution/{event_id}/delta ------------------------------


def test_get_evolution_delta_unknown_event_id_returns_404(client: TestClient) -> None:
    decision_id = _create_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/evolution/not-a-real-event/delta")

    assert response.status_code == 404


def test_get_evolution_delta_for_decision_created_shows_no_meaningful_change(
    client: TestClient,
) -> None:
    decision_id = _create_decision(client)
    evolution = client.get(f"/api/v1/decisions/{decision_id}/evolution").json()
    event_id = evolution["timeline"][0]["event_id"]

    response = client.get(f"/api/v1/decisions/{decision_id}/evolution/{event_id}/delta")

    assert response.status_code == 200
    body = response.json()
    assert body["changed"] is False
    assert body["assessment_changed"] is False


# --- Response shape / no chain-of-thought / no secrets --------------------------


def test_evolution_response_never_exposes_internal_fields(client: TestClient) -> None:
    decision_id, _ = _analyzed_decision_and_experiment(client)

    body = client.get(f"/api/v1/decisions/{decision_id}/evolution").json()

    serialized = str(body)
    for forbidden in ("chain_of_thought", "system_prompt", "aws_secret", "bedrock_api_key"):
        assert forbidden not in serialized


def test_evolution_is_bounded_by_a_single_call_no_per_event_fetch_required(
    client: TestClient,
) -> None:
    """The full timeline, current state, and major changes all come back
    from ONE call - the frontend never needs a per-event API call to
    render the whole section (spec section 22's performance requirement)."""
    decision_id, _ = _analyzed_decision_and_experiment(client)

    body = client.get(f"/api/v1/decisions/{decision_id}/evolution").json()

    assert "timeline" in body
    assert "major_changes" in body
    assert "current_assessment" in body
    assert "current_uncertainties" in body
