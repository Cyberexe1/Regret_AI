"""Tests for the Blindspot Hunter agent module itself.

Focused on the parts that don't require invoking a real model: prompt
construction and the structured schemas. No Bedrock call happens anywhere
in this file.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.agents.blindspot_hunter import build_blindspot_prompt
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
    ConfidenceLevel,
    DecisionAnalysis,
    ImportanceLevel,
    InformationClassification,
)
from app.schemas.decision_resources import Assumption as StoredAssumption
from app.schemas.decision_resources import AssumptionSource as StoredAssumptionSource
from app.schemas.decision_resources import Evidence, EvidenceStatus, SourceType


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


def _sample_stored_assumption() -> StoredAssumption:
    return StoredAssumption(
        id=uuid4(),
        decision_id=uuid4(),
        statement="Customers will order at least twice per month.",
        source=StoredAssumptionSource.IMPLICIT,
        importance="critical",
        confidence=0.45,
        evidence_status=EvidenceStatus.NOT_ADDRESSED,
        dependency="Business profitability",
        failure_consequence="Revenue may remain below the required operating margin.",
        reason=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
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


# --- 1 & 2: receives Decision Analyzer + Assumption Hunter output --------------


def test_prompt_is_built_from_decision_analysis_and_persisted_assumptions() -> None:
    """The prompt must be built from the structured DecisionAnalysis and
    the already-persisted assumptions, never from raw decision text."""
    analysis = _sample_decision_analysis()
    assumption = _sample_stored_assumption()

    prompt = build_blindspot_prompt(analysis, [assumption], evidence=[])

    assert analysis.decision_summary in prompt
    assert analysis.goal in prompt
    assert "Limited capital" in prompt
    assert assumption.statement in prompt
    assert str(assumption.id) in prompt  # real id exposed for related_assumption_ids

    import inspect

    from app.agents.blindspot_hunter import build_blindspot_prompt as fn

    signature = inspect.signature(fn)
    assert list(signature.parameters) == ["decision_analysis", "assumptions", "evidence"]


def test_prompt_includes_evidence_when_present() -> None:
    analysis = _sample_decision_analysis()
    evidence = _sample_evidence()

    prompt = build_blindspot_prompt(analysis, [], evidence=[evidence])

    assert "Foot traffic report" in prompt
    assert "Downtown foot traffic rose 12%" in prompt


def test_prompt_states_no_evidence_when_none_submitted() -> None:
    analysis = _sample_decision_analysis()

    prompt = build_blindspot_prompt(analysis, [], evidence=[])

    assert "No evidence has been submitted" in prompt


def test_prompt_states_no_assumptions_when_none_recorded() -> None:
    analysis = _sample_decision_analysis()

    prompt = build_blindspot_prompt(analysis, [], evidence=[])

    assert "No assumptions have been recorded" in prompt


# --- 3: produces valid BlindspotAnalysis ---------------------------------------


def test_blindspot_finding_schema_accepts_valid_data() -> None:
    finding = BlindspotFinding(
        question="What happens to unit economics if repeat orders fall below 20%?",
        category=BlindspotCategory.UNTESTED_ASSUMPTION,
        importance=ImportanceLevel.CRITICAL,
        confidence=0.7,
        evidence_status=BlindspotEvidenceStatus.NOT_ADDRESSED,
        related_assumption_ids=["abc-123"],
        why_it_matters="Repeat order rate drives whether the location breaks even.",
        evidence_gap="No repeat-purchase data has been submitted.",
    )

    analysis = BlindspotAnalysis(blindspots=[finding])

    assert len(analysis.blindspots) == 1
    assert analysis.blindspots[0].category is BlindspotCategory.UNTESTED_ASSUMPTION


def test_blindspot_analysis_can_be_empty() -> None:
    analysis = BlindspotAnalysis()

    assert analysis.blindspots == []


def test_blindspot_finding_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValidationError):
        BlindspotFinding(
            question="x",
            category=BlindspotCategory.OTHER,
            importance=ImportanceLevel.LOW,
            confidence=1.5,  # out of the 0.0-1.0 range
            evidence_status=BlindspotEvidenceStatus.NOT_ADDRESSED,
            related_assumption_ids=[],
            why_it_matters="x",
        )


def test_blindspot_finding_rejects_invalid_category() -> None:
    with pytest.raises(ValidationError):
        BlindspotFinding.model_validate(
            {
                "question": "x",
                "category": "not_a_real_category",
                "importance": "low",
                "confidence": 0.5,
                "evidence_status": "not_addressed",
                "related_assumption_ids": [],
                "why_it_matters": "x",
            }
        )


# --- 4: identifies missing evidence --------------------------------------------


def test_blindspot_can_represent_missing_evidence() -> None:
    finding = BlindspotFinding(
        question="What is the actual downtown lease rate?",
        category=BlindspotCategory.MISSING_EVIDENCE,
        importance=ImportanceLevel.HIGH,
        confidence=0.8,
        evidence_status=BlindspotEvidenceStatus.NOT_ADDRESSED,
        related_assumption_ids=[],
        why_it_matters="Lease cost materially affects break-even timing.",
        evidence_gap="No lease rate data has been submitted for this decision.",
    )

    assert finding.category is BlindspotCategory.MISSING_EVIDENCE
    assert finding.evidence_status is BlindspotEvidenceStatus.NOT_ADDRESSED
    assert finding.evidence_gap is not None


# --- 5: identifies an untested assumption --------------------------------------


def test_blindspot_can_represent_untested_assumption_and_reference_it() -> None:
    assumption = _sample_stored_assumption()
    finding = BlindspotFinding(
        question="Has the 'twice per month' ordering assumption actually been tested?",
        category=BlindspotCategory.UNTESTED_ASSUMPTION,
        importance=ImportanceLevel.CRITICAL,
        confidence=0.65,
        evidence_status=BlindspotEvidenceStatus.NOT_ADDRESSED,
        related_assumption_ids=[str(assumption.id)],
        why_it_matters="If false, profitability projections would be overstated.",
    )

    assert finding.category is BlindspotCategory.UNTESTED_ASSUMPTION
    assert str(assumption.id) in finding.related_assumption_ids


# --- 6: does not independently replace the Decision Analyzer -------------------


def test_prompt_signature_never_accepts_raw_decision() -> None:
    """`build_blindspot_prompt` only accepts a DecisionAnalysis + persisted
    assumptions + evidence - there is no code path here that could reach
    back into raw decision fields like title/description/budget."""
    import inspect

    from app.agents.blindspot_hunter import build_blindspot_prompt as fn

    signature = inspect.signature(fn)
    assert "decision" not in signature.parameters  # only decision_analysis, never raw decision


def test_prompt_never_asks_model_to_reanalyze_decision() -> None:
    """The system prompt must instruct the model to build on upstream
    output, not redo the Decision Analyzer's or Assumption Hunter's job."""
    from app.agents.blindspot_hunter import SYSTEM_PROMPT

    assert "Do NOT redo the Decision Analyzer's work" in SYSTEM_PROMPT
    assert "Do NOT redo" in SYSTEM_PROMPT or "do not redo" in SYSTEM_PROMPT.lower()


# --- 7: does not fabricate evidence ---------------------------------------------


def test_system_prompt_forbids_fabricating_evidence_or_citations() -> None:
    from app.agents.blindspot_hunter import SYSTEM_PROMPT

    lowered = SYSTEM_PROMPT.lower()
    assert "never invent facts" in lowered or "never fabricate" in lowered
    assert "outside research" in lowered


# --- 8: handles empty evidence ---------------------------------------------------


def test_prompt_handles_empty_evidence_list_without_error() -> None:
    analysis = _sample_decision_analysis()
    assumption = _sample_stored_assumption()

    prompt = build_blindspot_prompt(analysis, [assumption], evidence=[])

    assert "No evidence has been submitted" in prompt
    assert assumption.statement in prompt


def test_assumption_hunter_upstream_schema_still_importable() -> None:
    """Sanity check that BlindspotHunter's imports of upstream schemas
    haven't drifted - AssumptionAnalysis/AssumptionFinding/AssumptionSource/
    AssumptionEvidenceStatus must remain valid imports from app.agents.schemas."""
    analysis = AssumptionAnalysis(
        assumptions=[
            AssumptionFinding(
                statement="x",
                source=AssumptionSource.EXPLICIT,
                importance=ImportanceLevel.LOW,
                confidence=0.5,
                evidence_status=AssumptionEvidenceStatus.SUPPORTED,
                dependency="x",
                failure_consequence="x",
            )
        ]
    )
    assert len(analysis.assumptions) == 1
