"""Tests for the Evidence Agent module itself.

Focused on the parts that don't require invoking a real model: prompt
construction and the structured schemas. No Bedrock call happens anywhere
in this file.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.agents.evidence_agent import build_evidence_prompt
from app.agents.schemas import (
    DecisionAnalysis,
    EvidenceAnalysis,
    EvidenceCredibility,
    EvidenceFinding,
    EvidenceSupportLevel,
)
from app.schemas.decision_resources import Assumption as StoredAssumption
from app.schemas.decision_resources import AssumptionSource as StoredAssumptionSource
from app.schemas.decision_resources import Blindspot as StoredBlindspot
from app.schemas.decision_resources import (
    BlindspotEvidenceStatus,
    Evidence,
    EvidenceStatus,
    SourceType,
)


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


def _sample_evidence() -> Evidence:
    return Evidence(
        id=uuid4(),
        decision_id=uuid4(),
        title="Foot traffic report",
        source_type=SourceType.DOCUMENT,
        content_reference="Downtown foot traffic rose 12% year over year.",
        created_at=datetime.now(UTC),
    )


# --- 1: receives existing evidence ----------------------------------------------


def test_prompt_includes_real_evidence_id() -> None:
    analysis = _sample_decision_analysis()
    evidence = _sample_evidence()

    prompt = build_evidence_prompt(analysis, [], [], [evidence])

    assert str(evidence.id) in prompt
    assert "Foot traffic report" in prompt
    assert "Downtown foot traffic rose 12%" in prompt


def test_prompt_states_no_evidence_when_none_submitted() -> None:
    analysis = _sample_decision_analysis()

    prompt = build_evidence_prompt(analysis, [], [], [])

    assert "do not fabricate any findings" in prompt.lower()


def test_prompt_signature_never_accepts_raw_decision() -> None:
    """`build_evidence_prompt` only accepts structured upstream output plus
    evidence - never the raw decision."""
    import inspect

    from app.agents.evidence_agent import build_evidence_prompt as fn

    signature = inspect.signature(fn)
    assert list(signature.parameters) == [
        "decision_analysis",
        "assumptions",
        "blindspots",
        "evidence",
    ]


# --- 2: maps evidence to assumptions --------------------------------------------


def test_prompt_exposes_assumption_ids_for_referencing() -> None:
    analysis = _sample_decision_analysis()
    assumption = _sample_stored_assumption()

    prompt = build_evidence_prompt(analysis, [assumption], [], [])

    assert str(assumption.id) in prompt
    assert assumption.statement in prompt


def test_prompt_states_no_assumptions_when_none_recorded() -> None:
    analysis = _sample_decision_analysis()

    prompt = build_evidence_prompt(analysis, [], [], [])

    assert "No assumptions have been recorded" in prompt


# --- 3: maps evidence to blindspots ----------------------------------------------


def test_prompt_exposes_blindspot_ids_for_referencing() -> None:
    analysis = _sample_decision_analysis()
    blindspot = _sample_stored_blindspot()

    prompt = build_evidence_prompt(analysis, [], [blindspot], [])

    assert str(blindspot.id) in prompt
    assert blindspot.question in prompt


def test_prompt_states_no_blindspots_when_none_recorded() -> None:
    analysis = _sample_decision_analysis()

    prompt = build_evidence_prompt(analysis, [], [], [])

    assert "No blindspots have been recorded" in prompt


# --- 4: correctly represents supporting evidence --------------------------------


def test_evidence_finding_can_represent_supporting_evidence() -> None:
    evidence = _sample_evidence()
    finding = EvidenceFinding(
        evidence_id=str(evidence.id),
        claim="Downtown foot traffic is high enough to sustain a second store.",
        support_level=EvidenceSupportLevel.SUPPORTS,
        credibility=EvidenceCredibility.MEDIUM,
        related_assumption_ids=[],
        related_blindspot_ids=[],
        explanation="The report shows a 12% year-over-year increase in downtown foot traffic.",
        excerpt="Downtown foot traffic rose 12% year over year.",
    )

    assert finding.support_level is EvidenceSupportLevel.SUPPORTS
    assert finding.evidence_id == str(evidence.id)
    assert finding.excerpt is not None and finding.explanation is not None
    assert finding.excerpt != finding.explanation  # kept as separate fields


# --- 5: correctly represents contradictory evidence ------------------------------


def test_evidence_finding_can_represent_contradicting_evidence() -> None:
    evidence = _sample_evidence()
    finding = EvidenceFinding(
        evidence_id=str(evidence.id),
        claim="Customers will order at least twice per month.",
        support_level=EvidenceSupportLevel.CONTRADICTS,
        credibility=EvidenceCredibility.HIGH,
        related_assumption_ids=[],
        related_blindspot_ids=[],
        explanation="The submitted survey data shows average order frequency below once per month.",
        excerpt="Average customer order frequency was 0.8 times per month.",
    )

    assert finding.support_level is EvidenceSupportLevel.CONTRADICTS


# --- 6: correctly represents insufficient evidence -------------------------------


def test_evidence_finding_can_represent_insufficient_evidence() -> None:
    evidence = _sample_evidence()
    finding = EvidenceFinding(
        evidence_id=str(evidence.id),
        claim="Customers will order at least twice per month.",
        support_level=EvidenceSupportLevel.INSUFFICIENT,
        credibility=EvidenceCredibility.UNKNOWN,
        related_assumption_ids=[],
        related_blindspot_ids=[],
        explanation="Foot traffic data says nothing about order frequency per customer.",
        excerpt=None,
    )

    assert finding.support_level is EvidenceSupportLevel.INSUFFICIENT
    assert finding.excerpt is None  # no excerpt to quote - nothing relevant was found


def test_evidence_finding_can_represent_irrelevant_evidence() -> None:
    evidence = _sample_evidence()
    finding = EvidenceFinding(
        evidence_id=str(evidence.id),
        claim="The lease will be signed within 30 days.",
        support_level=EvidenceSupportLevel.IRRELEVANT,
        credibility=EvidenceCredibility.UNKNOWN,
        related_assumption_ids=[],
        related_blindspot_ids=[],
        explanation="This evidence is about foot traffic, not lease timing.",
    )

    assert finding.support_level is EvidenceSupportLevel.IRRELEVANT


# --- 7: never creates a fake evidence_id -----------------------------------------


def test_system_prompt_forbids_fabricating_evidence_ids() -> None:
    from app.agents.evidence_agent import SYSTEM_PROMPT

    lowered = SYSTEM_PROMPT.lower()
    assert "never invent an evidence_id" in lowered
    assert "never fabricate evidence" in lowered


def test_evidence_agent_module_declares_structured_output_prompt() -> None:
    """The structured-output instruction the agent is built with (not just
    the system prompt) must reiterate that evidence_id has to be copied
    exactly - belt-and-suspenders against the model inventing one. Checked
    at the module level, before constructing an `Agent`/`BedrockModel`, so
    this test never depends on any AWS credential or network resolution."""
    import inspect

    from app.agents import evidence_agent as module

    source = inspect.getsource(module.build_evidence_agent)
    assert "copied exactly" in source.lower()


# --- 8: produces valid EvidenceAnalysis ------------------------------------------


def test_evidence_analysis_can_be_empty() -> None:
    analysis = EvidenceAnalysis()

    assert analysis.findings == []


def test_evidence_analysis_accepts_valid_findings() -> None:
    evidence = _sample_evidence()
    analysis = EvidenceAnalysis(
        findings=[
            EvidenceFinding(
                evidence_id=str(evidence.id),
                claim="Downtown foot traffic supports a second location.",
                support_level=EvidenceSupportLevel.SUPPORTS,
                credibility=EvidenceCredibility.MEDIUM,
                related_assumption_ids=[],
                related_blindspot_ids=[],
                explanation="Foot traffic rose year over year per the submitted report.",
                excerpt="Downtown foot traffic rose 12% year over year.",
            )
        ]
    )

    assert len(analysis.findings) == 1


def test_evidence_finding_rejects_invalid_support_level() -> None:
    with pytest.raises(ValidationError):
        EvidenceFinding.model_validate(
            {
                "evidence_id": "x",
                "claim": "x",
                "support_level": "not_a_real_level",
                "credibility": "medium",
                "related_assumption_ids": [],
                "related_blindspot_ids": [],
                "explanation": "x",
            }
        )
