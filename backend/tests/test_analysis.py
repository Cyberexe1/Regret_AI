"""Tests for the analysis API and orchestrator.

The Strands agent invocation (`app.agents.decision_analyzer.run_decision_analyzer`)
is mocked in every test here - nothing in this suite makes a real call to
Amazon Bedrock, and no AWS credentials are required. DynamoDB access still
goes through moto (see `conftest.py`).
"""

from datetime import UTC, datetime
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
    EvidenceCredibility,
    EvidenceFinding,
    EvidenceSupportLevel,
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


def _sample_assumption_analysis() -> AssumptionAnalysis:
    return AssumptionAnalysis(
        assumptions=[
            AssumptionFinding(
                statement="Customers will order at least twice per month.",
                source=AssumptionSource.IMPLICIT,
                importance=ImportanceLevel.CRITICAL,
                confidence=0.45,
                evidence_status=AssumptionEvidenceStatus.NOT_ADDRESSED,
                dependency="Business profitability",
                failure_consequence="Revenue may remain below the required operating margin.",
            )
        ]
    )


def _sample_blindspot_analysis() -> BlindspotAnalysis:
    return BlindspotAnalysis(
        blindspots=[
            BlindspotFinding(
                question="What happens to unit economics if repeat orders fall below 20%?",
                category=BlindspotCategory.UNTESTED_ASSUMPTION,
                importance=ImportanceLevel.CRITICAL,
                confidence=0.7,
                evidence_status=BlindspotEvidenceStatus.NOT_ADDRESSED,
                related_assumption_ids=[],
                why_it_matters="Repeat order rate drives whether the location breaks even.",
                evidence_gap="No repeat-purchase data has been submitted for this decision.",
            )
        ]
    )


def _sample_evidence_analysis() -> EvidenceAnalysis:
    return EvidenceAnalysis(findings=[])


def _sample_devil_advocate_analysis() -> DevilAdvocateAnalysis:
    return DevilAdvocateAnalysis(
        overall_challenge=(
            "The business case assumes repeat customers without validating them."
        ),
        challenges=[
            Challenge(
                claim="Repeat customers will be high enough to sustain the business.",
                attack=(
                    "The decision depends on reaching sufficient repeat orders, but the "
                    "supplied evidence only establishes initial demand, not repeat behavior."
                ),
                severity=SeverityLevel.CRITICAL,
                confidence=0.7,
                related_assumption_ids=[],
                related_blindspot_ids=[],
                related_evidence_finding_ids=[],
                failure_mechanism=(
                    "If repeat ordering stays below the assumed level, the projected unit "
                    "economics no longer hold."
                ),
                evidence_basis=(
                    "No submitted evidence addresses repeat-purchase behavior specifically."
                ),
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
                provisional_threshold=None,
                consequence=(
                    "Full capital commitment occurs before demand quality is validated."
                ),
                related_assumption_ids=[],
                related_challenge_ids=[],
                evidence_basis="No repeat-purchase evidence was submitted for this decision.",
            )
        ],
        dominant_regret=(
            "Committing fully before validating repeat demand could leave the business "
            "under-capitalized once true unit economics become clear."
        ),
        highest_risk_scenario_id="scenario-1",
    )


def _sample_threshold_analysis() -> ThresholdAnalysis:
    return ThresholdAnalysis(
        thresholds=[
            Threshold(
                id="threshold-1",
                variable="Repeat-order rate",
                threshold_type=ThresholdType.UNKNOWN,
                direction=ThresholdDirection.BELOW,
                threshold_value=None,
                confidence=0.6,
                derivation=ThresholdDerivation.UNKNOWN,
                consequence=(
                    "The projected unit economics no longer hold if repeat orders stay too low."
                ),
                related_assumption_ids=[],
                related_regret_scenario_ids=[],
                evidence_basis="No repeat-purchase evidence was submitted for this decision.",
                validation_status=ThresholdValidationStatus.UNKNOWN,
            )
        ],
        primary_threshold_id="threshold-1",
        summary=(
            "The decision depends materially on repeat demand, but the available evidence is "
            "insufficient to establish the break-even repeat-order rate."
        ),
    )


def _sample_experiment_plan(target_threshold_id: str = "threshold-1") -> ExperimentPlan:
    """`target_threshold_id` defaults to the agent's own response-scoped
    label, but the orchestrator only persists an experiment whose
    target_threshold_id matches a *real, persisted* threshold id - callers
    that need a persisted experiment to actually survive must pass the
    real id (see `mock_experiment_planner`'s dynamic side_effect below,
    which threads the real persisted threshold id through automatically)."""
    return ExperimentPlan(
        experiments=[
            Experiment(
                id="experiment-1",
                title="14-day limited delivery pilot",
                objective="Validate repeat customer behavior before full capital commitment.",
                hypothesis=(
                    "Customers who make an initial purchase will reorder at a rate sufficient "
                    "to support the economic model."
                ),
                target_threshold_id=target_threshold_id,
                variable_to_test="Repeat-order rate",
                experiment_type=ExperimentType.PILOT,
                steps=["Run a small delivery pilot for 14 days.", "Track first and second orders."],
                success_criteria=["Repeat-order rate reaches or exceeds the target threshold."],
                failure_criteria=["Repeat-order rate remains below the target threshold."],
                duration_days=14,
                estimated_cost=None,
                currency=None,
                evidence_to_collect=["first orders", "second orders", "time to reorder"],
                decision_rule=(
                    "If the threshold is met, reassess the full investment with more "
                    "confidence. If missed, do not commit yet."
                ),
                expected_information_gain=InformationGain.HIGH,
                confidence=0.7,
                feasibility=Feasibility.HIGH,
                reversibility=Reversibility.HIGH,
                related_assumption_ids=[],
                related_regret_scenario_ids=[],
                status=ExperimentPlanStatus.RECOMMENDED,
            )
        ],
        recommended_experiment_id="experiment-1",
        summary="Run a 14-day pilot before committing the full investment.",
    )


@pytest.fixture(autouse=True)
def mock_decision_analyzer():
    """Patch the Strands agent call site so no real Bedrock call ever happens."""
    with patch(
        "app.agents.orchestrator.run_decision_analyzer",
        new=AsyncMock(return_value=_sample_analysis()),
    ) as mocked:
        yield mocked


@pytest.fixture(autouse=True)
def mock_assumption_hunter():
    """Patch the Strands agent call site so no real Bedrock call ever happens."""
    with patch(
        "app.agents.orchestrator.run_assumption_hunter",
        new=AsyncMock(return_value=_sample_assumption_analysis()),
    ) as mocked:
        yield mocked


@pytest.fixture(autouse=True)
def mock_blindspot_hunter():
    """Patch the Strands agent call site so no real Bedrock call ever happens."""
    with patch(
        "app.agents.orchestrator.run_blindspot_hunter",
        new=AsyncMock(return_value=_sample_blindspot_analysis()),
    ) as mocked:
        yield mocked


@pytest.fixture(autouse=True)
def mock_evidence_agent():
    """Patch the Strands agent call site so no real Bedrock call ever happens."""
    with patch(
        "app.agents.orchestrator.run_evidence_agent",
        new=AsyncMock(return_value=_sample_evidence_analysis()),
    ) as mocked:
        yield mocked


@pytest.fixture(autouse=True)
def mock_devils_advocate():
    """Patch the Strands agent call site so no real Bedrock call ever happens."""
    with patch(
        "app.agents.orchestrator.run_devils_advocate",
        new=AsyncMock(return_value=_sample_devil_advocate_analysis()),
    ) as mocked:
        yield mocked


@pytest.fixture(autouse=True)
def mock_regret_simulator():
    """Patch the Strands agent call site so no real Bedrock call ever happens."""
    with patch(
        "app.agents.orchestrator.run_regret_simulator",
        new=AsyncMock(return_value=_sample_regret_simulation()),
    ) as mocked:
        yield mocked


@pytest.fixture(autouse=True)
def mock_threshold_engine():
    """Patch the Strands agent call site so no real Bedrock call ever happens."""
    with patch(
        "app.agents.orchestrator.run_threshold_engine",
        new=AsyncMock(return_value=_sample_threshold_analysis()),
    ) as mocked:
        yield mocked


async def _experiment_plan_side_effect(
    decision_analysis, assumptions, blindspots, evidence_findings, challenges, regret_scenarios,
    thresholds,
):
    """Build an ExperimentPlan whose target_threshold_id is the REAL,
    persisted threshold id the orchestrator actually passed in - mirroring
    what a real agent call would receive, since the orchestrator only
    persists experiments that target a real threshold."""
    target_id = str(thresholds[0].id) if thresholds else "threshold-1"
    return _sample_experiment_plan(target_threshold_id=target_id)


@pytest.fixture(autouse=True)
def mock_experiment_planner():
    """Patch the Strands agent call site so no real Bedrock call ever happens."""
    with patch(
        "app.agents.orchestrator.run_experiment_planner",
        new=AsyncMock(side_effect=_experiment_plan_side_effect),
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
    assert stored_run.result["decision_analyzer"]["decision_type"] == "market expansion"
    assert len(stored_run.result["assumption_hunter"]["assumptions"]) == 1
    assert len(stored_run.result["blindspot_hunter"]["blindspots"]) == 1
    assert stored_run.result["evidence_agent"]["findings"] == []
    assert len(stored_run.result["devils_advocate"]["challenges"]) == 1
    assert len(stored_run.result["regret_simulator"]["scenarios"]) == 1
    assert len(stored_run.result["threshold_engine"]["thresholds"]) == 1


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


def test_assumption_hunter_receives_decision_analyzer_output(
    client: TestClient, mock_assumption_hunter: AsyncMock
) -> None:
    """The Assumption Hunter must be called with the Decision Analyzer's own
    structured result - not a fresh/independent re-analysis of anything."""
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    mock_assumption_hunter.assert_awaited_once()
    called_decision_analysis, called_evidence = mock_assumption_hunter.await_args.args
    assert called_decision_analysis == _sample_analysis()
    assert called_evidence == []


def test_assumption_hunter_does_not_invent_a_new_decision_analysis(
    client: TestClient, mock_decision_analyzer: AsyncMock, mock_assumption_hunter: AsyncMock
) -> None:
    """Explicit guard against the Assumption Hunter independently deriving
    its own understanding of the decision: the content the Decision
    Analyzer returned must be exactly what's passed through - unchanged,
    not re-derived. (The orchestrator re-validates the Decision Analyzer's
    output as a defensive step, so the passed-in object is a freshly
    validated copy with identical data, not the same Python instance -
    equality is the correct check here, not identity.)
    """
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    decision_analyzer_result = mock_decision_analyzer.return_value
    passed_in_analysis = mock_assumption_hunter.await_args.args[0]
    assert passed_in_analysis == decision_analyzer_result
    assert passed_in_analysis.model_dump() == decision_analyzer_result.model_dump()


def test_assumptions_are_persisted_as_structured_records(client: TestClient) -> None:
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    stored_assumptions = DecisionRepository().list_assumptions(_UUID(decision_id))
    assert len(stored_assumptions) == 1
    assumption = stored_assumptions[0]
    assert assumption.statement == "Customers will order at least twice per month."
    assert assumption.source == "implicit"
    assert assumption.confidence == 0.45
    assert assumption.evidence_status == "not_addressed"
    assert assumption.dependency == "Business profitability"
    expected_consequence = "Revenue may remain below the required operating margin."
    assert assumption.failure_consequence == expected_consequence


def test_evidence_status_not_addressed_is_correctly_represented(client: TestClient) -> None:
    """Distinguish 'evidence never addressed this' from 'proven false' -
    NOT_ADDRESSED must never be silently coerced into CONTRADICTED."""
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    stored_assumptions = DecisionRepository().list_assumptions(_UUID(decision_id))
    assert stored_assumptions[0].evidence_status == "not_addressed"


def test_evidence_status_supported_is_correctly_represented(client: TestClient) -> None:
    decision_id = _create_decision(client)

    supported_analysis = AssumptionAnalysis(
        assumptions=[
            AssumptionFinding(
                statement="The lease will be signed within 30 days.",
                source=AssumptionSource.EXPLICIT,
                importance=ImportanceLevel.HIGH,
                confidence=0.9,
                evidence_status=AssumptionEvidenceStatus.SUPPORTED,
                dependency="Timeline",
                failure_consequence="The expansion timeline slips.",
            )
        ]
    )
    with patch(
        "app.agents.orchestrator.run_assumption_hunter",
        new=AsyncMock(return_value=supported_analysis),
    ):
        client.post(f"/api/v1/decisions/{decision_id}/analyze")

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    stored_assumptions = DecisionRepository().list_assumptions(_UUID(decision_id))
    assert stored_assumptions[0].evidence_status == "supported"


def test_unsupported_assumptions_are_identified(client: TestClient) -> None:
    """An assumption whose evidence_status is not_addressed and whose
    confidence is low must be identifiable as unsupported from the
    persisted record alone - not lost or flattened in storage."""
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    stored_assumptions = DecisionRepository().list_assumptions(_UUID(decision_id))
    unsupported = [
        a
        for a in stored_assumptions
        if a.evidence_status == "not_addressed" and (a.confidence or 1.0) < 0.5
    ]
    assert len(unsupported) == 1
    assert unsupported[0].statement == "Customers will order at least twice per month."


def test_decision_analyzer_failure_prevents_assumption_hunter_execution(
    client: TestClient, mock_assumption_hunter: AsyncMock
) -> None:
    """If the Decision Analyzer fails, the Assumption Hunter must never run -
    there is nothing valid yet for it to consume."""
    decision_id = _create_decision(client)

    with patch(
        "app.agents.orchestrator.run_decision_analyzer",
        new=AsyncMock(side_effect=RuntimeError("model failure")),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    assert response.json()["status"] == "failed"
    mock_assumption_hunter.assert_not_awaited()


def test_decision_analyzer_invalid_output_prevents_assumption_hunter_execution(
    client: TestClient, mock_assumption_hunter: AsyncMock
) -> None:
    """Same guarantee, but for the 'model returned no structured output'
    failure path rather than an exception from the SDK/model itself."""
    decision_id = _create_decision(client)

    with patch(
        "app.agents.orchestrator.run_decision_analyzer",
        new=AsyncMock(side_effect=ValueError("no structured output")),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    assert response.json()["status"] == "failed"
    mock_assumption_hunter.assert_not_awaited()


def test_assumption_hunter_malformed_output_marks_run_failed(client: TestClient) -> None:
    decision_id = _create_decision(client)

    error = ValueError("Assumption hunter did not return structured output.")
    with patch(
        "app.agents.orchestrator.run_assumption_hunter",
        new=AsyncMock(side_effect=error),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"

    # The Decision Analyzer's own result must still be visible/persisted -
    # only the run as a whole is failed, not silently discarded.
    from uuid import UUID as _UUID

    from app.repositories.analysis_repository import AnalysisRepository

    stored_run = AnalysisRepository().get(_UUID(decision_id), _UUID(body["analysis_run_id"]))
    assert stored_run is not None
    assert stored_run.result is not None
    assert stored_run.result["decision_analyzer"]["decision_type"] == "market expansion"
    assert "assumption_hunter" not in stored_run.result


def test_assumption_hunter_model_failure_marks_run_failed_with_safe_message(
    client: TestClient,
) -> None:
    decision_id = _create_decision(client)

    error = RuntimeError("botocore.exceptions.ClientError: assumption-hunter-secret")
    with patch(
        "app.agents.orchestrator.run_assumption_hunter",
        new=AsyncMock(side_effect=error),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    # No partial/invalid assumptions were ever persisted for this failed step.
    assert DecisionRepository().list_assumptions(_UUID(decision_id)) == []


def test_agent_statuses_reflect_completed_pipeline(client: TestClient) -> None:
    """Structured per-agent status, for future frontend display of
    'Decision Analyzer: completed / Assumption Hunter: completed'."""
    decision_id = _create_decision(client)

    analyze_response = client.post(f"/api/v1/decisions/{decision_id}/analyze")
    run_id = analyze_response.json()["analysis_run_id"]

    from uuid import UUID as _UUID

    from app.repositories.analysis_repository import AnalysisRepository

    stored_run = AnalysisRepository().get(_UUID(decision_id), _UUID(run_id))
    assert stored_run is not None
    assert stored_run.agent_statuses == {
        "decision_analyzer": "completed",
        "assumption_hunter": "completed",
        "blindspot_hunter": "completed",
        "research_agent": "unavailable",
        "evidence_agent": "completed",
        "devils_advocate": "completed",
        "regret_simulator": "completed",
        "threshold_engine": "completed",
        "experiment_planner": "completed",
    }


def test_agent_statuses_reflect_skipped_assumption_hunter_on_decision_analyzer_failure(
    client: TestClient,
) -> None:
    decision_id = _create_decision(client)

    with patch(
        "app.agents.orchestrator.run_decision_analyzer",
        new=AsyncMock(side_effect=RuntimeError("model failure")),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    from uuid import UUID as _UUID

    from app.repositories.analysis_repository import AnalysisRepository

    run_id = response.json()["analysis_run_id"]
    stored_run = AnalysisRepository().get(_UUID(decision_id), _UUID(run_id))
    assert stored_run is not None
    assert stored_run.agent_statuses == {
        "decision_analyzer": "failed",
        "assumption_hunter": "skipped",
        "blindspot_hunter": "skipped",
        "research_agent": "skipped",
        "evidence_agent": "skipped",
        "devils_advocate": "skipped",
        "regret_simulator": "skipped",
        "threshold_engine": "skipped",
        "experiment_planner": "skipped",
    }


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


def test_blindspot_hunter_receives_persisted_assumptions(
    client: TestClient, mock_blindspot_hunter: AsyncMock
) -> None:
    """The Blindspot Hunter must be called with the Decision Analyzer's
    structured result and the *persisted* assumptions (with real ids) -
    not a fresh/independent re-analysis of anything."""
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    mock_blindspot_hunter.assert_awaited_once()
    called_decision_analysis, called_assumptions, called_evidence = (
        mock_blindspot_hunter.await_args.args
    )
    assert called_decision_analysis == _sample_analysis()
    assert called_evidence == []
    assert len(called_assumptions) == 1
    assert called_assumptions[0].statement == "Customers will order at least twice per month."
    assert called_assumptions[0].id is not None  # a real persisted id, not invented


def test_evidence_agent_receives_persisted_assumptions_and_blindspots(
    client: TestClient, mock_evidence_agent: AsyncMock
) -> None:
    """The Evidence Agent must be called with the persisted assumptions and
    blindspots (both with real ids), plus the decision's evidence - not a
    fresh/independent re-analysis of anything."""
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    mock_evidence_agent.assert_awaited_once()
    (
        called_decision_analysis,
        called_assumptions,
        called_blindspots,
        called_evidence,
    ) = mock_evidence_agent.await_args.args
    assert called_decision_analysis == _sample_analysis()
    assert called_evidence == []
    assert len(called_assumptions) == 1
    assert len(called_blindspots) == 1
    assert called_blindspots[0].question == (
        "What happens to unit economics if repeat orders fall below 20%?"
    )
    assert called_blindspots[0].id is not None  # a real persisted id, not invented


def test_full_pipeline_sequencing_decision_to_threshold_engine(
    client: TestClient,
    mock_decision_analyzer: AsyncMock,
    mock_assumption_hunter: AsyncMock,
    mock_blindspot_hunter: AsyncMock,
    mock_evidence_agent: AsyncMock,
    mock_devils_advocate: AsyncMock,
    mock_regret_simulator: AsyncMock,
    mock_threshold_engine: AsyncMock,
) -> None:
    """Verify the full chain runs in order and every downstream agent
    receives upstream structured results, not raw decision text."""
    decision_id = _create_decision(client)

    response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.json()["status"] == "completed"
    mock_decision_analyzer.assert_awaited_once()
    mock_assumption_hunter.assert_awaited_once()
    mock_blindspot_hunter.assert_awaited_once()
    mock_evidence_agent.assert_awaited_once()
    mock_devils_advocate.assert_awaited_once()
    mock_regret_simulator.assert_awaited_once()
    mock_threshold_engine.assert_awaited_once()


def test_blindspots_are_persisted_as_structured_records(client: TestClient) -> None:
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    stored_blindspots = DecisionRepository().list_blindspots(_UUID(decision_id))
    assert len(stored_blindspots) == 1
    blindspot = stored_blindspots[0]
    assert blindspot.question == (
        "What happens to unit economics if repeat orders fall below 20%?"
    )
    assert blindspot.category == "untested_assumption"
    assert blindspot.confidence == 0.7
    assert blindspot.evidence_status == "not_addressed"


def test_evidence_findings_are_persisted_separately_from_evidence(client: TestClient) -> None:
    """Evidence findings must be persisted under their own key
    (EVIDENCE_FINDING#), never overwriting the original Evidence record."""
    decision_id = _create_decision(client)

    evidence_item = {
        "evidence_id": str(uuid4()),
        "claim": "Downtown foot traffic supports a second location.",
        "support_level": "supports",
        "credibility": "medium",
        "related_assumption_ids": [],
        "related_blindspot_ids": [],
        "explanation": "The report shows a year-over-year increase in foot traffic.",
        "excerpt": "Downtown foot traffic rose 12% year over year.",
    }
    with patch(
        "app.agents.orchestrator.run_evidence_agent",
        new=AsyncMock(
            return_value=EvidenceAnalysis(
                findings=[EvidenceFinding.model_validate(evidence_item)]
            )
        ),
    ):
        client.post(f"/api/v1/decisions/{decision_id}/analyze")

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository
    from app.repositories.evidence_repository import EvidenceRepository

    # The evidence_id referenced above was never actually uploaded, so the
    # orchestrator must have dropped the finding rather than persist a
    # dangling reference - this is exercised fully in the fabricated-id
    # test below. Here we only assert the persistence *path* used is the
    # dedicated one, not a mutation of EvidenceRepository.
    assert DecisionRepository().list_evidence_findings(_UUID(decision_id)) == []
    assert EvidenceRepository().list_for_decision(_UUID(decision_id)) == []


def test_evidence_agent_fabricated_evidence_id_is_dropped(client: TestClient) -> None:
    """A finding referencing an evidence_id that was never actually given
    to the agent must never be persisted - that would be exactly the kind
    of fabricated source the Evidence Agent must not produce."""
    decision_id = _create_decision(client)

    fabricated_finding = EvidenceFinding(
        evidence_id=str(uuid4()),  # not a real evidence id for this decision
        claim="Some claim.",
        support_level=EvidenceSupportLevel.SUPPORTS,
        credibility=EvidenceCredibility.HIGH,
        related_assumption_ids=[],
        related_blindspot_ids=[],
        explanation="Fabricated - should be dropped.",
    )
    with patch(
        "app.agents.orchestrator.run_evidence_agent",
        new=AsyncMock(return_value=EvidenceAnalysis(findings=[fabricated_finding])),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.json()["status"] == "completed"

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    assert DecisionRepository().list_evidence_findings(_UUID(decision_id)) == []


def test_blindspot_hunter_failure_skips_evidence_agent_and_preserves_prior_results(
    client: TestClient, mock_evidence_agent: AsyncMock
) -> None:
    decision_id = _create_decision(client)

    error = ValueError("Blindspot hunter did not return structured output.")
    with patch(
        "app.agents.orchestrator.run_blindspot_hunter",
        new=AsyncMock(side_effect=error),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    mock_evidence_agent.assert_not_awaited()

    from uuid import UUID as _UUID

    from app.repositories.analysis_repository import AnalysisRepository

    stored_run = AnalysisRepository().get(_UUID(decision_id), _UUID(body["analysis_run_id"]))
    assert stored_run is not None
    assert stored_run.result is not None
    assert stored_run.result["decision_analyzer"]["decision_type"] == "market expansion"
    assert len(stored_run.result["assumption_hunter"]["assumptions"]) == 1
    assert "blindspot_hunter" not in stored_run.result
    assert "evidence_agent" not in stored_run.result
    assert stored_run.agent_statuses == {
        "decision_analyzer": "completed",
        "assumption_hunter": "completed",
        "blindspot_hunter": "failed",
        "research_agent": "skipped",
        "evidence_agent": "skipped",
        "devils_advocate": "skipped",
        "regret_simulator": "skipped",
        "threshold_engine": "skipped",
        "experiment_planner": "skipped",
    }


def test_evidence_agent_failure_preserves_prior_results(client: TestClient) -> None:
    decision_id = _create_decision(client)

    error = RuntimeError("botocore.exceptions.ClientError: evidence-agent-secret")
    with patch(
        "app.agents.orchestrator.run_evidence_agent",
        new=AsyncMock(side_effect=error),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"

    from uuid import UUID as _UUID

    from app.repositories.analysis_repository import AnalysisRepository
    from app.repositories.decision_repository import DecisionRepository

    stored_run = AnalysisRepository().get(_UUID(decision_id), _UUID(body["analysis_run_id"]))
    assert stored_run is not None
    assert stored_run.result is not None
    assert len(stored_run.result["blindspot_hunter"]["blindspots"]) == 1
    assert "evidence_agent" not in stored_run.result
    # The blindspots that *did* run successfully must still be persisted.
    assert len(DecisionRepository().list_blindspots(_UUID(decision_id))) == 1


def test_assumption_hunter_failure_skips_blindspot_and_evidence_stages(
    client: TestClient, mock_blindspot_hunter: AsyncMock, mock_evidence_agent: AsyncMock
) -> None:
    decision_id = _create_decision(client)

    error = ValueError("Assumption hunter did not return structured output.")
    with patch(
        "app.agents.orchestrator.run_assumption_hunter",
        new=AsyncMock(side_effect=error),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.json()["status"] == "failed"
    mock_blindspot_hunter.assert_not_awaited()
    mock_evidence_agent.assert_not_awaited()

    from uuid import UUID as _UUID

    from app.repositories.analysis_repository import AnalysisRepository

    run_id = response.json()["analysis_run_id"]
    stored_run = AnalysisRepository().get(_UUID(decision_id), _UUID(run_id))
    assert stored_run is not None
    assert stored_run.agent_statuses == {
        "decision_analyzer": "completed",
        "assumption_hunter": "failed",
        "blindspot_hunter": "skipped",
        "research_agent": "skipped",
        "evidence_agent": "skipped",
        "devils_advocate": "skipped",
        "regret_simulator": "skipped",
        "threshold_engine": "skipped",
        "experiment_planner": "skipped",
    }


def test_devils_advocate_receives_persisted_upstream_records(
    client: TestClient, mock_devils_advocate: AsyncMock
) -> None:
    """The Devil's Advocate must be called with the Decision Analyzer's
    structured result and the *persisted* assumptions/blindspots/evidence
    findings (with real ids) - not a fresh/independent re-analysis."""
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    mock_devils_advocate.assert_awaited_once()
    (
        called_decision_analysis,
        called_assumptions,
        called_blindspots,
        called_evidence_findings,
    ) = mock_devils_advocate.await_args.args
    assert called_decision_analysis == _sample_analysis()
    assert len(called_assumptions) == 1
    assert called_assumptions[0].id is not None
    assert len(called_blindspots) == 1
    assert called_blindspots[0].id is not None
    assert called_evidence_findings == []


def test_regret_simulator_receives_persisted_upstream_records_including_challenges(
    client: TestClient, mock_regret_simulator: AsyncMock
) -> None:
    """The Regret Simulator must be called with the persisted assumptions,
    blindspots, evidence findings, and challenges (all with real ids)."""
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    mock_regret_simulator.assert_awaited_once()
    (
        called_decision_analysis,
        called_assumptions,
        called_blindspots,
        called_evidence_findings,
        called_challenges,
    ) = mock_regret_simulator.await_args.args
    assert called_decision_analysis == _sample_analysis()
    assert len(called_assumptions) == 1
    assert len(called_blindspots) == 1
    assert called_evidence_findings == []
    assert len(called_challenges) == 1
    assert called_challenges[0].id is not None
    assert called_challenges[0].claim == (
        "Repeat customers will be high enough to sustain the business."
    )


def test_threshold_engine_receives_persisted_upstream_records_including_regret_scenarios(
    client: TestClient, mock_threshold_engine: AsyncMock
) -> None:
    """The Threshold Engine must be called with the persisted assumptions,
    blindspots, evidence findings, challenges, and regret scenarios (all
    with real ids)."""
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    mock_threshold_engine.assert_awaited_once()
    (
        called_decision_analysis,
        called_assumptions,
        called_blindspots,
        called_evidence_findings,
        called_challenges,
        called_regret_scenarios,
    ) = mock_threshold_engine.await_args.args
    assert called_decision_analysis == _sample_analysis()
    assert len(called_assumptions) == 1
    assert len(called_blindspots) == 1
    assert called_evidence_findings == []
    assert len(called_challenges) == 1
    assert len(called_regret_scenarios) == 1
    assert called_regret_scenarios[0].id is not None
    assert called_regret_scenarios[0].title == "Adoption failure"


def test_challenges_are_persisted_as_structured_records(client: TestClient) -> None:
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    stored_challenges = DecisionRepository().list_challenges(_UUID(decision_id))
    assert len(stored_challenges) == 1
    challenge = stored_challenges[0]
    assert challenge.claim == "Repeat customers will be high enough to sustain the business."
    assert challenge.severity == "critical"
    assert challenge.confidence == 0.7


def test_regret_scenarios_are_persisted_with_fresh_ids_not_agents_response_scoped_id(
    client: TestClient,
) -> None:
    """The agent's own response-scoped `id` (e.g. 'scenario-1') must never
    leak into storage - a real, persisted UUID must be assigned instead."""
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    stored_scenarios = DecisionRepository().list_regret_scenarios(_UUID(decision_id))
    assert len(stored_scenarios) == 1
    scenario = stored_scenarios[0]
    assert scenario.title == "Adoption failure"
    assert scenario.trigger_variable == "Repeat-order rate"
    assert scenario.trigger_direction == "below"
    assert scenario.probability_band == "unknown"
    assert scenario.impact == "severe"
    # `scenario.id` is a real UUID assigned at persistence, never the
    # agent's own "scenario-1" response-scoped label.
    assert str(scenario.id) != "scenario-1"
    _UUID(str(scenario.id))  # well-formed UUID


def test_devils_advocate_challenge_with_unrecognized_related_ids_are_dropped(
    client: TestClient,
) -> None:
    """A challenge referencing an assumption/blindspot/evidence-finding id
    that was never actually given to the agent must have that dangling
    reference dropped before persistence - never a fabricated relationship."""
    decision_id = _create_decision(client)

    fabricated_challenge = Challenge(
        claim="Some claim.",
        attack="Some attack.",
        severity=SeverityLevel.MEDIUM,
        confidence=0.5,
        related_assumption_ids=[str(uuid4())],  # not a real, persisted id
        related_blindspot_ids=[str(uuid4())],  # not a real, persisted id
        related_evidence_finding_ids=[str(uuid4())],  # not a real, persisted id
        failure_mechanism="Some mechanism.",
        evidence_basis="Some basis.",
    )
    with patch(
        "app.agents.orchestrator.run_devils_advocate",
        new=AsyncMock(
            return_value=DevilAdvocateAnalysis(
                overall_challenge="x", challenges=[fabricated_challenge]
            )
        ),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.json()["status"] == "completed"

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    stored_challenges = DecisionRepository().list_challenges(_UUID(decision_id))
    assert len(stored_challenges) == 1
    assert stored_challenges[0].related_assumption_ids == []
    assert stored_challenges[0].related_blindspot_ids == []
    assert stored_challenges[0].related_evidence_finding_ids == []


def test_devils_advocate_failure_skips_regret_simulator_and_preserves_prior_results(
    client: TestClient, mock_regret_simulator: AsyncMock
) -> None:
    decision_id = _create_decision(client)

    error = ValueError("Devil's advocate did not return structured output.")
    with patch(
        "app.agents.orchestrator.run_devils_advocate",
        new=AsyncMock(side_effect=error),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    mock_regret_simulator.assert_not_awaited()

    from uuid import UUID as _UUID

    from app.repositories.analysis_repository import AnalysisRepository
    from app.repositories.decision_repository import DecisionRepository

    stored_run = AnalysisRepository().get(_UUID(decision_id), _UUID(body["analysis_run_id"]))
    assert stored_run is not None
    assert stored_run.result is not None
    assert len(stored_run.result["evidence_agent"]["findings"]) == 0
    assert "devils_advocate" not in stored_run.result
    assert "regret_simulator" not in stored_run.result
    assert stored_run.agent_statuses == {
        "decision_analyzer": "completed",
        "assumption_hunter": "completed",
        "blindspot_hunter": "completed",
        "research_agent": "unavailable",
        "evidence_agent": "completed",
        "devils_advocate": "failed",
        "regret_simulator": "skipped",
        "threshold_engine": "skipped",
        "experiment_planner": "skipped",
    }
    # Blindspots that already succeeded must still be persisted.
    assert len(DecisionRepository().list_blindspots(_UUID(decision_id))) == 1


def test_regret_simulator_failure_preserves_all_prior_results(client: TestClient) -> None:
    decision_id = _create_decision(client)

    error = RuntimeError("botocore.exceptions.ClientError: regret-simulator-secret")
    with patch(
        "app.agents.orchestrator.run_regret_simulator",
        new=AsyncMock(side_effect=error),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert "regret-simulator-secret" not in str(body)

    from uuid import UUID as _UUID

    from app.repositories.analysis_repository import AnalysisRepository
    from app.repositories.decision_repository import DecisionRepository

    stored_run = AnalysisRepository().get(_UUID(decision_id), _UUID(body["analysis_run_id"]))
    assert stored_run is not None
    assert stored_run.result is not None
    assert len(stored_run.result["devils_advocate"]["challenges"]) == 1
    assert "regret_simulator" not in stored_run.result
    # The challenge that did run successfully must still be persisted.
    assert len(DecisionRepository().list_challenges(_UUID(decision_id))) == 1
    assert DecisionRepository().list_regret_scenarios(_UUID(decision_id)) == []


def test_thresholds_are_persisted_with_fresh_ids_not_agents_response_scoped_id(
    client: TestClient,
) -> None:
    """The agent's own response-scoped `id` (e.g. 'threshold-1') must never
    leak into storage - a real, persisted UUID must be assigned instead."""
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    stored_thresholds = DecisionRepository().list_thresholds(_UUID(decision_id))
    assert len(stored_thresholds) == 1
    threshold = stored_thresholds[0]
    assert threshold.variable == "Repeat-order rate"
    assert threshold.direction == "below"
    assert threshold.validation_status == "unknown"
    assert threshold.threshold_value is None
    # `threshold.id` is a real UUID assigned at persistence, never the
    # agent's own "threshold-1" response-scoped label.
    assert str(threshold.id) != "threshold-1"
    _UUID(str(threshold.id))  # well-formed UUID


def test_threshold_engine_unrecognized_related_ids_are_dropped(client: TestClient) -> None:
    """A threshold referencing an assumption/regret-scenario id that was
    never actually given to the agent must have that dangling reference
    dropped before persistence - never a fabricated relationship."""
    decision_id = _create_decision(client)

    fabricated_threshold = Threshold(
        id="threshold-1",
        variable="Some variable",
        threshold_type=ThresholdType.QUALITATIVE,
        direction=ThresholdDirection.UNKNOWN,
        confidence=0.5,
        derivation=ThresholdDerivation.QUALITATIVE,
        consequence="x",
        related_assumption_ids=[str(uuid4())],  # not a real, persisted id
        related_regret_scenario_ids=[str(uuid4())],  # not a real, persisted id
        evidence_basis="x",
        validation_status=ThresholdValidationStatus.UNKNOWN,
    )
    with patch(
        "app.agents.orchestrator.run_threshold_engine",
        new=AsyncMock(
            return_value=ThresholdAnalysis(
                thresholds=[fabricated_threshold],
                primary_threshold_id="threshold-1",
                summary="x",
            )
        ),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.json()["status"] == "completed"

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    stored_thresholds = DecisionRepository().list_thresholds(_UUID(decision_id))
    assert len(stored_thresholds) == 1
    assert stored_thresholds[0].related_assumption_ids == []
    assert stored_thresholds[0].related_regret_scenario_ids == []


def test_threshold_engine_failure_preserves_all_prior_results(client: TestClient) -> None:
    decision_id = _create_decision(client)

    error = RuntimeError("botocore.exceptions.ClientError: threshold-engine-secret")
    with patch(
        "app.agents.orchestrator.run_threshold_engine",
        new=AsyncMock(side_effect=error),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert "threshold-engine-secret" not in str(body)

    from uuid import UUID as _UUID

    from app.repositories.analysis_repository import AnalysisRepository
    from app.repositories.decision_repository import DecisionRepository

    stored_run = AnalysisRepository().get(_UUID(decision_id), _UUID(body["analysis_run_id"]))
    assert stored_run is not None
    assert stored_run.result is not None
    assert len(stored_run.result["regret_simulator"]["scenarios"]) == 1
    assert "threshold_engine" not in stored_run.result
    assert stored_run.agent_statuses == {
        "decision_analyzer": "completed",
        "assumption_hunter": "completed",
        "blindspot_hunter": "completed",
        "research_agent": "unavailable",
        "evidence_agent": "completed",
        "devils_advocate": "completed",
        "regret_simulator": "completed",
        "threshold_engine": "failed",
        "experiment_planner": "skipped",
    }
    # The regret scenario that did run successfully must still be persisted.
    assert len(DecisionRepository().list_regret_scenarios(_UUID(decision_id))) == 1
    assert DecisionRepository().list_thresholds(_UUID(decision_id)) == []


def test_threshold_engine_invalid_output_marks_run_failed(client: TestClient) -> None:
    """Same guarantee, but for the 'model returned no structured output'
    failure path rather than an exception from the SDK/model itself."""
    decision_id = _create_decision(client)

    error = ValueError("Threshold engine did not return structured output.")
    with patch(
        "app.agents.orchestrator.run_threshold_engine",
        new=AsyncMock(side_effect=error),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    assert response.json()["status"] == "failed"

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    assert DecisionRepository().list_thresholds(_UUID(decision_id)) == []


def test_experiment_planner_receives_persisted_upstream_records_including_thresholds(
    client: TestClient, mock_experiment_planner: AsyncMock
) -> None:
    """The Experiment Planner must be called with the persisted assumptions,
    blindspots, evidence findings, challenges, regret scenarios, and
    thresholds (all with real ids)."""
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    mock_experiment_planner.assert_awaited_once()
    (
        called_decision_analysis,
        called_assumptions,
        called_blindspots,
        called_evidence_findings,
        called_challenges,
        called_regret_scenarios,
        called_thresholds,
    ) = mock_experiment_planner.await_args.args
    assert called_decision_analysis == _sample_analysis()
    assert len(called_assumptions) == 1
    assert len(called_blindspots) == 1
    assert called_evidence_findings == []
    assert len(called_challenges) == 1
    assert len(called_regret_scenarios) == 1
    assert len(called_thresholds) == 1
    assert called_thresholds[0].id is not None
    assert called_thresholds[0].variable == "Repeat-order rate"


def test_full_pipeline_sequencing_through_experiment_planner(
    client: TestClient,
    mock_decision_analyzer: AsyncMock,
    mock_assumption_hunter: AsyncMock,
    mock_blindspot_hunter: AsyncMock,
    mock_evidence_agent: AsyncMock,
    mock_devils_advocate: AsyncMock,
    mock_regret_simulator: AsyncMock,
    mock_threshold_engine: AsyncMock,
    mock_experiment_planner: AsyncMock,
) -> None:
    """Verify the complete 8-agent chain runs in order and every downstream
    agent receives upstream structured results, not raw decision text."""
    decision_id = _create_decision(client)

    response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.json()["status"] == "completed"
    mock_decision_analyzer.assert_awaited_once()
    mock_assumption_hunter.assert_awaited_once()
    mock_blindspot_hunter.assert_awaited_once()
    mock_evidence_agent.assert_awaited_once()
    mock_devils_advocate.assert_awaited_once()
    mock_regret_simulator.assert_awaited_once()
    mock_threshold_engine.assert_awaited_once()
    mock_experiment_planner.assert_awaited_once()


def test_experiments_are_persisted_with_fresh_ids_not_agents_response_scoped_id(
    client: TestClient,
) -> None:
    """The agent's own response-scoped `id` (e.g. 'experiment-1') must never
    leak into storage - a real, persisted UUID must be assigned instead."""
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    stored_experiments = DecisionRepository().list_experiments(_UUID(decision_id))
    assert len(stored_experiments) == 1
    experiment = stored_experiments[0]
    assert experiment.title == "14-day limited delivery pilot"
    assert experiment.variable_to_test == "Repeat-order rate"
    assert experiment.status == "recommended"
    assert experiment.duration_days == 14
    # `experiment.id` is a real UUID assigned at persistence, never the
    # agent's own "experiment-1" response-scoped label.
    assert str(experiment.id) != "experiment-1"
    _UUID(str(experiment.id))  # well-formed UUID

    # target_threshold_id must be the real, persisted threshold id.
    stored_thresholds = DecisionRepository().list_thresholds(_UUID(decision_id))
    assert experiment.target_threshold_id == str(stored_thresholds[0].id)


def test_experiment_with_fabricated_target_threshold_id_is_dropped(client: TestClient) -> None:
    """An experiment referencing a target_threshold_id that was never
    actually given to the agent must never be persisted - every
    recommended experiment must target a real threshold."""
    decision_id = _create_decision(client)

    fabricated_experiment = Experiment(
        id="experiment-1",
        title="x",
        objective="x",
        hypothesis="x",
        target_threshold_id=str(uuid4()),  # not a real, persisted threshold id
        variable_to_test="x",
        experiment_type=ExperimentType.SURVEY,
        steps=["x"],
        success_criteria=["x"],
        failure_criteria=["x"],
        duration_days=None,
        estimated_cost=None,
        currency=None,
        evidence_to_collect=["x"],
        decision_rule="x",
        expected_information_gain=InformationGain.LOW,
        confidence=0.5,
        feasibility=Feasibility.MEDIUM,
        reversibility=Reversibility.HIGH,
        related_assumption_ids=[],
        related_regret_scenario_ids=[],
    )
    with patch(
        "app.agents.orchestrator.run_experiment_planner",
        new=AsyncMock(
            return_value=ExperimentPlan(
                experiments=[fabricated_experiment],
                recommended_experiment_id="experiment-1",
                summary="x",
            )
        ),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.json()["status"] == "completed"

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    assert DecisionRepository().list_experiments(_UUID(decision_id)) == []


def test_decision_status_becomes_needs_validation_when_experiment_recommended(
    client: TestClient,
) -> None:
    """A completed analysis that produces at least one recommended
    experiment must move the decision to needs_validation - never
    'approved' or 'rejected'."""
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    response = client.get(f"/api/v1/decisions/{decision_id}")
    assert response.json()["status"] == "needs_validation"


def test_decision_status_unchanged_when_no_experiments_recommended(client: TestClient) -> None:
    """If the Experiment Planner recommends nothing (e.g. every experiment
    was dropped as fabricated, or none were returned), the decision status
    must not be force-changed to needs_validation."""
    decision_id = _create_decision(client)

    with patch(
        "app.agents.orchestrator.run_experiment_planner",
        new=AsyncMock(return_value=ExperimentPlan(experiments=[], summary="Nothing to test yet.")),
    ):
        client.post(f"/api/v1/decisions/{decision_id}/analyze")

    response = client.get(f"/api/v1/decisions/{decision_id}")
    assert response.json()["status"] == "draft"


def test_experiment_planner_failure_preserves_all_prior_results(client: TestClient) -> None:
    decision_id = _create_decision(client)

    error = RuntimeError("botocore.exceptions.ClientError: experiment-planner-secret")
    with patch(
        "app.agents.orchestrator.run_experiment_planner",
        new=AsyncMock(side_effect=error),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert "experiment-planner-secret" not in str(body)

    from uuid import UUID as _UUID

    from app.repositories.analysis_repository import AnalysisRepository
    from app.repositories.decision_repository import DecisionRepository

    stored_run = AnalysisRepository().get(_UUID(decision_id), _UUID(body["analysis_run_id"]))
    assert stored_run is not None
    assert stored_run.result is not None
    assert len(stored_run.result["threshold_engine"]["thresholds"]) == 1
    assert "experiment_planner" not in stored_run.result
    assert stored_run.agent_statuses == {
        "decision_analyzer": "completed",
        "assumption_hunter": "completed",
        "blindspot_hunter": "completed",
        "research_agent": "unavailable",
        "evidence_agent": "completed",
        "devils_advocate": "completed",
        "regret_simulator": "completed",
        "threshold_engine": "completed",
        "experiment_planner": "failed",
    }
    # The threshold that did run successfully must still be persisted.
    assert len(DecisionRepository().list_thresholds(_UUID(decision_id))) == 1
    assert DecisionRepository().list_experiments(_UUID(decision_id)) == []
    # A failed run must never move the decision toward needs_validation.
    response = client.get(f"/api/v1/decisions/{decision_id}")
    assert response.json()["status"] == "draft"


def test_experiment_planner_invalid_output_marks_run_failed(client: TestClient) -> None:
    """Same guarantee, but for the 'model returned no structured output'
    failure path rather than an exception from the SDK/model itself."""
    decision_id = _create_decision(client)

    error = ValueError("Experiment planner did not return structured output.")
    with patch(
        "app.agents.orchestrator.run_experiment_planner",
        new=AsyncMock(side_effect=error),
    ):
        response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.status_code == 201
    assert response.json()["status"] == "failed"

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    assert DecisionRepository().list_experiments(_UUID(decision_id)) == []


def test_list_experiments_api_returns_recommended_experiment(client: TestClient) -> None:
    decision_id = _create_decision(client)

    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    response = client.get(f"/api/v1/decisions/{decision_id}/experiments")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "14-day limited delivery pilot"


def test_list_experiments_api_requires_ownership(client: TestClient) -> None:
    decision_id = _create_decision(client)
    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    from app.dependencies.auth import get_current_user_id
    from app.main import app

    app.dependency_overrides[get_current_user_id] = lambda: "someone-else"
    try:
        response = client.get(f"/api/v1/decisions/{decision_id}/experiments")
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)

    assert response.status_code == 404


def test_get_experiment_by_id_api(client: TestClient) -> None:
    decision_id = _create_decision(client)
    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    stored_experiments = DecisionRepository().list_experiments(_UUID(decision_id))
    experiment_id = stored_experiments[0].id

    response = client.get(f"/api/v1/experiments/{experiment_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(experiment_id)
    assert response.json()["title"] == "14-day limited delivery pilot"


def test_get_experiment_by_id_missing_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/experiments/{uuid4()}")

    assert response.status_code == 404


def test_get_experiment_by_id_requires_ownership(client: TestClient) -> None:
    decision_id = _create_decision(client)
    client.post(f"/api/v1/decisions/{decision_id}/analyze")

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    stored_experiments = DecisionRepository().list_experiments(_UUID(decision_id))
    experiment_id = stored_experiments[0].id

    from app.dependencies.auth import get_current_user_id
    from app.main import app

    app.dependency_overrides[get_current_user_id] = lambda: "someone-else"
    try:
        response = client.get(f"/api/v1/experiments/{experiment_id}")
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)

    assert response.status_code == 404


# --- Research Agent pipeline integration ---------------------------------------


def test_research_agent_unavailable_by_default_does_not_block_pipeline(client: TestClient) -> None:
    """With no research provider configured (the default), the Research
    Agent stage must be marked unavailable and the rest of the pipeline
    must still complete successfully."""
    decision_id = _create_decision(client)

    response = client.post(f"/api/v1/decisions/{decision_id}/analyze")

    assert response.json()["status"] == "completed"

    from uuid import UUID as _UUID

    from app.repositories.analysis_repository import AnalysisRepository

    run_id = response.json()["analysis_run_id"]
    stored_run = AnalysisRepository().get(_UUID(decision_id), _UUID(run_id))
    assert stored_run is not None
    assert stored_run.agent_statuses["research_agent"] == "unavailable"
    assert "research_agent" not in stored_run.result  # nothing persisted when unavailable


def test_research_agent_enabled_persists_external_evidence_separately_from_user_evidence(
    client: TestClient,
) -> None:
    """When a research provider IS configured and returns real findings,
    external evidence must be persisted under its own entity, distinct
    from user-uploaded Evidence, and the pipeline must still reach
    completion."""
    from app.agents.research_agent import ResearchMapping, ResearchQueryPlan
    from app.agents.schemas import ExternalEvidence as AgentExternalEvidence
    from app.agents.schemas import ExternalEvidenceSupportLevel
    from app.dependencies.analysis import get_research_service
    from app.main import app
    from app.research.schemas import ResearchResult
    from app.research.service import ResearchService

    decision_id = _create_decision(client)

    fake_result = ResearchResult(
        title="Repeat-purchase behavior report",
        url="https://example.com/report",
        source_name="example.com",
        snippet="Repeat purchase rates vary substantially by category.",
        retrieved_at=datetime.now(UTC),
        query="repeat purchase behavior",
    )
    stub_provider = AsyncMock()
    stub_provider.search = AsyncMock(return_value=[fake_result])
    research_service = ResearchService(provider=stub_provider)

    query_plan = ResearchQueryPlan(
        queries=["repeat purchase behavior"], rationale="Critical gap in evidence."
    )
    mapping = ResearchMapping(
        findings=[
            AgentExternalEvidence(
                research_result_id=str(fake_result.id),
                claim="Repeat customers will order at least twice per month.",
                support_level=ExternalEvidenceSupportLevel.CONTEXTUAL,
                credibility=EvidenceCredibility.MEDIUM,
                explanation="The source discusses general repeat-purchase variability, not "
                "this business's specific rate.",
                excerpt="Repeat purchase rates vary substantially by category.",
            )
        ],
        unresolved_questions=[],
        summary="External research provided context only.",
    )

    query_agent_mock = AsyncMock()
    query_agent_mock.invoke_async = AsyncMock(
        return_value=type("Result", (), {"structured_output": query_plan})()
    )
    mapping_agent_mock = AsyncMock()
    mapping_agent_mock.invoke_async = AsyncMock(
        return_value=type("Result", (), {"structured_output": mapping})()
    )

    app.dependency_overrides[get_research_service] = lambda: research_service
    try:
        with (
            patch(
                "app.agents.research_agent.build_research_query_agent",
                return_value=query_agent_mock,
            ),
            patch(
                "app.agents.research_agent.build_research_mapping_agent",
                return_value=mapping_agent_mock,
            ),
        ):
            response = client.post(f"/api/v1/decisions/{decision_id}/analyze")
    finally:
        app.dependency_overrides.pop(get_research_service, None)

    assert response.json()["status"] == "completed"

    from uuid import UUID as _UUID

    from app.repositories.analysis_repository import AnalysisRepository
    from app.repositories.decision_repository import DecisionRepository
    from app.repositories.evidence_repository import EvidenceRepository

    run_id = response.json()["analysis_run_id"]
    stored_run = AnalysisRepository().get(_UUID(decision_id), _UUID(run_id))
    assert stored_run is not None
    assert stored_run.agent_statuses["research_agent"] == "completed"
    assert len(stored_run.result["research_agent"]["findings"]) == 1

    external_evidence = DecisionRepository().list_external_evidence(_UUID(decision_id))
    assert len(external_evidence) == 1
    assert external_evidence[0].source_url == "https://example.com/report"
    assert external_evidence[0].source_name == "example.com"
    assert external_evidence[0].support_level == "contextual"

    # External evidence must never appear in (or overwrite) user-uploaded evidence.
    user_evidence = EvidenceRepository().list_for_decision(_UUID(decision_id))
    assert user_evidence == []


def test_research_agent_findings_with_fabricated_result_id_are_dropped(client: TestClient) -> None:
    """A finding referencing a research_result_id that was never actually
    retrieved this run must never be persisted - the same fabrication
    guard already used for the Evidence Agent's evidence_id."""
    from app.agents.research_agent import ResearchMapping, ResearchQueryPlan
    from app.agents.schemas import ExternalEvidence as AgentExternalEvidence
    from app.agents.schemas import ExternalEvidenceSupportLevel
    from app.dependencies.analysis import get_research_service
    from app.main import app
    from app.research.schemas import ResearchResult
    from app.research.service import ResearchService

    decision_id = _create_decision(client)

    real_result = ResearchResult(
        title="Real result",
        url="https://example.com/real",
        source_name="example.com",
        snippet="A real snippet.",
        retrieved_at=datetime.now(UTC),
        query="q",
    )
    stub_provider = AsyncMock()
    stub_provider.search = AsyncMock(return_value=[real_result])
    research_service = ResearchService(provider=stub_provider)

    fabricated_finding = AgentExternalEvidence(
        research_result_id=str(uuid4()),  # not the real_result's id
        claim="x",
        support_level=ExternalEvidenceSupportLevel.SUPPORTS,
        credibility=EvidenceCredibility.HIGH,
        explanation="Fabricated - should be dropped.",
    )

    query_agent_mock = AsyncMock()
    query_agent_mock.invoke_async = AsyncMock(
        return_value=type(
            "Result", (), {"structured_output": ResearchQueryPlan(queries=["q"], rationale="x")}
        )()
    )
    mapping_agent_mock = AsyncMock()
    mapping_agent_mock.invoke_async = AsyncMock(
        return_value=type(
            "Result",
            (),
            {
                "structured_output": ResearchMapping(
                    findings=[fabricated_finding], unresolved_questions=[], summary="x"
                )
            },
        )()
    )

    app.dependency_overrides[get_research_service] = lambda: research_service
    try:
        with (
            patch(
                "app.agents.research_agent.build_research_query_agent",
                return_value=query_agent_mock,
            ),
            patch(
                "app.agents.research_agent.build_research_mapping_agent",
                return_value=mapping_agent_mock,
            ),
        ):
            response = client.post(f"/api/v1/decisions/{decision_id}/analyze")
    finally:
        app.dependency_overrides.pop(get_research_service, None)

    assert response.json()["status"] == "completed"

    from uuid import UUID as _UUID

    from app.repositories.decision_repository import DecisionRepository

    assert DecisionRepository().list_external_evidence(_UUID(decision_id)) == []


def test_research_agent_provider_failure_marks_unavailable_not_failed(client: TestClient) -> None:
    """A provider that fails on every query must mark the stage
    `unavailable`, never `failed` - and must never block the rest of the
    pipeline from completing."""
    from app.dependencies.analysis import get_research_service
    from app.main import app
    from app.research.service import ResearchService

    decision_id = _create_decision(client)

    failing_provider = AsyncMock()
    failing_provider.search = AsyncMock(side_effect=RuntimeError("provider exploded"))
    research_service = ResearchService(provider=failing_provider)

    from app.agents.research_agent import ResearchQueryPlan

    query_agent_mock = AsyncMock()
    query_agent_mock.invoke_async = AsyncMock(
        return_value=type(
            "Result", (), {"structured_output": ResearchQueryPlan(queries=["q"], rationale="x")}
        )()
    )

    app.dependency_overrides[get_research_service] = lambda: research_service
    try:
        with patch(
            "app.agents.research_agent.build_research_query_agent", return_value=query_agent_mock
        ):
            response = client.post(f"/api/v1/decisions/{decision_id}/analyze")
    finally:
        app.dependency_overrides.pop(get_research_service, None)

    assert response.json()["status"] == "completed"

    from uuid import UUID as _UUID

    from app.repositories.analysis_repository import AnalysisRepository

    run_id = response.json()["analysis_run_id"]
    stored_run = AnalysisRepository().get(_UUID(decision_id), _UUID(run_id))
    assert stored_run is not None
    assert stored_run.agent_statuses["research_agent"] == "unavailable"
