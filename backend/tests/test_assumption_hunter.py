"""Tests for the Assumption Hunter agent module itself.

Focused on the parts that don't require invoking a real model: prompt
construction and the structured schemas. No Bedrock call happens anywhere
in this file.
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.agents.assumption_hunter import build_assumption_prompt
from app.agents.schemas import (
    Assumption,
    AssumptionAnalysis,
    AssumptionEvidenceStatus,
    AssumptionFinding,
    AssumptionSource,
    ConfidenceLevel,
    DecisionAnalysis,
    ImportanceLevel,
    InformationClassification,
)
from app.schemas.decision_resources import Evidence, SourceType


def _sample_decision_analysis() -> DecisionAnalysis:
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


def _sample_evidence() -> Evidence:
    return Evidence(
        id=uuid4(),
        decision_id=uuid4(),
        title="Foot traffic report",
        source_type=SourceType.DOCUMENT,
        content_reference="Downtown foot traffic rose 12% year over year.",
        created_at=datetime.now(UTC),
    )


def test_prompt_is_built_from_decision_analysis_not_raw_decision() -> None:
    """The prompt must be built from the structured DecisionAnalysis fields,
    never from raw decision text the Decision Analyzer was never given
    access to at this point in the pipeline."""
    analysis = _sample_decision_analysis()

    prompt = build_assumption_prompt(analysis, evidence=[])

    assert analysis.decision_summary in prompt
    assert analysis.goal in prompt
    assert "Limited capital" in prompt
    assert "Foot traffic downtown" in prompt
    # The prompt-building function only accepts a DecisionAnalysis + evidence
    # list as parameters - there is no code path here that could reach back
    # into raw decision fields like title/description/budget, since those
    # were never passed in. This assertion documents that intent alongside
    # the signature itself.
    import inspect

    from app.agents.assumption_hunter import build_assumption_prompt as fn

    signature = inspect.signature(fn)
    assert list(signature.parameters) == ["decision_analysis", "evidence"]


def test_prompt_includes_evidence_when_present() -> None:
    analysis = _sample_decision_analysis()
    evidence = _sample_evidence()

    prompt = build_assumption_prompt(analysis, evidence=[evidence])

    assert "Foot traffic report" in prompt
    assert "Downtown foot traffic rose 12%" in prompt


def test_prompt_states_no_evidence_when_none_submitted() -> None:
    analysis = _sample_decision_analysis()

    prompt = build_assumption_prompt(analysis, evidence=[])

    assert "No evidence has been submitted" in prompt


def test_prompt_surfaces_decision_analyzers_prior_assumptions() -> None:
    analysis = _sample_decision_analysis()

    prompt = build_assumption_prompt(analysis, evidence=[])

    assert "Downtown foot traffic is high enough to sustain a second store." in prompt
    assert "Actual downtown lease rates were not provided." in prompt


def test_assumption_finding_schema_accepts_valid_data() -> None:
    finding = AssumptionFinding(
        statement="Customers will order at least twice per month.",
        source=AssumptionSource.IMPLICIT,
        importance=ImportanceLevel.CRITICAL,
        confidence=0.45,
        evidence_status=AssumptionEvidenceStatus.NOT_ADDRESSED,
        dependency="Business profitability",
        failure_consequence="Revenue may remain below the required operating margin.",
    )

    assert finding.confidence == 0.45
    assert finding.evidence_status is AssumptionEvidenceStatus.NOT_ADDRESSED


def test_assumption_finding_rejects_out_of_range_confidence() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AssumptionFinding(
            statement="x",
            source=AssumptionSource.EXPLICIT,
            importance=ImportanceLevel.LOW,
            confidence=1.5,  # out of the 0.0-1.0 range
            evidence_status=AssumptionEvidenceStatus.SUPPORTED,
            dependency="x",
            failure_consequence="x",
        )


def test_assumption_analysis_can_be_empty() -> None:
    analysis = AssumptionAnalysis()

    assert analysis.assumptions == []


def test_assumption_finding_can_be_both_explicit_and_critical() -> None:
    """`source` and `importance` (and `evidence_status`) are independent
    axes - an assumption is not forced into a single classification bucket."""
    finding = AssumptionFinding(
        statement="The lease will be signed within 30 days.",
        source=AssumptionSource.EXPLICIT,
        importance=ImportanceLevel.CRITICAL,
        confidence=0.9,
        evidence_status=AssumptionEvidenceStatus.SUPPORTED,
        dependency="Timeline",
        failure_consequence="The expansion timeline slips by a full quarter.",
    )

    assert finding.source is AssumptionSource.EXPLICIT
    assert finding.importance is ImportanceLevel.CRITICAL
    assert finding.evidence_status is AssumptionEvidenceStatus.SUPPORTED
