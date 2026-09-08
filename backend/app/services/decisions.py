"""Business logic for decisions.

Route handlers stay thin and delegate here. No AI, no external calls yet -
this step only validates input, enforces ownership, and coordinates the
DynamoDB-backed repository.
"""

from uuid import UUID

from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.repositories.decision_repository import DecisionRepository
from app.schemas.decision import (
    DecisionCreate,
    DecisionListResponse,
    DecisionResponse,
    DecisionUpdate,
)

logger = get_logger(__name__)


class DecisionService:
    """Coordinates decision creation, retrieval, update, and deletion."""

    def __init__(self, repository: DecisionRepository) -> None:
        self._repository = repository

    def create_decision(self, user_id: str, payload: DecisionCreate) -> DecisionResponse:
        decision = self._repository.create(user_id, payload)
        logger.info("Decision created id=%s user_id=%s", decision.id, user_id)
        return decision

    def get_decision(self, user_id: str, decision_id: UUID) -> DecisionResponse:
        return self._get_owned(user_id, decision_id)

    def list_decisions(
        self, user_id: str, limit: int = 20, cursor: str | None = None
    ) -> DecisionListResponse:
        items, next_cursor = self._repository.list_for_user(user_id, limit=limit, cursor=cursor)
        return DecisionListResponse(items=items, next_cursor=next_cursor)

    def update_decision(
        self, user_id: str, decision_id: UUID, payload: DecisionUpdate
    ) -> DecisionResponse:
        # Ownership + existence check first, so a stranger's decision id
        # returns a plain 404 rather than leaking a conditional-write
        # conflict for a resource that was never theirs to begin with.
        self._get_owned(user_id, decision_id)
        updated = self._repository.update(decision_id, payload)
        logger.info("Decision updated id=%s user_id=%s", decision_id, user_id)
        return updated

    def delete_decision(self, user_id: str, decision_id: UUID) -> None:
        self._get_owned(user_id, decision_id)
        self._repository.delete(decision_id)
        logger.info("Decision deleted id=%s user_id=%s", decision_id, user_id)

    def _get_owned(self, user_id: str, decision_id: UUID) -> DecisionResponse:
        """Fetch a decision and verify it belongs to `user_id`.

        A missing decision and one owned by someone else both raise the
        same `NotFoundError` - existence of another user's decision is
        never revealed.
        """
        record = self._repository.get_raw(decision_id)
        if record is None or record.get("user_id") != user_id:
            raise NotFoundError(detail=f"Decision {decision_id} not found.")
        return DecisionRepository.to_response(record)
