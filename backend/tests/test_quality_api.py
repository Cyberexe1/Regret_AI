"""API tests for the Decision Intelligence Quality & Calibration routes
(REGRET ENGINE 2.0, Step 24):

    GET  /decisions/{decision_id}/quality
    GET  /decisions/{decision_id}/quality/history
    POST /decisions/{decision_id}/quality/check
    GET  /learning/calibration
    GET  /learning/calibration/{variable}
    POST /learning/calibration/refresh

No LLM/Strands invocation is mocked here because none is needed - the
quality engine is fully deterministic Python. Data is seeded directly
through the real repositories, mirroring `test_learning_api.py`'s
direct-repository-seeding helper.

There is no real auth in this codebase yet, so "another user" is
simulated the same way `test_learning_api.py`/`test_adaptive_api.py` do:
by calling the SERVICE directly with a different `user_id` string for
isolation checks, since the HTTP layer itself has only one fixed caller
identity.
"""

from uuid import UUID as _UUID
from uuid import uuid4

from fastapi.testclient import TestClient

from app.memory.memory_repository import MemoryRepository
from app.memory.memory_service import MemoryService
from app.quality.repository import CalibrationRepository
from app.quality.service import CalibrationService
from app.repositories.decision_repository import DecisionRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.schemas.experiment_result import ExperimentResultCreate
from app.services.re_evaluation_service import ReEvaluationService


def _create_decision(client: TestClient) -> str:
    response = client.post(
        "/api/v1/decisions",
        json={"title": "Open a cloud kitchen", "description": "x", "budget": 500000},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _seed_decision_with_experiment(client: TestClient) -> dict:
    decision_id = _create_decision(client)
    decision_repo = DecisionRepository()

    assumption = decision_repo.create_assumptions(
        _UUID(decision_id),
        [
            {
                "statement": "Customer retention rate",
                "source": "implicit",
                "importance": "critical",
                "confidence": 0.1,
                "evidence_status": "not_addressed",
            }
        ],
    )[0]
    scenario = decision_repo.create_regret_scenarios(
        _UUID(decision_id),
        [
            {
                "title": "x",
                "failure_condition": "x",
                "regret_level": "critical",
                "impact": "severe",
                "related_assumption_ids": [str(assumption.id)],
            }
        ],
    )[0]
    threshold = decision_repo.create_thresholds(
        _UUID(decision_id),
        [
            {
                "variable": "Customer retention rate",
                "validation_status": "provisional",
                "derivation": "calculated_from_evidence",
                "threshold_value": "24",
                "direction": "below",
                "related_assumption_ids": [str(assumption.id)],
                "related_regret_scenario_ids": [str(scenario.id)],
            }
        ],
    )[0]
    experiment = decision_repo.create_experiments(
        _UUID(decision_id),
        [
            {
                "title": "Retention pilot",
                "hypothesis": "x",
                "target_threshold_id": str(threshold.id),
                "decision_rule": "x",
                "feasibility": "high",
                "reversibility": "high",
                "estimated_cost": 1000,
            }
        ],
    )[0]
    return {"decision_id": decision_id, "experiment_id": str(experiment.id)}


# --- GET /decisions/{decision_id}/quality -----------------------------------------


def test_get_quality_before_any_check_returns_404(client: TestClient) -> None:
    decision_id = _create_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/quality")

    assert response.status_code == 404


def test_get_quality_for_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/decisions/{uuid4()}/quality")

    assert response.status_code == 404


def test_get_quality_after_check_returns_the_assessment(client: TestClient) -> None:
    decision_id = _create_decision(client)
    client.post(f"/api/v1/decisions/{decision_id}/quality/check")

    response = client.get(f"/api/v1/decisions/{decision_id}/quality")
    body = response.json()

    assert response.status_code == 200
    assert body["decision_id"] == decision_id
    assert "overall_quality" in body
    assert "checks" in body


# --- POST /decisions/{decision_id}/quality/check -----------------------------------


def test_run_quality_check_returns_category_bands(client: TestClient) -> None:
    seeded = _seed_decision_with_experiment(client)

    response = client.post(f"/api/v1/decisions/{seeded['decision_id']}/quality/check")
    body = response.json()

    assert response.status_code == 200
    for field in (
        "evidence_quality",
        "assumption_quality",
        "threshold_quality",
        "experiment_quality",
        "provenance_quality",
        "consistency_quality",
        "freshness_quality",
        "historical_learning_quality",
    ):
        assert body[field] in {"strong", "moderate", "weak", "insufficient"}


def test_run_quality_check_for_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.post(f"/api/v1/decisions/{uuid4()}/quality/check")

    assert response.status_code == 404


# --- GET /decisions/{decision_id}/quality/history ----------------------------------


def test_quality_history_before_any_check_is_empty(client: TestClient) -> None:
    decision_id = _create_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/quality/history")

    assert response.status_code == 200
    assert response.json() == []


def test_quality_history_after_checks_is_never_empty(client: TestClient) -> None:
    decision_id = _create_decision(client)
    client.post(f"/api/v1/decisions/{decision_id}/quality/check")

    response = client.get(f"/api/v1/decisions/{decision_id}/quality/history")
    body = response.json()

    assert response.status_code == 200
    assert len(body) >= 1


def test_quality_history_for_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/decisions/{uuid4()}/quality/history")

    assert response.status_code == 404


# --- GET /learning/calibration ------------------------------------------------------


def test_list_calibration_before_any_refresh_returns_empty(client: TestClient) -> None:
    response = client.get("/api/v1/learning/calibration")

    assert response.status_code == 200
    assert response.json() == []


def test_calibration_refresh_and_list_round_trip(client: TestClient) -> None:
    seeded = _seed_decision_with_experiment(client)
    reeval_service = ReEvaluationService(DecisionRepository(), EvidenceRepository())
    memory_service = MemoryService(MemoryRepository(), DecisionRepository())
    result, reevaluation = reeval_service.submit_result(
        _UUID(seeded["decision_id"]),
        _UUID(seeded["experiment_id"]),
        ExperimentResultCreate(
            outcome="failure", summary="x", measured_values={"Customer retention rate": 5}
        ),
    )
    memory_service.update_memory_from_reevaluation(
        _UUID(seeded["decision_id"]), _UUID(seeded["experiment_id"]), result, reevaluation
    )

    refresh_response = client.post("/api/v1/learning/calibration/refresh")
    assert refresh_response.status_code == 200
    assert len(refresh_response.json()) >= 1

    list_response = client.get("/api/v1/learning/calibration")
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1


# --- GET /learning/calibration/{variable} -------------------------------------------


def test_get_calibration_for_unknown_variable_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/learning/calibration/nonexistent-variable")

    assert response.status_code == 404


def test_get_calibration_for_known_variable_returns_insight(client: TestClient) -> None:
    seeded = _seed_decision_with_experiment(client)
    reeval_service = ReEvaluationService(DecisionRepository(), EvidenceRepository())
    memory_service = MemoryService(MemoryRepository(), DecisionRepository())
    result, reevaluation = reeval_service.submit_result(
        _UUID(seeded["decision_id"]),
        _UUID(seeded["experiment_id"]),
        ExperimentResultCreate(
            outcome="failure", summary="x", measured_values={"Customer retention rate": 5}
        ),
    )
    memory_service.update_memory_from_reevaluation(
        _UUID(seeded["decision_id"]), _UUID(seeded["experiment_id"]), result, reevaluation
    )
    client.post("/api/v1/learning/calibration/refresh")

    response = client.get("/api/v1/learning/calibration/Customer retention rate")

    assert response.status_code == 200
    assert response.json()["variable"] == "Customer retention rate"


# --- user isolation (service-level, since there is no real auth to simulate a second caller) ---


def test_calibration_service_isolates_users(dynamodb_table: None) -> None:
    calibration_service = CalibrationService(DecisionRepository(), CalibrationRepository())

    a_insights = calibration_service.refresh_calibration("user-a")
    b_insights = calibration_service.refresh_calibration("user-b")

    assert a_insights == []
    assert b_insights == []
    assert calibration_service.list_for_user("user-a") == []


# --- security: no secrets, no chain-of-thought --------------------------------------


def test_quality_response_never_exposes_internal_fields(client: TestClient) -> None:
    decision_id = _create_decision(client)
    client.post(f"/api/v1/decisions/{decision_id}/quality/check")

    body = client.get(f"/api/v1/decisions/{decision_id}/quality").json()

    serialized = str(body)
    for forbidden in ("chain_of_thought", "system_prompt", "aws_secret", "bedrock_api_key"):
        assert forbidden not in serialized
