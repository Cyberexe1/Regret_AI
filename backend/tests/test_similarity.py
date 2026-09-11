"""Tests for `DecisionSimilarityService` - deterministic, explainable
similarity scoring across decisions.

No LLM/Strands invocation happens anywhere in this file - similarity
scoring is entirely deterministic Python. Tests seed decisions directly
through `DecisionRepository`, mirroring `test_memory_service.py`'s
pattern.
"""

from uuid import uuid4

from app.memory.similarity import DecisionSimilarityService
from app.repositories.decision_repository import DecisionRepository
from app.schemas.decision import DecisionCreate

USER_ID = "test-user"


def _make_decision(decision_repo: DecisionRepository, **overrides):
    payload = {
        "title": "Open a cloud kitchen",
        "description": "Considering a Rs 5 lakh investment in a cloud kitchen in Mumbai.",
    }
    payload.update(overrides)
    return decision_repo.create(USER_ID, DecisionCreate(**payload))


def test_identical_decisions_score_highly(dynamodb_table: None) -> None:
    decision_repo = DecisionRepository()
    service = DecisionSimilarityService()

    current = _make_decision(decision_repo)
    past = _make_decision(decision_repo)

    score = service.score(current, past, [], [])

    assert score.decision_id == past.id
    assert score.score >= 0.5
    assert "decision_text_similarity" in score.matched_features
    assert score.explanation
    assert 0.0 <= score.confidence <= 1.0


def test_completely_unrelated_decisions_score_low(dynamodb_table: None) -> None:
    decision_repo = DecisionRepository()
    service = DecisionSimilarityService()

    current = _make_decision(
        decision_repo,
        title="Open a cloud kitchen",
        description="Considering a Rs 5 lakh investment in a cloud kitchen in Mumbai.",
    )
    past = _make_decision(
        decision_repo,
        title="Switch to a remote job offer",
        description="Deciding whether to accept a fully remote software engineering role abroad.",
    )

    score = service.score(current, past, [], [])

    assert score.score < 0.3


def test_score_never_raises_for_thin_past_decision_data(dynamodb_table: None) -> None:
    """A past decision with no recorded assumptions/thresholds yet (e.g.
    never analyzed) must still score cleanly - missing data means "no
    signal" for that component, never a crash and never a fabricated 0."""
    decision_repo = DecisionRepository()
    service = DecisionSimilarityService()

    current = _make_decision(decision_repo)
    past = _make_decision(decision_repo, budget=None, risk_tolerance=None, location=None)

    score = service.score(current, past, [], [])

    assert 0.0 <= score.score <= 1.0
    assert 0.0 <= score.confidence <= 1.0


def test_budget_similarity_contributes_to_score(dynamodb_table: None) -> None:
    decision_repo = DecisionRepository()
    service = DecisionSimilarityService()

    current = _make_decision(decision_repo, budget=500000, description="Investment plan A.")
    similar_budget = _make_decision(
        decision_repo, budget=510000, description="Totally different wording here."
    )
    different_budget = _make_decision(
        decision_repo, budget=5000, description="Totally different wording here."
    )

    similar_score = service.score(current, similar_budget, [], [])
    different_score = service.score(current, different_budget, [], [])

    assert similar_score.score > different_score.score
    assert "budget_similarity" in similar_score.matched_features


def test_risk_tolerance_and_location_match_are_named_features(dynamodb_table: None) -> None:
    decision_repo = DecisionRepository()
    service = DecisionSimilarityService()

    current = _make_decision(
        decision_repo,
        description="Unrelated wording entirely, nothing textually overlapping here at all.",
        risk_tolerance="moderate",
        location="Mumbai",
    )
    past = _make_decision(
        decision_repo,
        description="A completely different sentence structure and topic altogether.",
        risk_tolerance="moderate",
        location="Mumbai",
    )

    score = service.score(current, past, [], [])

    assert "risk_tolerance_match" in score.matched_features
    assert "location_match" in score.matched_features


def test_rank_orders_by_score_descending_and_is_deterministic(dynamodb_table: None) -> None:
    decision_repo = DecisionRepository()
    service = DecisionSimilarityService()

    current = _make_decision(decision_repo)
    close = _make_decision(decision_repo)
    far = _make_decision(
        decision_repo,
        title="Switch jobs",
        description="Should I take a remote job offer in a different country entirely?",
    )

    ranked = service.rank(
        current,
        [(far, [], []), (close, [], [])],
    )

    assert ranked[0].decision_id == close.id
    assert ranked[0].score >= ranked[1].score

    # Deterministic: calling rank() again produces the exact same order.
    ranked_again = service.rank(current, [(far, [], []), (close, [], [])])
    assert [s.decision_id for s in ranked] == [s.decision_id for s in ranked_again]


def test_score_is_never_negative_or_above_one(dynamodb_table: None) -> None:
    decision_repo = DecisionRepository()
    service = DecisionSimilarityService()
    current = _make_decision(decision_repo)
    past = _make_decision(decision_repo)

    score = service.score(current, past, [], [])

    assert 0.0 <= score.score <= 1.0


def test_score_for_nonexistent_style_decision_ids_still_deterministic() -> None:
    """Scoring is a pure function of the objects passed in - it never
    touches a repository itself, so it works even for decisions that were
    never persisted (e.g. constructed purely for a unit test)."""
    from datetime import UTC, datetime

    from app.schemas.decision import DecisionResponse, DecisionStatus

    now = datetime.now(UTC)
    current = DecisionResponse(
        id=uuid4(),
        title="A",
        description="A generic decision about something.",
        status=DecisionStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    past = DecisionResponse(
        id=uuid4(),
        title="B",
        description="A generic decision about something else entirely.",
        status=DecisionStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )

    service = DecisionSimilarityService()
    first = service.score(current, past, [], [])
    second = service.score(current, past, [], [])

    assert first.score == second.score
    assert first.explanation == second.explanation
