"""API tests for the Cross-Decision Learning routes (REGRET ENGINE 2.0,
Step 23):

    GET  /learning/patterns
    GET  /learning/patterns/{pattern_id}
    POST /learning/patterns/refresh
    GET  /decisions/{decision_id}/patterns

No LLM/Strands invocation is mocked here because none is needed -
pattern detection is fully deterministic Python. Data is seeded directly
through the real repositories, mirroring `test_adaptive_api.py`'s
direct-repository-seeding helper for cases where the mocked analysis
pipeline itself isn't the point of the test.
"""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.memory.memory_repository import MemoryRepository
from app.memory.memory_service import MemoryService
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


def _seed_failed_retention_decision(client: TestClient) -> str:
    """Seeds one decision, through the real repositories, with a failed
    retention assumption/threshold - mirrors `test_learning_service.py`'s
    helper but driven from the API-level `client` fixture's own table."""
    from uuid import UUID as _UUID

    decision_id = _create_decision(client)
    decision_repo = DecisionRepository()
    evidence_repo = EvidenceRepository()
    memory_repo = MemoryRepository()
    memory_service = MemoryService(memory_repo, decision_repo)
    reeval_service = ReEvaluationService(decision_repo, evidence_repo)

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
                "validation_status": "validated",
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
                "title": "x",
                "hypothesis": "x",
                "target_threshold_id": str(threshold.id),
                "decision_rule": "x",
                "feasibility": "high",
                "reversibility": "high",
                "estimated_cost": 1000,
            }
        ],
    )[0]

    result, reevaluation = reeval_service.submit_result(
        _UUID(decision_id),
        experiment.id,
        ExperimentResultCreate(
            outcome="failure",
            summary="Observed weak retention.",
            measured_values={"Customer retention rate": 10},
        ),
    )
    memory_service.update_memory_from_reevaluation(
        _UUID(decision_id), experiment.id, result, reevaluation
    )
    return decision_id


# --- GET /learning/patterns ------------------------------------------------------


def test_list_patterns_before_any_refresh_returns_empty(client: TestClient) -> None:
    response = client.get("/api/v1/learning/patterns")

    assert response.status_code == 200
    assert response.json() == {"patterns": []}


def test_list_patterns_after_refresh_returns_real_patterns(client: TestClient) -> None:
    _seed_failed_retention_decision(client)
    _seed_failed_retention_decision(client)

    refresh = client.post("/api/v1/learning/patterns/refresh")
    assert refresh.status_code == 200
    assert refresh.json()["patterns_created"] >= 1

    response = client.get("/api/v1/learning/patterns")
    body = response.json()

    assert response.status_code == 200
    assert len(body["patterns"]) >= 1
    assert any(p["pattern_type"] == "recurring_failed_assumption" for p in body["patterns"])


def test_list_patterns_supports_pattern_type_filter(client: TestClient) -> None:
    _seed_failed_retention_decision(client)
    _seed_failed_retention_decision(client)
    client.post("/api/v1/learning/patterns/refresh")

    response = client.get(
        "/api/v1/learning/patterns", params={"pattern_type": "recurring_failed_assumption"}
    )
    body = response.json()

    assert response.status_code == 200
    assert all(p["pattern_type"] == "recurring_failed_assumption" for p in body["patterns"])


# --- GET /learning/patterns/{pattern_id} ------------------------------------------


def test_get_pattern_detail_returns_occurrences(client: TestClient) -> None:
    _seed_failed_retention_decision(client)
    _seed_failed_retention_decision(client)
    client.post("/api/v1/learning/patterns/refresh")
    patterns = client.get("/api/v1/learning/patterns").json()["patterns"]
    failed = next(p for p in patterns if p["pattern_type"] == "recurring_failed_assumption")

    response = client.get(f"/api/v1/learning/patterns/{failed['pattern_id']}")
    body = response.json()

    assert response.status_code == 200
    assert body["pattern"]["pattern_id"] == failed["pattern_id"]
    assert len(body["occurrences"]) == 2
    assert len(body["supporting_occurrences"]) == 2
    assert body["contradicting_occurrences"] == []


def test_get_pattern_detail_unknown_id_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/learning/patterns/not-a-real-pattern")

    assert response.status_code == 404


# --- POST /learning/patterns/refresh ----------------------------------------------


def test_refresh_is_idempotent_via_the_api(client: TestClient) -> None:
    _seed_failed_retention_decision(client)
    _seed_failed_retention_decision(client)

    first = client.post("/api/v1/learning/patterns/refresh").json()
    second = client.post("/api/v1/learning/patterns/refresh").json()

    assert second["patterns_created"] == 0
    assert second["patterns_unchanged"] == first["patterns_created"]
    assert second["total_patterns"] == first["total_patterns"]


def test_refresh_with_no_decisions_never_fails(client: TestClient) -> None:
    response = client.post("/api/v1/learning/patterns/refresh")

    assert response.status_code == 200
    assert response.json()["total_patterns"] == 0


# --- GET /decisions/{decision_id}/patterns ----------------------------------------


def test_get_patterns_for_decision_returns_only_relevant_patterns(client: TestClient) -> None:
    decision_id_1 = _seed_failed_retention_decision(client)
    decision_id_2 = _seed_failed_retention_decision(client)
    client.post("/api/v1/learning/patterns/refresh")

    response = client.get(f"/api/v1/decisions/{decision_id_1}/patterns")
    body = response.json()

    assert response.status_code == 200
    assert len(body["patterns"]) >= 1
    for pattern in body["patterns"]:
        assert (
            decision_id_1 in pattern["supporting_decision_ids"]
            or decision_id_1 in pattern["contradicting_decision_ids"]
        )

    # decision_id_2's patterns are the SAME patterns (they share the
    # recurring variable) - both decisions legitimately appear as
    # supporting evidence for the same real pattern.
    response_2 = client.get(f"/api/v1/decisions/{decision_id_2}/patterns")
    assert response_2.status_code == 200


def test_get_patterns_for_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/decisions/{uuid4()}/patterns")

    assert response.status_code == 404


def test_get_patterns_for_decision_before_refresh_returns_empty(client: TestClient) -> None:
    decision_id = _seed_failed_retention_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/patterns")

    assert response.status_code == 200
    assert response.json() == {"patterns": []}


# --- security: no secrets, no chain-of-thought ------------------------------------


def test_pattern_responses_never_expose_internal_fields(client: TestClient) -> None:
    _seed_failed_retention_decision(client)
    _seed_failed_retention_decision(client)
    client.post("/api/v1/learning/patterns/refresh")

    body = client.get("/api/v1/learning/patterns").json()

    serialized = str(body)
    for forbidden in ("chain_of_thought", "system_prompt", "aws_secret", "bedrock_api_key"):
        assert forbidden not in serialized
