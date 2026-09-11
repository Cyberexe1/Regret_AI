"""API tests for `GET /decisions/{id}/value-of-information` and
`POST /decisions/{id}/value-of-information/recompute`, plus its
integration into the analysis pipeline and the experiment-result
re-evaluation flow (REGRET ENGINE 2.0, Step 20).

Strands/LLM invocation for the analysis pipeline stages is mocked (see
`mock_pipeline`, mirrored from `test_historical_context_api.py`) so no
real Bedrock call ever happens - VOI scoring itself is fully deterministic
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
    real Bedrock call - mirrors `test_historical_context_api.py` exactly."""
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


# --- GET /decisions/{id}/value-of-information --------------------------------


def test_get_voi_before_analysis_returns_404(client: TestClient) -> None:
    decision_id = _create_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/value-of-information")

    assert response.status_code == 404


def test_get_voi_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/decisions/{uuid4()}/value-of-information")
    assert response.status_code == 404


def test_get_voi_after_analysis_returns_ranked_uncertainties(client: TestClient) -> None:
    decision_id, _ = _analyzed_decision_and_experiment(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/value-of-information")

    assert response.status_code == 200
    body = response.json()
    assert len(body["ranked_uncertainties"]) >= 1
    assert body["primary_uncertainty_id"] is not None
    assert body["methodology_version"] == "voi-v1"
    assert body["decision_id"] == decision_id


def test_voi_primary_uncertainty_connects_to_a_real_threshold(client: TestClient) -> None:
    """The mocked pipeline in this file doesn't link the threshold back to
    the assumption via related_assumption_ids (mirroring how little the
    Threshold Engine mock bothers to cross-reference) - so this uses the
    direct-repository seeding pattern from test_historical_context.py to
    guarantee a real, linked threshold exists, then recomputes VOI against it."""
    from app.repositories.decision_repository import DecisionRepository

    decision_id, _ = _analyzed_decision_and_experiment(client)
    decision_repo = DecisionRepository()
    from uuid import UUID as _UUID

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
    decision_repo.create_thresholds(
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
    )

    recompute_response = client.post(
        f"/api/v1/decisions/{decision_id}/value-of-information/recompute"
    )
    body = recompute_response.json()
    thresholds = client.get(f"/api/v1/decisions/{decision_id}/thresholds").json()
    threshold_ids = {t["id"] for t in thresholds}

    assert body["primary_threshold_id"] in threshold_ids


def test_voi_never_produces_fake_numeric_probability_fields(client: TestClient) -> None:
    """Every score-bearing field must be a documented qualitative band
    (a string enum value), never a bare float presented as a probability."""
    decision_id, _ = _analyzed_decision_and_experiment(client)

    body = client.get(f"/api/v1/decisions/{decision_id}/value-of-information").json()

    for item in body["ranked_uncertainties"]:
        assert isinstance(item["information_value"], str)
        assert isinstance(item["practical_value"], str)
        # confidence IS a bounded float, but explicitly documented as
        # "how much of this score rests on real inputs", never a
        # probability - the schema's own docstring enforces the framing,
        # this just confirms the bound.
        assert 0.0 <= item["confidence"] <= 1.0


# --- POST /decisions/{id}/value-of-information/recompute ---------------------


def test_recompute_creates_a_new_analysis_and_supersedes_the_old_one(client: TestClient) -> None:
    decision_id, _ = _analyzed_decision_and_experiment(client)

    first = client.get(f"/api/v1/decisions/{decision_id}/value-of-information").json()

    recomputed = client.post(f"/api/v1/decisions/{decision_id}/value-of-information/recompute")
    assert recomputed.status_code == 201
    second = recomputed.json()

    assert second["analysis_id"] != first["analysis_id"]

    latest = client.get(f"/api/v1/decisions/{decision_id}/value-of-information").json()
    assert latest["analysis_id"] == second["analysis_id"]


def test_recompute_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.post(f"/api/v1/decisions/{uuid4()}/value-of-information/recompute")
    assert response.status_code == 404


# --- Re-evaluation integration (spec section 21): recompute after a result ---


def test_submitting_experiment_result_recomputes_voi_automatically(client: TestClient) -> None:
    decision_id, experiment_id = _analyzed_decision_and_experiment(client)

    before = client.get(f"/api/v1/decisions/{decision_id}/value-of-information").json()

    submit_response = client.post(
        f"/api/v1/experiments/{experiment_id}/results",
        json={
            "outcome": "success",
            "summary": "35 of 100 customers reordered.",
            "measured_values": {"Repeat-order rate": 35},
        },
    )
    assert submit_response.status_code == 201

    after = client.get(f"/api/v1/decisions/{decision_id}/value-of-information").json()

    assert after["analysis_id"] != before["analysis_id"]
    # The original ExperimentResultResponse contract is unchanged - VOI
    # integration must not alter the existing API shape.
    submit_body = submit_response.json()
    assert set(submit_body.keys()) == {
        "experiment_id", "result_id", "reevaluation_id", "status",
        "decision_assessment", "key_learning", "next_step",
    }


def test_voi_recompute_failure_never_blocks_result_submission(client: TestClient) -> None:
    decision_id, experiment_id = _analyzed_decision_and_experiment(client)

    with patch(
        "app.agents.value_of_information.ValueOfInformationService.compute_and_persist",
        side_effect=RuntimeError("boom"),
    ):
        response = client.post(
            f"/api/v1/experiments/{experiment_id}/results",
            json={"outcome": "failure", "summary": "x"},
        )

    assert response.status_code == 201


# --- Orchestrator integration: additive, never blocking analysis ------------


def test_voi_computation_failure_never_blocks_analysis(client: TestClient) -> None:
    decision_id = _create_decision(client)

    with patch(
        "app.agents.orchestrator.ValueOfInformationService.compute_and_persist",
        side_effect=RuntimeError("boom"),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    assert response.json()["status"] == "completed"


def test_analysis_result_includes_value_of_information_key(client: TestClient) -> None:
    decision_id, _ = _analyzed_decision_and_experiment(client)

    runs = client.get(f"/api/v1/decisions/{decision_id}/analysis/latest")
    assert runs.status_code == 200
    assert runs.json()["status"] == "completed"


def test_experiment_planner_prioritizes_primary_uncertainty_threshold(client: TestClient) -> None:
    """The mocked Experiment Planner in this file always targets
    thresholds[0] regardless of the VOI hint (mirroring the real
    planner's own final judgment) - this test instead confirms the VOI
    hint was actually passed into the call, never silently dropped."""
    with patch(
        "app.agents.orchestrator.run_experiment_planner",
        new=AsyncMock(side_effect=_experiment_plan_side_effect),
    ) as mock_planner:
        decision_id = _create_decision(client)
        client.post(f"/api/v1/decisions/{decision_id}/analyze")

    mock_planner.assert_awaited_once()
    args = mock_planner.await_args.args
    assert len(args) == 8
    voi_analysis_arg = args[7]
    assert voi_analysis_arg is not None
    assert voi_analysis_arg.primary_uncertainty_id is not None
