"""DynamoDB-backed Decision Memory storage.

Uses the EXISTING single-table design (see `app.repositories.dynamodb` and
`app.repositories.decision_repository`'s module docstring) - no second
database, no new table. Key layout:

    DecisionMemory:  PK=DECISION#<decision_id>   SK=MEMORY#<memory_id>
    MemoryLearning:  PK=DECISION#<decision_id>   SK=LEARNING#<learning_id>

Both live in the same decision partition as every other entity
(assumptions, thresholds, experiments, re-evaluations, ...), so "get
everything about this decision" - including its memory - stays a single
`Query` on `PK`, never a scan. There is exactly one `DecisionMemory` per
decision (identified by a deterministic SK derived from the decision id
itself, not a fresh UUID - see `_memory_sk`), so `create_memory` is really
an upsert; `MemoryLearning` records are append-only history, one per
(experiment result, learning type) pair, keyed so a duplicate write is a
no-op rather than a duplicate record (see `create_learning`).

Follows the same constructor pattern as every other repository
(`gateway: DynamoDBGateway | None = None`, defaulting to a fresh
`DynamoDBGateway()`, which itself resolves the same cached, process-wide
table via `app.repositories.dynamodb.get_table()`).
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from boto3.dynamodb.conditions import Attr, Key

from app.core.errors import ConflictError
from app.core.logging import get_logger
from app.memory.memory_schemas import DecisionMemory, MemoryLearning
from app.repositories.dynamodb import DynamoDBGateway

logger = get_logger(__name__)


def _decision_pk(decision_id: UUID | str) -> str:
    return f"DECISION#{decision_id}"


def _memory_sk(memory_id: UUID | str) -> str:
    return f"MEMORY#{memory_id}"


def _learning_sk(learning_id: UUID | str) -> str:
    return f"LEARNING#{learning_id}"


class MemoryRepository:
    """Stores `DecisionMemory` and `MemoryLearning` records for decisions.

    Contains no business logic (no learning extraction, no threshold
    comparison, no decision about what counts as "validated") - that all
    lives in `MemoryService`. This class only knows how to read and write
    plain dicts/Pydantic models against the existing table.
    """

    def __init__(self, gateway: DynamoDBGateway | None = None) -> None:
        self._gateway = gateway if gateway is not None else DynamoDBGateway()

    # --- DecisionMemory --------------------------------------------------------

    def create_memory(self, memory: DecisionMemory) -> DecisionMemory:
        """Persist a new `DecisionMemory`.

        Guarded by `Attr("PK").not_exists() | Attr("SK").not_exists()`... in
        practice this is a fresh memory_id, so collision is not expected;
        the guard exists purely as the same defensive safety net every
        other `create()` in this codebase uses for a freshly generated id
        (see `DecisionRepository.create`).
        """
        item = _memory_to_item(memory)
        self._gateway.put_item(item, condition=Attr("PK").not_exists())
        return memory

    def get_memory(self, decision_id: UUID, memory_id: UUID) -> DecisionMemory | None:
        item = self._gateway.get_item(
            {"PK": _decision_pk(decision_id), "SK": _memory_sk(memory_id)}
        )
        return DecisionMemory.model_validate(_strip_keys(item)) if item is not None else None

    def get_memory_by_id(self, memory_id: UUID) -> DecisionMemory | None:
        """Look up a memory by its own id alone, without knowing its decision.

        Supports `GET /api/v1/memory/{memory_id}`, which only has the
        memory id. Mirrors `EvidenceRepository.get_by_id`/
        `DecisionRepository.get_experiment_by_id`: rather than a table
        scan or a new index, this queries the existing `GSI2` (shared with
        evidence/experiment lookups, distinguished by key prefix -
        `MEMORY#<id>` never collides with `EVIDENCE#<id>`/`EXPERIMENT#<id>`)
        with a single bounded `Query`.
        """
        items, _ = self._gateway.query(
            key_condition=Key("GSI2PK").eq(_memory_gsi2pk(memory_id)),
            index_name="GSI2",
            limit=1,
        )
        return DecisionMemory.model_validate(_strip_keys(items[0])) if items else None

    def update_memory(self, memory: DecisionMemory) -> DecisionMemory:
        """Overwrite the single `DecisionMemory` record for a decision.

        This is the one place Decision Memory departs from the
        "append-only, never overwrite" convention used for
        Assumption/Threshold/RegretScenario/ReEvaluation records - and
        deliberately so: `DecisionMemory` is a *current-state summary*,
        not a history record (the history lives in the immutable
        `MemoryLearning` records it references, which are never
        overwritten - see `create_learning`). Rewriting the summary in
        place as new evidence arrives is the whole point of "memory" as
        specified in Step 18; the underlying facts it summarizes remain
        fully auditable via the learnings themselves and via
        `list_reevaluations`/`list_experiment_results` on
        `DecisionRepository`, which this module never touches.
        """
        item = _memory_to_item(memory)
        self._gateway.put_item(item, condition=Attr("PK").exists())
        return memory

    def list_memory_for_decision(self, decision_id: UUID) -> list[DecisionMemory]:
        """List memory records for a decision.

        Returns at most one item today (one `DecisionMemory` per
        decision), as a list for API-shape consistency with every other
        `list_*` method in this codebase and to avoid a breaking schema
        change if a future step ever needs more than one.
        """
        items = self._query_children(decision_id, "MEMORY#")
        return [DecisionMemory.model_validate(_strip_keys(item)) for item in items]

    # --- MemoryLearning ----------------------------------------------------------

    def create_learning(self, learning: MemoryLearning) -> tuple[MemoryLearning, bool]:
        """Persist a new `MemoryLearning`, idempotently.

        `learning.learning_id` MUST be deterministically derived by the
        caller from `(experiment_result_id, learning_type)` (see
        `MemoryService._learning_id_for`) so that re-processing the same
        experiment result twice - the exact scenario Step 18 calls out -
        produces the same id and therefore the same DynamoDB key, rather
        than two rows. The write is conditioned on `Attr("PK").not_exists()`;
        if the record already exists, `DynamoDBGateway._run` raises
        `ConflictError`, which is caught here and turned into
        `(existing_learning, False)` - the second bool return value tells
        the caller whether a NEW learning was actually created, so
        `MemoryService` can log "duplicate prevented" rather than "learning
        created" without needing a separate existence check first.
        """
        item = _learning_to_item(learning)
        try:
            self._gateway.put_item(item, condition=Attr("PK").not_exists())
        except ConflictError:
            existing = self.get_learning(learning.decision_id, learning.learning_id)
            logger.info(
                "Duplicate learning write prevented decision_id=%s learning_id=%s "
                "learning_type=%s",
                learning.decision_id,
                learning.learning_id,
                learning.learning_type.value,
            )
            # `existing` should always be found (the ConflictError proves
            # the item exists) - fall back to the caller's own copy only
            # in the theoretically-impossible case of a concurrent delete.
            return existing or learning, False
        return learning, True

    def get_learning(self, decision_id: UUID, learning_id: UUID) -> MemoryLearning | None:
        item = self._gateway.get_item(
            {"PK": _decision_pk(decision_id), "SK": _learning_sk(learning_id)}
        )
        return MemoryLearning.model_validate(_strip_keys(item)) if item is not None else None

    def list_learnings_for_decision(self, decision_id: UUID) -> list[MemoryLearning]:
        """List every learning ever recorded for a decision, oldest first.

        Nothing here is ever deleted or overwritten - this is the
        decision's full, auditable learning history.
        """
        items = self._query_children(decision_id, "LEARNING#")
        return [MemoryLearning.model_validate(_strip_keys(item)) for item in items]

    # --- shared -------------------------------------------------------------

    def _query_children(self, decision_id: UUID, sk_prefix: str) -> list[dict[str, Any]]:
        items, _ = self._gateway.query(
            key_condition=Key("PK").eq(_decision_pk(decision_id)) & Key("SK").begins_with(sk_prefix)
        )
        return items


def _memory_gsi2pk(memory_id: UUID | str) -> str:
    return f"MEMORY#{memory_id}"


def _memory_to_item(memory: DecisionMemory) -> dict[str, Any]:
    dumped = memory.model_dump(mode="json")
    return {
        "PK": _decision_pk(memory.decision_id),
        "SK": _memory_sk(memory.memory_id),
        "entity_type": "MEMORY",
        "GSI2PK": _memory_gsi2pk(memory.memory_id),
        "GSI2SK": _memory_gsi2pk(memory.memory_id),
        **dumped,
    }


def _learning_to_item(learning: MemoryLearning) -> dict[str, Any]:
    dumped = learning.model_dump(mode="json")
    return {
        "PK": _decision_pk(learning.decision_id),
        "SK": _learning_sk(learning.learning_id),
        "entity_type": "LEARNING",
        **dumped,
    }


def _strip_keys(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in item.items()
        if key not in {"PK", "SK", "GSI1PK", "GSI1SK", "GSI2PK", "GSI2SK", "entity_type"}
    }


# Re-exported for callers that only need a timestamp helper matching the
# rest of the codebase's convention (`datetime.now(UTC).isoformat()`).
def now_iso() -> str:
    return datetime.now(UTC).isoformat()
