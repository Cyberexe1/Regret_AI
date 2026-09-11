"""Tests for `ValueOfInformationRepository` - persistence and versioning
(REGRET ENGINE 2.0, Step 20). No LLM/Strands invocation happens anywhere
in this file.
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.agents.value_of_information_schemas import ValueOfInformationAnalysis
from app.repositories.value_of_information_repository import ValueOfInformationRepository


def _analysis(decision_id, **overrides) -> ValueOfInformationAnalysis:
    payload = {
        "analysis_id": uuid4(),
        "decision_id": decision_id,
        "ranked_uncertainties": [],
        "summary": "x",
        "created_at": datetime.now(UTC),
    }
    payload.update(overrides)
    return ValueOfInformationAnalysis(**payload)


def test_create_and_get(dynamodb_table: None) -> None:
    repo = ValueOfInformationRepository()
    decision_id = uuid4()
    analysis = _analysis(decision_id)

    repo.create(analysis)
    fetched = repo.get(decision_id, analysis.analysis_id)

    assert fetched is not None
    assert fetched.analysis_id == analysis.analysis_id
    assert fetched.decision_id == decision_id


def test_get_missing_returns_none(dynamodb_table: None) -> None:
    repo = ValueOfInformationRepository()
    assert repo.get(uuid4(), uuid4()) is None


def test_list_for_decision_never_returns_another_decisions_analysis(dynamodb_table: None) -> None:
    repo = ValueOfInformationRepository()
    decision_a = uuid4()
    decision_b = uuid4()

    repo.create(_analysis(decision_a))
    repo.create(_analysis(decision_b))

    results = repo.list_for_decision(decision_a)

    assert len(results) == 1
    assert results[0].decision_id == decision_a


def test_get_latest_before_any_analysis_returns_none(dynamodb_table: None) -> None:
    repo = ValueOfInformationRepository()
    assert repo.get_latest(uuid4()) is None


def test_get_latest_returns_the_most_recently_created(dynamodb_table: None) -> None:
    repo = ValueOfInformationRepository()
    decision_id = uuid4()

    older = _analysis(decision_id, created_at=datetime(2024, 1, 1, tzinfo=UTC))
    newer = _analysis(decision_id, created_at=datetime(2025, 1, 1, tzinfo=UTC))
    repo.create(older)
    repo.create(newer)

    latest = repo.get_latest(decision_id)

    assert latest is not None
    assert latest.analysis_id == newer.analysis_id


def test_mark_superseded_does_not_delete_the_original_record(dynamodb_table: None) -> None:
    repo = ValueOfInformationRepository()
    decision_id = uuid4()
    first = _analysis(decision_id)
    second = _analysis(decision_id)
    repo.create(first)
    repo.create(second)

    repo.mark_superseded(decision_id, first.analysis_id, second.analysis_id)

    still_there = repo.get(decision_id, first.analysis_id)
    assert still_there is not None
    assert still_there.superseded_by_analysis_id == second.analysis_id
    # The newer record is completely untouched.
    unaffected = repo.get(decision_id, second.analysis_id)
    assert unaffected is not None
    assert unaffected.superseded_by_analysis_id is None


def test_mark_superseded_on_nonexistent_record_is_a_safe_no_op(dynamodb_table: None) -> None:
    repo = ValueOfInformationRepository()
    # Should never raise, even though neither analysis id exists.
    repo.mark_superseded(uuid4(), uuid4(), uuid4())


def test_duplicate_analysis_ids_are_not_silently_overwritten(dynamodb_table: None) -> None:
    """Persisting two analyses that happen to share an analysis_id (should
    never occur in practice, since ids come from uuid4()) is guarded by
    the same fresh-id safety net every other create() in this codebase
    uses - this test just documents create() is not a blind upsert."""
    from app.core.errors import ConflictError

    repo = ValueOfInformationRepository()
    decision_id = uuid4()
    shared_id = uuid4()
    first = _analysis(decision_id, analysis_id=shared_id)
    duplicate = _analysis(decision_id, analysis_id=shared_id, summary="different summary")

    repo.create(first)
    try:
        repo.create(duplicate)
        raised = False
    except ConflictError:
        raised = True

    assert raised
