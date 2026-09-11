"""API tests for the Adaptive Experiment Loop routes (REGRET ENGINE 2.0,
Step 21):

    GET  /decisions/{id}/adaptive
    GET  /decisions/{id}/adaptive/history
    POST /decisions/{id}/adaptive/advance
    POST /decisions/{id}/adaptive/stop

Also covers the experiment-result-submission integration
(`AdaptiveExperimentService.mark_experiment_completed` being called from
`POST /experiments/{id}/results`) and user isolation at the API layer.

Strands/LLM invocation for the analysis pipeline stages is mocked (see
`mock_pipeline`, mirrored from `test_value_of_information_api.py`) so no
real Bedrock call ever happens.
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
    real Bedrock call - mirrors `test_value_of_information_api.py` exactly."""
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
    """Analyzes a decision and returns `(decision_id, experiment_id)`.

    The mocked pipeline in this file (mirroring
    `test_value_of_information_api.py`'s own mock) doesn't cross-reference
    the threshold back to the assumption via `related_assumption_ids`, so
    VOI can't link its primary uncertainty to a real threshold/experiment
    from the mocked analysis run alone. This uses the same
    direct-repository-seeding pattern as
    `test_value_of_information_api.py::
    test_voi_primary_uncertainty_connects_to_a_real_threshold` to
    guarantee a real, linked threshold + experiment exist, then
    recomputes VOI so the adaptive loop has something real to select.
    """
    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    decision_id = _create_decision(client)
    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    decision_repo = DecisionRepository()
    assumptions = decision_repo.list_assumptions(_UUID(decision_id))
    assumption = assumptions[0]

    scenarios = decision_repo.create_regret_scenarios(
        _UUID(decision_id),
        [
            {
                "title": "Adoption failure",
                "failure_condition": "x",
                "regret_level": "critical",
                "impact": "severe",
                "related_assumption_ids": [str(assumption.id)],
            }
        ],
    )
    threshold = decision_repo.create_thresholds(
        _UUID(decision_id),
        [
            {
                "variable": "Repeat-order rate",
                "validation_status": "validated",
                "derivation": "calculated_from_evidence",
                "related_assumption_ids": [str(assumption.id)],
                "related_regret_scenario_ids": [str(scenarios[0].id)],
            }
        ],
    )[0]
    experiment = decision_repo.create_experiments(
        _UUID(decision_id),
        [
            {
                "title": "14-day limited delivery pilot",
                "hypothesis": "Customers will reorder at a sufficient rate.",
                "target_threshold_id": str(threshold.id),
                "decision_rule": "If met, reassess. If missed, do not commit yet.",
                "feasibility": "high",
                "reversibility": "high",
                "estimated_cost": 5000,
            }
        ],
    )[0]

    client.post(f"/api/v1/decisions/{decision_id}/value-of-information/recompute")
    return decision_id, str(experiment.id)


# --- GET /decisions/{id}/adaptive ---------------------------------------------


def test_get_adaptive_before_started_returns_404(client: TestClient) -> None:
    decision_id, _ = _analyzed_decision_and_experiment(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/adaptive")

    assert response.status_code == 404


def test_get_adaptive_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/decisions/{uuid4()}/adaptive")
    assert response.status_code == 404


def test_get_adaptive_history_before_started_returns_empty_list(client: TestClient) -> None:
    decision_id, _ = _analyzed_decision_and_experiment(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/adaptive/history")

    assert response.status_code == 200
    assert response.json() == []


def test_get_adaptive_history_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/decisions/{uuid4()}/adaptive/history")
    assert response.status_code == 404


# --- POST /decisions/{id}/adaptive/advance ------------------------------------


def test_advance_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.post(f"/api/v1/decisions/{uuid4()}/adaptive/advance")
    assert response.status_code == 404


def test_advance_starts_the_first_cycle(client: TestClient) -> None:
    decision_id, experiment_id = _analyzed_decision_and_experiment(client)

    response = client.post(f"/api/v1/decisions/{decision_id}/adaptive/advance")

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "started_first_cycle"
    assert body["state"]["cycle_number"] == 1
    assert body["state"]["current_status"] == "awaiting_experiment"
    assert body["state"]["current_experiment_id"] == experiment_id

    # The now-started state is retrievable via GET.
    fetched = client.get(f"/api/v1/decisions/{decision_id}/adaptive")
    assert fetched.status_code == 200
    assert fetched.json()["state_id"] == body["state"]["state_id"]


def test_advance_twice_with_no_new_evidence_is_idempotent(client: TestClient) -> None:
    decision_id, _ = _analyzed_decision_and_experiment(client)

    first = client.post(f"/api/v1/decisions/{decision_id}/adaptive/advance").json()
    second = client.post(f"/api/v1/decisions/{decision_id}/adaptive/advance").json()

    assert second["outcome"] == "no_change"
    assert first["state"]["state_id"] == second["state"]["state_id"]

    history = client.get(f"/api/v1/decisions/{decision_id}/adaptive/history").json()
    assert len(history) == 1


def test_advance_after_submitting_result_moves_to_next_cycle(client: TestClient) -> None:
    decision_id, experiment_id = _analyzed_decision_and_experiment(client)

    client.post(f"/api/v1/decisions/{decision_id}/adaptive/advance")

    result_response = client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={
            "outcome": "success",
            "summary": "35 of 100 customers reordered.",
            "measured_values": {"Repeat-order rate": 35},
        },
    )
    assert result_response.status_code == 201

    after_result = client.get(f"/api/v1/decisions/{decision_id}/adaptive").json()
    assert after_result["current_status"] == "ready_for_next_experiment"

    advanced = client.post(f"/api/v1/decisions/{decision_id}/adaptive/advance").json()
    # Only one experiment exists in this mocked pipeline, so with nothing
    # else feasible left to test the loop concludes rather than
    # re-selecting the same, now-completed experiment.
    assert advanced["state"]["current_experiment_id"] != experiment_id


# --- POST /decisions/{id}/adaptive/stop ---------------------------------------


def test_stop_before_started_returns_404(client: TestClient) -> None:
    decision_id, _ = _analyzed_decision_and_experiment(client)

    response = client.post(f"/api/v1/decisions/{decision_id}/adaptive/stop")

    assert response.status_code == 404


def test_stop_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.post(f"/api/v1/decisions/{uuid4()}/adaptive/stop")
    assert response.status_code == 404


def test_stop_after_started_marks_user_stopped_and_preserves_history(client: TestClient) -> None:
    decision_id, _ = _analyzed_decision_and_experiment(client)

    started = client.post(f"/api/v1/decisions/{decision_id}/adaptive/advance").json()

    stopped = client.post(f"/api/v1/decisions/{decision_id}/adaptive/stop")
    assert stopped.status_code == 200
    assert stopped.json()["current_status"] == "user_stopped"

    history = client.get(f"/api/v1/decisions/{decision_id}/adaptive/history").json()
    assert len(history) == 2
    assert any(s["state_id"] == started["state"]["state_id"] for s in history)


# --- Experiment-result-submission integration ---------------------------------


def test_submitting_result_calls_mark_experiment_completed_without_altering_response_contract(
    client: TestClient,
) -> None:
    decision_id, experiment_id = _analyzed_decision_and_experiment(client)
    client.post(f"/api/v1/decisions/{decision_id}/adaptive/advance")

    with patch(
        "app.adaptive.service.AdaptiveExperimentService.mark_experiment_completed"
    ) as mock_mark:
        submit_response = client.post(
            f"/api/v1/experiments/{experiment_id}/results",
            json={"outcome": "success", "summary": "x"},
        )

    assert submit_response.status_code == 201
    mock_mark.assert_called_once()
    body = submit_response.json()
    assert set(body.keys()) == {
        "experiment_id", "result_id", "reevaluation_id", "status",
        "decision_assessment", "key_learning", "next_step",
    }


def test_adaptive_bookkeeping_failure_never_blocks_result_submission(client: TestClient) -> None:
    decision_id, experiment_id = _analyzed_decision_and_experiment(client)
    client.post(f"/api/v1/decisions/{decision_id}/adaptive/advance")

    with patch(
        "app.adaptive.service.AdaptiveExperimentService.mark_experiment_completed",
        side_effect=RuntimeError("boom"),
    ):
        response = client.post(
            f"/api/v1/experiments/{experiment_id}/results",
            json={"outcome": "failure", "summary": "x"},
        )

    assert response.status_code == 201


def test_submitting_result_without_an_active_adaptive_loop_is_a_safe_no_op(
    client: TestClient,
) -> None:
    """A result can be submitted for an experiment before the adaptive
    loop has ever been started for that decision - `mark_experiment_completed`
    must be a no-op (never a crash) in that case."""
    decision_id, experiment_id = _analyzed_decision_and_experiment(client)

    response = client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={"outcome": "success", "summary": "x"},
    )

    assert response.status_code == 201
    # No adaptive loop was ever started, so GET must still 404.
    assert client.get(f"/api/v1/decisions/{decision_id}/adaptive").status_code == 404


# NOTE on user isolation: there is no real authentication yet (see
# `app.dependencies.auth.get_current_user_id` - every request is
# currently attributed to the same fixed placeholder user id), so there
# is no way to simulate a second distinct user through the API layer
# itself. User-scoping of adaptive state (keyed by decision_id, and a
# decision is already user-scoped in `DecisionRepository`) is covered at
# the service level in `test_adaptive_service.py::
# test_user_isolation_adaptive_state_is_scoped_by_decision_not_shared`.
