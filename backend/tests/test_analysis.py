"""Tests for the analysis API and orchestrator.

The Strands agent invocation (`app.agents.decision_analyzer.run_decision_analyzer`)
is mocked in every test here - nothing in this suite makes a real call to
Amazon Bedrock, and no AWS credentials are required. DynamoDB access still
goes through moto (see `conftest.py`).
"""

from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.agents.schemas import (
    Assumption,
    ConfidenceLevel,
    DecisionAnalysis,
    ImportanceLevel,
    InformationClassification,
)

DECISION_PAYLOAD = {
    "title": "Open a second bakery location",
    "description": "Considering a second storefront in the downtown district.",
}


def _create_decision(client: TestClient) -> str:
    response = client.post("/api/v1/decisions", json=DECISION_PAYLOAD)
    assert response.status_code == 201
    return response.json()["id"]


def _sample_analysis() -> DecisionAnalysis:
    return DecisionAnalysis(
        decision_summary="Whether to open a second bakery location downtown.",
        decision_type="market expansion",
        goal="Increase revenue by expanding to a second physical location.",
        constraints=["Limited capital", "Six-month lease decision window"],
        success_criteria=["Second location breaks even within 12 months"],
        key_variables=["Foot traffic downtown", "Lease cost", "Staffing availability"],
        initial_assumptions=[
            Assumption(
                statement="Downtown foot traffic is high enough to sustain a second store.",
                importance=ImportanceLevel.HIGH,
                confidence=ConfidenceLevel.MEDIUM,
                classification=InformationClassification.ASSUMPTION,
                reason="No foot-traffic evidence was submitted for this decision.",
            )
        ],
        unknowns=["Actual downtown lease rates were not provided."],
    )


@pytest.fixture(autouse=True)
def mock_decision_analyzer():
    """Patch the Strands agent call site so no real Bedrock call ever happens."""
    with patch(
        "app.agents.orchestrator.run_decision_analyzer",
        new=AsyncMock(return_value=_sample_analysis()),
    ) as mocked:
        yield mocked


def test_analyze_decision_success(client: TestClient, mock_decision_analyzer: AsyncMock) -> None:
    decision_id = _create_decision(client)

    response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    body = response.json()
    assert body["decision_id"] == decision_id
    assert body["status"] == "completed"
    assert UUID(body["analysis_run_id"])  # well-formed UUID
    mock_decision_analyzer.assert_awaited_once()


def test_analyze_missing_decision_returns_404(client: TestClient) -> None:
    response = client.post("/api/v1/decisions/00000000-0000-0000-0000-000000000000/analyze")

    assert response.status_code == 404


def test_analysis_result_is_persisted_in_dynamodb(client: TestClient) -> None:
    """The orchestrator must go through the repository, not bypass it."""
    decision_id = _create_decision(client)

    analyze_response = client.post(f"/api/v1/decisions/{decision_id}/analyze")
    run_id = analyze_response.json()["analysis_run_id"]

    from uuid import UUID as _UUID

    from app.repositories.analysis_repository import AnalysisRepository

    repo = AnalysisRepository()
    stored_run = repo.get(_UUID(decision_id), _UUID(run_id))

    assert stored_run is not None
    assert stored_run.status == "completed"
    assert stored_run.result is not None
    assert stored_run.result["decision_type"] == "market expansion"


def test_analysis_run_status_lifecycle_reaches_completed(client: TestClient) -> None:
    decision_id = _create_decision(client)

    response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    # queued -> running -> completed all happen within one synchronous call;
    # only the terminal status is observable from the API response.
    assert response.json()["status"] == "completed"


def test_analyze_decision_with_malformed_model_output_fails_gracefully(client: TestClient) -> None:
    decision_id = _create_decision(client)

    error = ValueError("Decision analyzer did not return structured output.")
    with patch(
        "app.agents.orchestrator.run_decision_analyzer",
        new=AsyncMock(side_effect=error),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201  # the run itself is created and returned...
    body = response.json()
    assert body["status"] == "failed"  # ...but marked failed, not silently accepted


def test_analyze_decision_model_failure_returns_safe_error_message(client: TestClient) -> None:
    decision_id = _create_decision(client)

    error = RuntimeError("botocore.exceptions.ClientError: secret-detail-xyz")
    with patch(
        "app.agents.orchestrator.run_decision_analyzer",
        new=AsyncMock(side_effect=error),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"

    from uuid import UUID as _UUID

    from app.repositories.analysis_repository import AnalysisRepository

    repo = AnalysisRepository()
    stored_run = repo.get(_UUID(decision_id), _UUID(body["analysis_run_id"]))

    assert stored_run is not None
    assert "secret-detail-xyz" not in (stored_run.error_message or "")
    assert "botocore" not in (stored_run.error_message or "")


def test_analyze_decision_timeout_fails_gracefully(client: TestClient) -> None:
    decision_id = _create_decision(client)

    with patch(
        "app.agents.orchestrator.run_decision_analyzer",
        new=AsyncMock(side_effect=TimeoutError()),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    assert response.json()["status"] == "failed"


def test_analysis_does_not_bypass_repository_layer(client: TestClient) -> None:
    """The orchestrator must call the repository, never boto3/DynamoDB directly.

    Patch the repository's own update_status method and confirm the
    orchestrator's terminal status transition goes through it rather than
    around it.
    """
    decision_id = _create_decision(client)

    from app.repositories.analysis_repository import AnalysisRepository

    original = AnalysisRepository.update_status
    with patch.object(
        AnalysisRepository, "update_status", autospec=True, side_effect=original
    ) as spy:
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    assert spy.call_count >= 2  # at least: -> running, -> completed/failed


def test_analyze_decision_owned_by_another_user_returns_404(client: TestClient) -> None:
    """A decision that exists but belongs to a different user is treated as not found."""
    decision_id = _create_decision(client)

    from app.dependencies.auth import get_current_user_id
    from app.main import app

    app.dependency_overrides[get_current_user_id] = lambda: "someone-else"
    try:
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)

    assert response.status_code == 404
