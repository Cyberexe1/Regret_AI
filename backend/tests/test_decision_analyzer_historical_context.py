"""Tests for how `app.agents.decision_analyzer.build_analysis_prompt` renders
Decision Similarity + Historical Insight context (REGRET ENGINE 2.0) into
the Decision Analyzer's prompt.

Pure prompt-construction tests - no Bedrock/Strands call happens anywhere
in this file. Confirms the evidence-hierarchy framing (never a fact about
the current decision) is present, and that an absent/empty historical
context renders as a clear "none available" line rather than silently
omitting the section.
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.agents.decision_analyzer import build_analysis_prompt
from app.memory.memory_schemas import LearningSourceType, LearningType
from app.memory.similarity_schemas import HistoricalContext, HistoricalInsight, SimilarityScore
from app.schemas.decision import DecisionResponse, DecisionStatus


def _sample_decision() -> DecisionResponse:
    now = datetime.now(UTC)
    return DecisionResponse(
        id=uuid4(),
        title="Open a cloud kitchen",
        description="Considering a Rs 5 lakh investment in a cloud kitchen.",
        status=DecisionStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )


def _sample_insight(
    learning_type: LearningType = LearningType.THRESHOLD_FAILED,
) -> HistoricalInsight:
    now = datetime.now(UTC)
    return HistoricalInsight(
        insight_id=uuid4(),
        source_decision_id=uuid4(),
        source_memory_id=uuid4(),
        learning_id=uuid4(),
        statement="Observed Repeat-order rate did not meet the recorded threshold (18 vs 24).",
        relevance_score=0.62,
        relevance_reason="Considered similar because of similar wording.",
        learning_type=learning_type,
        source_type=LearningSourceType.RE_EVALUATION,
        observed_value="18",
        expected_value="24",
        confidence=0.7,
        created_at=now,
    )


def test_prompt_with_no_historical_context_says_none_available() -> None:
    decision = _sample_decision()

    prompt = build_analysis_prompt(decision, [], historical_context=None)

    assert "Historical context: none available" in prompt
    assert "Do not reference any past decision" in prompt


def test_prompt_with_found_false_historical_context_says_none_available() -> None:
    decision = _sample_decision()
    context = HistoricalContext(found=False, warnings=["No past decisions were available."])

    prompt = build_analysis_prompt(decision, [], historical_context=context)

    assert "Historical context: none available" in prompt


def test_prompt_with_insights_uses_previous_decision_observed_framing() -> None:
    decision = _sample_decision()
    insight = _sample_insight()
    score = SimilarityScore(
        decision_id=insight.source_decision_id,
        score=0.62,
        matched_features=["decision_text_similarity"],
        explanation="Considered similar because of similar wording.",
        confidence=0.7,
    )
    context = HistoricalContext(
        found=True,
        relevant_decisions=[score],
        relevant_decisions_count=1,
        relevant_learnings=[insight],
    )

    prompt = build_analysis_prompt(decision, [], historical_context=context)

    assert "Historical context (background only" in prompt
    assert "A previous decision observed:" in prompt
    assert insight.statement in prompt
    assert "historical relevance score" in prompt
    # Never phrased as a fact about the current decision.
    assert "is true here" not in prompt
    # Never claims statistical calibration.
    assert "not a probability" in prompt


def test_prompt_never_claims_validated_when_learning_is_still_provisional() -> None:
    decision = _sample_decision()
    insight = _sample_insight(learning_type=LearningType.THRESHOLD_INCONCLUSIVE)
    score = SimilarityScore(
        decision_id=insight.source_decision_id,
        score=0.5,
        matched_features=["decision_text_similarity"],
        explanation="x",
        confidence=0.5,
    )
    context = HistoricalContext(
        found=True,
        relevant_decisions=[score],
        relevant_decisions_count=1,
        relevant_learnings=[insight],
    )

    prompt = build_analysis_prompt(decision, [], historical_context=context)

    assert "still provisional/unresolved" in prompt


def test_prompt_with_found_true_but_no_learnings_yet() -> None:
    decision = _sample_decision()
    score = SimilarityScore(
        decision_id=uuid4(), score=0.5, matched_features=["decision_text_similarity"],
        explanation="x", confidence=0.5,
    )
    context = HistoricalContext(
        found=True, relevant_decisions=[score], relevant_decisions_count=1, relevant_learnings=[]
    )

    prompt = build_analysis_prompt(decision, [], historical_context=context)

    assert "none have recorded learnings yet" in prompt
