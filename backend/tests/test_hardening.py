"""Tests for Step 12 (Production Hardening + AWS Integration Readiness):

- idempotent /analyze (duplicate requests reuse the active run)
- the analysis status endpoint
- standardized error envelope
- production config validation
- request id propagation
- readiness endpoint

Strands/LLM invocation is mocked wherever a full pipeline run is needed,
mirroring the pattern already established in `test_analysis.py`. Nothing
here makes a real Bedrock or external HTTP call.
"""

import asyncio
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.schemas import (
    Assumption,
    AssumptionAnalysis,
    ConfidenceLevel,
    DecisionAnalysis,
    ImportanceLevel,
    InformationClassification,
)
from app.core.config import Settings

DECISION_PAYLOAD = {
    "title": "Open a second bakery location",
    "description": "Considering a second storefront in the downtown district.",
}


def _create_decision(client: TestClient) -> str:
    response = client.post("/api/v1/decisions", json=DECISION_PAYLOAD)
    assert response.status_code == 201
    return response.json()["id"]


@contextmanager
def _mocked_pipeline_that_fails_at_blindspot_hunter():
    """Patch the first three agent call sites so the pipeline completes
    Decision Analyzer + Assumption Hunter, then fails at the Blindspot
    Hunter - a cheap, deterministic way to produce a `failed` run with a
    known, non-trivial `stage_statuses` shape for these tests."""
    with (
        patch(
            "app.agents.orchestrator.run_decision_analyzer",
            new=AsyncMock(return_value=_sample_analysis()),
        ),
        patch(
            "app.agents.orchestrator.run_assumption_hunter",
            new=AsyncMock(return_value=AssumptionAnalysis(assumptions=[])),
        ),
        patch(
            "app.agents.orchestrator.run_blindspot_hunter",
            new=AsyncMock(side_effect=RuntimeError("stop")),
        ),
    ):
        yield


def _sample_analysis() -> DecisionAnalysis:
    return DecisionAnalysis(
        decision_summary="Whether to open a second bakery location downtown.",
        decision_type="market expansion",
        goal="Increase revenue by expanding to a second physical location.",
        constraints=["Limited capital"],
        success_criteria=["Second location breaks even within 12 months"],
        key_variables=["Foot traffic downtown"],
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


# --- Idempotent /analyze -------------------------------------------------------


def test_concurrent_analyze_calls_reuse_the_active_run(client: TestClient) -> None:
    """Two concurrent POST /analyze calls for the same decision must not
    start two separate pipelines - the second call must observe the first
    run (already `running`) and reuse it rather than creating a duplicate.
    """
    decision_id = _create_decision(client)

    # A slow Decision Analyzer so both requests are in flight
    # simultaneously - the second one must see the first run as active.
    async def _slow_decision_analyzer(*args, **kwargs):
        await asyncio.sleep(0.2)
        return _sample_analysis()

    with (
        patch(
            "app.agents.orchestrator.run_decision_analyzer",
            new=AsyncMock(side_effect=_slow_decision_analyzer),
        ) as mock_analyzer,
        patch(
            "app.agents.orchestrator.run_assumption_hunter",
            new=AsyncMock(return_value=AssumptionAnalysis(assumptions=[])),
        ),
    ):
        import concurrent.futures

        def _call() -> dict:
            response = client.post(f"/api/v1/decisions/{decision_id}/analyze")
            return response.json()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            future_a = pool.submit(_call)
            future_b = pool.submit(_call)
            body_a = future_a.result()
            body_b = future_b.result()

        # Both requests must resolve to the SAME analysis_run_id - the
        # second one reused the first's active run rather than starting
        # its own pipeline.
        assert body_a["analysis_run_id"] == body_b["analysis_run_id"]
        # The (slow) Decision Analyzer must only have been invoked once -
        # if idempotency failed, it would have been invoked twice.
        assert mock_analyzer.await_count == 1


def test_sequential_analyze_calls_after_completion_start_a_new_run(client: TestClient) -> None:
    """Idempotency only applies to an ACTIVE run - once a run reaches a
    terminal status, a subsequent /analyze call must start a fresh one."""
    decision_id = _create_decision(client)

    with _mocked_pipeline_that_fails_at_blindspot_hunter():
        first = client.post(f"/api/v1/decisions/{decision_id}/analyze").json()
        second = client.post(f"/api/v1/decisions/{decision_id}/analyze").json()

    assert first["status"] == "failed"
    assert second["status"] == "failed"
    assert first["analysis_run_id"] != second["analysis_run_id"]


# --- Analysis status endpoint --------------------------------------------------


def test_analysis_status_endpoint_returns_stage_statuses(client: TestClient) -> None:
    decision_id = _create_decision(client)

    with _mocked_pipeline_that_fails_at_blindspot_hunter():
        analyze_response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    run_id = analyze_response.json()["analysis_run_id"]
    status_response = client.get(f"/api/v1/decisions/{decision_id}/analysis/{run_id}")

    assert status_response.status_code == 200
    body = status_response.json()
    assert body["analysis_run_id"] == run_id
    assert body["decision_id"] == decision_id
    assert body["status"] == "failed"
    assert body["stage_statuses"]["decision_analyzer"] == "completed"
    assert body["stage_statuses"]["assumption_hunter"] == "completed"
    assert body["stage_statuses"]["blindspot_hunter"] == "failed"
    assert body["stage_statuses"]["research_agent"] == "skipped"
    assert body["created_at"]
    assert body["updated_at"]
    # Never leaks chain-of-thought/prompts - only execution metadata.
    assert "prompt" not in body
    assert "reasoning" not in body


def test_latest_analysis_status_endpoint_returns_most_recent_run(client: TestClient) -> None:
    """Lets a caller poll a decision's just-created run from a second,
    concurrent request while the (synchronous) /analyze call is still in
    flight - see app/api/routes/analysis.py::get_latest_analysis_status."""
    decision_id = _create_decision(client)

    with _mocked_pipeline_that_fails_at_blindspot_hunter():
        analyze_response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    run_id = analyze_response.json()["analysis_run_id"]
    latest_response = client.get(f"/api/v1/decisions/{decision_id}/analysis/latest")

    assert latest_response.status_code == 200
    body = latest_response.json()
    assert body["analysis_run_id"] == run_id
    assert body["status"] == "failed"


def test_latest_analysis_status_endpoint_no_runs_yet_returns_404(client: TestClient) -> None:
    decision_id = _create_decision(client)

    response = client.get(f"/api/v1/decisions/{decision_id}/analysis/latest")

    assert response.status_code == 404


def test_latest_analysis_status_endpoint_returns_most_recent_of_several_runs(
    client: TestClient,
) -> None:
    decision_id = _create_decision(client)

    with _mocked_pipeline_that_fails_at_blindspot_hunter():
        first = client.post(f"/api/v1/decisions/{decision_id}/analyze").json()
        second = client.post(f"/api/v1/decisions/{decision_id}/analyze").json()

    assert first["analysis_run_id"] != second["analysis_run_id"]

    response = client.get(f"/api/v1/decisions/{decision_id}/analysis/latest")

    assert response.status_code == 200
    assert response.json()["analysis_run_id"] == second["analysis_run_id"]


def test_analysis_status_endpoint_unknown_run_returns_404(client: TestClient) -> None:
    decision_id = _create_decision(client)

    response = client.get(
        f"/api/v1/decisions/{decision_id}/analysis/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404


def test_analysis_status_endpoint_requires_ownership(client: TestClient) -> None:
    decision_id = _create_decision(client)

    with _mocked_pipeline_that_fails_at_blindspot_hunter():
        analyze_response = client.post(f"/api/v1/decisions/{decision_id}/analyze")
    run_id = analyze_response.json()["analysis_run_id"]

    from app.dependencies.auth import get_current_user_id
    from app.main import app

    app.dependency_overrides[get_current_user_id] = lambda: "someone-else"
    try:
        response = client.get(f"/api/v1/decisions/{decision_id}/analysis/{run_id}")
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)

    assert response.status_code == 404


# --- Standardized error envelope -----------------------------------------------


def test_error_envelope_shape_on_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/decisions/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert isinstance(body["error"]["message"], str)
    assert body["error"]["request_id"]
    assert body["detail"] == body["error"]["message"]  # backward-compat field


def test_error_envelope_shape_on_validation_error(client: TestClient) -> None:
    response = client.post("/api/v1/decisions", json={"title": "Missing description"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["request_id"]


# --- Request id propagation -----------------------------------------------------


def test_response_echoes_client_supplied_request_id(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "my-custom-id-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "my-custom-id-123"


def test_response_generates_request_id_when_absent(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]


def test_malformed_client_request_id_is_replaced(client: TestClient) -> None:
    """An oversized/invalid client-supplied request id must never be
    echoed back verbatim - a fresh one is generated instead."""
    malformed = "x" * 500
    response = client.get("/api/v1/health", headers={"X-Request-ID": malformed})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != malformed


# --- Readiness endpoint ---------------------------------------------------------


def test_readiness_endpoint_reports_ready_when_dynamodb_reachable(client: TestClient) -> None:
    response = client.get("/api/v1/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    dependency_names = {dep["name"] for dep in body["dependencies"]}
    assert "dynamodb" in dependency_names
    assert "research_provider" in dependency_names


def test_health_endpoint_never_depends_on_research_provider(client: TestClient) -> None:
    """The basic liveness check must never fail because an optional
    external dependency (research) isn't configured."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "regret-engine-api"}


# --- Production config validation -----------------------------------------------


def test_production_config_requires_explicit_cors_origins() -> None:
    settings = Settings(
        app_env="production",
        cors_allowed_origins="*",
        aws_region="us-east-1",
        dynamodb_table_name="regret-engine",
        bedrock_model_id="some-model",
    )

    with pytest.raises(RuntimeError, match="CORS_ALLOWED_ORIGINS"):
        settings.validate_for_production()


def test_production_config_requires_dynamodb_table_name() -> None:
    settings = Settings(
        app_env="production",
        dynamodb_table_name="",
        cors_allowed_origins="https://app.example.com",
        aws_region="us-east-1",
        bedrock_model_id="some-model",
    )

    with pytest.raises(RuntimeError, match="DYNAMODB_TABLE_NAME"):
        settings.validate_for_production()


def test_production_config_passes_with_full_valid_configuration() -> None:
    settings = Settings(
        app_env="production",
        cors_allowed_origins="https://app.example.com",
        aws_region="us-east-1",
        dynamodb_table_name="regret-engine",
        bedrock_model_id="some-model",
    )

    settings.validate_for_production()  # must not raise


def test_development_config_never_requires_production_validation() -> None:
    """Development mode must never require any of the production-only
    fields to be set explicitly - defaults are always acceptable."""
    settings = Settings(app_env="development", cors_allowed_origins="*")

    settings.validate_for_production()  # must not raise


# --- Concurrency: analysis semaphore does not deadlock a single request --------


def test_single_analyze_call_still_completes_normally(client: TestClient) -> None:
    """Sanity check that the concurrency-limiting semaphore introduced for
    Step 12 doesn't change behavior for the common single-request case."""
    decision_id = _create_decision(client)

    with _mocked_pipeline_that_fails_at_blindspot_hunter():
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    assert response.json()["status"] == "failed"
