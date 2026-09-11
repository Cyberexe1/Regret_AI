"""Tests for `CrossDecisionLearningRepository` - user-scoped DynamoDB
persistence for Cross-Decision Patterns (REGRET ENGINE 2.0, Step 23).

MANDATORY per spec section 8/21: User A must never be able to retrieve
User B's patterns or occurrences through this repository - see
`test_user_a_cannot_list_user_b_patterns` and
`test_user_a_cannot_list_user_b_occurrences`.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.learning.repository import CrossDecisionLearningRepository
from app.learning.schemas import (
    CrossDecisionPattern,
    OccurrenceRelation,
    PatternConfidence,
    PatternOccurrence,
    PatternStatus,
    PatternType,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def repo(dynamodb_table: None) -> CrossDecisionLearningRepository:
    return CrossDecisionLearningRepository()


def _pattern(user_id: str, pattern_id: str | None = None, **overrides) -> CrossDecisionPattern:
    defaults = {
        "pattern_id": pattern_id or str(uuid4()),
        "user_id": user_id,
        "pattern_type": PatternType.RECURRING_FAILED_ASSUMPTION,
        "title": "Retention has repeatedly underperformed.",
        "statement": "In your past decisions, retention has repeatedly underperformed.",
        "normalized_key": "retention",
        "variable": "Customer retention",
        "occurrence_count": 2,
        "evidence_count": 2,
        "confidence": PatternConfidence.MEDIUM,
        "confidence_basis": "2 decisions support this pattern.",
        "first_seen_at": NOW,
        "last_seen_at": NOW,
        "status": PatternStatus.EMERGING,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    return CrossDecisionPattern(**defaults)


def _occurrence(
    user_id: str, pattern_id: str, decision_id: str | None = None, **overrides
) -> PatternOccurrence:
    defaults = {
        "occurrence_id": str(uuid4()),
        "pattern_id": pattern_id,
        "user_id": user_id,
        "decision_id": decision_id or str(uuid4()),
        "source_type": "memory_learning",
        "source_id": str(uuid4()),
        "observation": "Retention underperformed.",
        "observed_at": NOW,
        "relation": OccurrenceRelation.SUPPORTS,
        "confidence": 0.6,
    }
    defaults.update(overrides)
    return PatternOccurrence(**defaults)


# --- basic upsert / get ----------------------------------------------------------


def test_upsert_and_get_pattern_round_trips(repo: CrossDecisionLearningRepository) -> None:
    pattern = _pattern("user-a")

    repo.upsert_pattern(pattern)
    fetched = repo.get_pattern("user-a", pattern.pattern_id)

    assert fetched is not None
    assert fetched.pattern_id == pattern.pattern_id
    assert fetched.title == pattern.title


def test_get_pattern_for_nonexistent_id_returns_none(repo: CrossDecisionLearningRepository) -> None:
    assert repo.get_pattern("user-a", "does-not-exist") is None


def test_upsert_is_idempotent_and_never_duplicates(repo: CrossDecisionLearningRepository) -> None:
    pattern = _pattern("user-a", pattern_id="fixed-id")

    repo.upsert_pattern(pattern)
    repo.upsert_pattern(pattern.model_copy(update={"occurrence_count": 3}))

    patterns = repo.list_patterns_for_user("user-a")
    assert len(patterns) == 1
    assert patterns[0].occurrence_count == 3


# --- filters -----------------------------------------------------------------


def test_list_patterns_for_user_supports_filters(repo: CrossDecisionLearningRepository) -> None:
    repo.upsert_pattern(
        _pattern(
            "user-a",
            pattern_type=PatternType.RECURRING_FAILED_ASSUMPTION,
            status=PatternStatus.EMERGING,
        )
    )
    repo.upsert_pattern(
        _pattern(
            "user-a",
            pattern_type=PatternType.RECURRING_VALIDATED_ASSUMPTION,
            status=PatternStatus.ESTABLISHED,
            normalized_key="pricing",
            variable="Pricing tolerance",
        )
    )

    by_type = repo.list_patterns_for_user("user-a", pattern_type="recurring_validated_assumption")
    by_status = repo.list_patterns_for_user("user-a", status="established")
    by_variable = repo.list_patterns_for_user("user-a", variable="Pricing tolerance")

    assert len(by_type) == 1
    assert by_type[0].pattern_type == PatternType.RECURRING_VALIDATED_ASSUMPTION
    assert len(by_status) == 1
    assert len(by_variable) == 1


# --- occurrences ---------------------------------------------------------------


def test_list_pattern_occurrences_returns_only_that_patterns_rows(
    repo: CrossDecisionLearningRepository,
) -> None:
    pattern_a = _pattern("user-a", pattern_id="pattern-a")
    pattern_b = _pattern("user-a", pattern_id="pattern-b")
    repo.upsert_pattern(pattern_a)
    repo.upsert_pattern(pattern_b)
    repo.upsert_occurrence(_occurrence("user-a", "pattern-a"))
    repo.upsert_occurrence(_occurrence("user-a", "pattern-a"))
    repo.upsert_occurrence(_occurrence("user-a", "pattern-b"))

    occurrences_a = repo.list_pattern_occurrences("user-a", "pattern-a")
    occurrences_b = repo.list_pattern_occurrences("user-a", "pattern-b")

    assert len(occurrences_a) == 2
    assert len(occurrences_b) == 1
    assert all(o.pattern_id == "pattern-a" for o in occurrences_a)


def test_delete_occurrences_for_pattern_removes_only_that_patterns_rows(
    repo: CrossDecisionLearningRepository,
) -> None:
    repo.upsert_pattern(_pattern("user-a", pattern_id="pattern-a"))
    repo.upsert_pattern(_pattern("user-a", pattern_id="pattern-b"))
    repo.upsert_occurrence(_occurrence("user-a", "pattern-a"))
    repo.upsert_occurrence(_occurrence("user-a", "pattern-b"))

    repo.delete_occurrences_for_pattern("user-a", "pattern-a")

    assert repo.list_pattern_occurrences("user-a", "pattern-a") == []
    assert len(repo.list_pattern_occurrences("user-a", "pattern-b")) == 1
    # The pattern SUMMARY record itself must survive - only occurrences are removed.
    assert repo.get_pattern("user-a", "pattern-a") is not None


def test_occurrence_upsert_is_idempotent(repo: CrossDecisionLearningRepository) -> None:
    occurrence = _occurrence("user-a", "pattern-a", occurrence_id="fixed-occ")
    repo.upsert_pattern(_pattern("user-a", pattern_id="pattern-a"))

    repo.upsert_occurrence(occurrence)
    repo.upsert_occurrence(occurrence)

    assert len(repo.list_pattern_occurrences("user-a", "pattern-a")) == 1


# --- get_patterns_for_decision ---------------------------------------------------


def test_get_patterns_for_decision_matches_supporting_or_contradicting(
    repo: CrossDecisionLearningRepository,
) -> None:
    decision_id = str(uuid4())
    repo.upsert_pattern(
        _pattern("user-a", pattern_id="pattern-a", supporting_decision_ids=[decision_id])
    )
    repo.upsert_pattern(
        _pattern("user-a", pattern_id="pattern-b", contradicting_decision_ids=[decision_id])
    )
    repo.upsert_pattern(_pattern("user-a", pattern_id="pattern-c"))  # unrelated

    patterns = repo.get_patterns_for_decision("user-a", decision_id)

    assert {p.pattern_id for p in patterns} == {"pattern-a", "pattern-b"}


# --- MANDATORY: user isolation ---------------------------------------------------


def test_user_a_cannot_list_user_b_patterns(repo: CrossDecisionLearningRepository) -> None:
    repo.upsert_pattern(_pattern("user-a", pattern_id="a-pattern"))
    repo.upsert_pattern(_pattern("user-b", pattern_id="b-pattern"))

    a_patterns = repo.list_patterns_for_user("user-a")
    b_patterns = repo.list_patterns_for_user("user-b")

    assert [p.pattern_id for p in a_patterns] == ["a-pattern"]
    assert [p.pattern_id for p in b_patterns] == ["b-pattern"]


def test_user_a_cannot_get_user_b_pattern_by_id(repo: CrossDecisionLearningRepository) -> None:
    repo.upsert_pattern(_pattern("user-b", pattern_id="shared-id"))

    # Even knowing User B's exact pattern id, User A's own partition
    # never contains it - by construction (see repository module docstring).
    assert repo.get_pattern("user-a", "shared-id") is None
    assert repo.get_pattern("user-b", "shared-id") is not None


def test_user_a_cannot_list_user_b_occurrences(repo: CrossDecisionLearningRepository) -> None:
    repo.upsert_pattern(_pattern("user-a", pattern_id="pattern-a"))
    repo.upsert_pattern(
        _pattern("user-b", pattern_id="pattern-a")
    )  # same pattern_id, different user
    repo.upsert_occurrence(_occurrence("user-a", "pattern-a", decision_id="decision-a"))
    repo.upsert_occurrence(_occurrence("user-b", "pattern-a", decision_id="decision-b"))

    occurrences_a = repo.list_pattern_occurrences("user-a", "pattern-a")
    occurrences_b = repo.list_pattern_occurrences("user-b", "pattern-a")

    assert len(occurrences_a) == 1
    assert occurrences_a[0].decision_id == "decision-a"
    assert len(occurrences_b) == 1
    assert occurrences_b[0].decision_id == "decision-b"


def test_user_a_and_user_b_can_share_the_same_pattern_id_without_collision(
    repo: CrossDecisionLearningRepository,
) -> None:
    """Deterministic pattern ids are derived per-user (see
    `deterministic_pattern_id`), but even if two users' patterns
    happened to share an id, the DynamoDB partition key (`PK=USER#<id>`)
    keeps them fully isolated - this test proves that structurally."""
    repo.upsert_pattern(_pattern("user-a", pattern_id="same-id", title="User A's pattern"))
    repo.upsert_pattern(_pattern("user-b", pattern_id="same-id", title="User B's pattern"))

    pattern_a = repo.get_pattern("user-a", "same-id")
    pattern_b = repo.get_pattern("user-b", "same-id")

    assert pattern_a.title == "User A's pattern"
    assert pattern_b.title == "User B's pattern"
