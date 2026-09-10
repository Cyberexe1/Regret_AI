"""Tests for the Devil's Advocate agent module itself.

Focused on the parts that don't require invoking a real model: prompt
construction and the structured schemas. No Bedrock call happens anywhere
in this file.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.agents.devils_advocate import build_devils_advocate_prompt
from app.agents.schemas import Challenge, DecisionAnalysis, DevilAdvocateAnalysis, SeverityLevel
from app.schemas.decision_resources import Assumption as StoredAssumption
from app.schemas.decision_resources import AssumptionSource as StoredAssumptionSource
from app.schemas.decision_resources import Blindspot as StoredBlindspot
from app.schemas.decision_resources import BlindspotEvidenceStatus, EvidenceStatus
from app.schemas.decision_resources import EvidenceFinding as StoredEvidenceFinding


def _sample_decision_analysis() -> DecisionAnalysis:
    return DecisionAnalysis(
        decision_summary="Whether to open a second bakery location downtown.",
        decision_type="market expansion",
        goal="Increase revenue by expanding to a second physical location.",
        constraints=["Limited capital"],
        success_criteria=["Second location breaks even within 12 months"],
        key_variables=["Foot traffic downtown"],
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
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _sample_stored_blindspot() -> StoredBlindspot:
    return StoredBlindspot(
        id=uuid4(),
        decision_id=uuid4(),
        question="What happens to unit economics if repeat orders fall below 20%?",
        category="untested_assumption",
        importance="critical",
        confidence=0.7,
        evidence_status=BlindspotEvidenceStatus.NOT_ADDRESSED,
        related_assumption_ids=[],
        why_it_matters="Repeat order rate drives whether the location breaks even.",
        created_at=datetime.now(UTC),
    )


def _sample_stored_evidence_finding() -> StoredEvidenceFinding:
    return StoredEvidenceFinding(
        id=uuid4(),
        decision_id=uuid4(),
        evidence_id=uuid4(),
        claim="Downtown foot traffic supports a second location.",
        support_level="supports",
        credibility="medium",
        related_assumption_ids=[],
        related_blindspot_ids=[],
        explanation="Foot traffic rose year over year per the submitted report.",
        excerpt="Downtown foot traffic rose 12% year over year.",
        created_at=datetime.now(UTC),
    )


# --- 1, 2, 3, 4: consumes Decision Analyzer / Assumption Hunter / Blindspot
# Hunter / Evidence Agent output --------------------------------------------


def test_prompt_is_built_from_all_upstream_structured_output() -> None:
    """The prompt must be built from the structured DecisionAnalysis plus
    the already-persisted assumptions/blindspots/evidence findings, never
    from raw decision text or raw evidence documents."""
    analysis = _sample_decision_analysis()
    assumption = _sample_stored_assumption()
    blindspot = _sample_stored_blindspot()
    finding = _sample_stored_evidence_finding()

    prompt = build_devils_advocate_prompt(analysis, [assumption], [blindspot], [finding])

    assert analysis.decision_summary in prompt
    assert analysis.goal in prompt
    assert assumption.statement in prompt
    assert str(assumption.id) in prompt
    assert blindspot.question in prompt
    assert str(blindspot.id) in prompt
    assert finding.claim in prompt
    assert str(finding.id) in prompt

    import inspect

    from app.agents.devils_advocate import build_devils_advocate_prompt as fn

    signature = inspect.signature(fn)
    assert list(signature.parameters) == [
        "decision_analysis",
        "assumptions",
        "blindspots",
        "evidence_findings",
    ]


def test_prompt_signature_never_accepts_raw_decision_or_raw_evidence() -> None:
    import inspect

    from app.agents.devils_advocate import build_devils_advocate_prompt as fn

    signature = inspect.signature(fn)
    assert "decision" not in signature.parameters
    assert "evidence" not in signature.parameters  # only evidence_findings, never raw Evidence


def test_prompt_states_absence_of_each_upstream_input() -> None:
    analysis = _sample_decision_analysis()

    prompt = build_devils_advocate_prompt(analysis, [], [], [])

    assert "No assumptions have been recorded" in prompt
    assert "No blindspots have been recorded" in prompt
    assert "No evidence findings have been recorded" in prompt


# --- 5: produces valid DevilAdvocateAnalysis -------------------------------


def test_challenge_schema_accepts_valid_data() -> None:
    challenge = Challenge(
        claim="Repeat customers will be high enough to sustain the business.",
        attack=(
            "The decision depends on reaching 25% repeat orders, but the supplied evidence "
            "only establishes initial demand."
        ),
        severity=SeverityLevel.CRITICAL,
        confidence=0.7,
        related_assumption_ids=["abc-123"],
        related_blindspot_ids=[],
        related_evidence_finding_ids=[],
        failure_mechanism="If repeat ordering stays low, unit economics no longer hold.",
        evidence_basis="No submitted evidence addresses repeat-purchase behavior.",
    )

    analysis = DevilAdvocateAnalysis(overall_challenge="x", challenges=[challenge])

    assert len(analysis.challenges) == 1
    assert analysis.challenges[0].severity is SeverityLevel.CRITICAL


def test_devil_advocate_analysis_can_have_empty_challenges() -> None:
    analysis = DevilAdvocateAnalysis(overall_challenge="No material challenges found.")

    assert analysis.challenges == []


def test_challenge_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValidationError):
        Challenge(
            claim="x",
            attack="x",
            severity=SeverityLevel.LOW,
            confidence=1.5,  # out of the 0.0-1.0 range
            related_assumption_ids=[],
            related_blindspot_ids=[],
            related_evidence_finding_ids=[],
            failure_mechanism="x",
            evidence_basis="x",
        )


# --- 6: identifies a concrete failure mechanism -----------------------------


def test_challenge_carries_a_concrete_failure_mechanism_field() -> None:
    challenge = Challenge(
        claim="Repeat customers will be high enough to sustain the business.",
        attack="Concrete attack text.",
        severity=SeverityLevel.HIGH,
        confidence=0.6,
        related_assumption_ids=[],
        related_blindspot_ids=[],
        related_evidence_finding_ids=[],
        failure_mechanism=(
            "If repeat ordering stays below the assumed level, the projected unit economics "
            "no longer hold and the business cannot cover fixed costs."
        ),
        evidence_basis="x",
    )

    assert "unit economics" in challenge.failure_mechanism


# --- 7: connects challenges to existing assumptions -------------------------


def test_challenge_can_reference_real_assumption_id() -> None:
    assumption = _sample_stored_assumption()
    challenge = Challenge(
        claim=assumption.statement,
        attack="x",
        severity=SeverityLevel.HIGH,
        confidence=0.6,
        related_assumption_ids=[str(assumption.id)],
        related_blindspot_ids=[],
        related_evidence_finding_ids=[],
        failure_mechanism="x",
        evidence_basis="x",
    )

    assert str(assumption.id) in challenge.related_assumption_ids


# --- 8, 9: does not fabricate evidence / does not invent statistics --------


def test_system_prompt_forbids_fabricating_evidence_and_statistics() -> None:
    from app.agents.devils_advocate import SYSTEM_PROMPT

    lowered = SYSTEM_PROMPT.lower()
    assert "never invent facts, statistics, sources, studies" in lowered
    assert "never fabricate a citation" in lowered or "fabricate" in lowered
    assert "base-rate" in lowered  # only raise base-rate claims the evidence actually supports


def test_system_prompt_forbids_generic_criticism() -> None:
    from app.agents.devils_advocate import SYSTEM_PROMPT

    assert "generic criticism" in SYSTEM_PROMPT.lower()
    assert "competition could be a problem" in SYSTEM_PROMPT.lower()


# --- 10: handles empty evidence ----------------------------------------------


def test_prompt_handles_empty_evidence_findings_without_error() -> None:
    analysis = _sample_decision_analysis()
    assumption = _sample_stored_assumption()

    prompt = build_devils_advocate_prompt(analysis, [assumption], [], [])

    assert "No evidence findings have been recorded" in prompt
    assert "do not fabricate" in prompt.lower()
    assert assumption.statement in prompt
