"""Repository-level tests for `DecisionRepository`.

These exercise the DynamoDB access layer directly, without going through
the API, so pagination, conditional writes, and child-entity queries are
verified at the layer they're actually implemented in.
"""

from uuid import uuid4

import pytest

from app.core.errors import ConflictError
from app.repositories.decision_repository import DecisionRepository
from app.schemas.decision import DecisionCreate, DecisionUpdate

USER_ID = "test-user"


@pytest.fixture
def repository(dynamodb_table: None) -> DecisionRepository:
    return DecisionRepository()


def _payload(**overrides: object) -> DecisionCreate:
    base = {
        "title": "Relocate the warehouse",
        "description": "Considering a move to a larger facility.",
    }
    base.update(overrides)
    return DecisionCreate(**base)


def test_create_and_get(repository: DecisionRepository) -> None:
    created = repository.create(USER_ID, _payload())

    fetched = repository.get(created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.title == created.title


def test_get_missing_returns_none(repository: DecisionRepository) -> None:
    assert repository.get(uuid4()) is None


def test_list_for_user_only_returns_that_users_decisions(repository: DecisionRepository) -> None:
    mine = repository.create(USER_ID, _payload(title="Mine"))
    repository.create("someone-else", _payload(title="Not mine"))

    items, _ = repository.list_for_user(USER_ID)

    ids = [item.id for item in items]
    assert mine.id in ids
    assert len(items) == 1


def test_list_for_user_pagination_cursor_advances(repository: DecisionRepository) -> None:
    for i in range(3):
        repository.create(USER_ID, _payload(title=f"Decision {i}"))

    first_page, cursor = repository.list_for_user(USER_ID, limit=2)
    assert len(first_page) == 2
    assert cursor is not None

    second_page, next_cursor = repository.list_for_user(USER_ID, limit=2, cursor=cursor)
    assert len(second_page) == 1
    assert next_cursor is None


def test_update_changes_fields_and_updated_at(repository: DecisionRepository) -> None:
    created = repository.create(USER_ID, _payload())

    updated = repository.update(created.id, DecisionUpdate(title="New title"))

    assert updated.title == "New title"
    assert updated.updated_at > created.updated_at


def test_update_with_matching_expected_updated_at_succeeds(repository: DecisionRepository) -> None:
    created = repository.create(USER_ID, _payload())

    updated = repository.update(
        created.id, DecisionUpdate(title="Guarded update", expected_updated_at=created.updated_at)
    )

    assert updated.title == "Guarded update"


def test_update_with_stale_expected_updated_at_raises_conflict(
    repository: DecisionRepository,
) -> None:
    created = repository.create(USER_ID, _payload())
    repository.update(created.id, DecisionUpdate(title="First change"))

    with pytest.raises(ConflictError):
        repository.update(
            created.id,
            DecisionUpdate(title="Second change", expected_updated_at=created.updated_at),
        )


def test_delete_removes_decision(repository: DecisionRepository) -> None:
    created = repository.create(USER_ID, _payload())

    repository.delete(created.id)

    assert repository.get(created.id) is None


def test_list_child_entities_are_empty_for_new_decision(repository: DecisionRepository) -> None:
    created = repository.create(USER_ID, _payload())

    assert repository.list_assumptions(created.id) == []
    assert repository.list_blindspots(created.id) == []
    assert repository.list_scenarios(created.id) == []
    assert repository.list_thresholds(created.id) == []
    assert repository.list_experiments(created.id) == []
