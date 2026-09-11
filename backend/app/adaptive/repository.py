"""DynamoDB-backed Adaptive Experiment State storage (REGRET ENGINE 2.0,
Step 21).

Uses the EXISTING single-table design (see `app.repositories.dynamodb`)
- no second database, no new table. Key layout:

    AdaptiveExperimentState:  PK=DECISION#<decision_id>   SK=ADAPTIVE_STATE#<state_id>

Lives in the same decision partition as every other entity, so "get
everything about this decision" stays a single `Query` on `PK`.
Append-only, exactly like `ReEvaluation`/`ValueOfInformationAnalysis`: a
new cycle transition always creates a NEW record; nothing is ever
deleted, and the core snapshot fields of an existing record are never
rewritten - `update_adaptive_state` only ever touches a narrow allow-list
of bookkeeping fields (currently: `current_status` transitioning to
`user_stopped`, plus `stopping_reason`/`updated_at`), mirroring
`ValueOfInformationRepository.mark_superseded`'s own "small, targeted
update, never a full overwrite" convention.

CONCURRENCY: `create_adaptive_state`'s caller
(`app.adaptive.service.AdaptiveExperimentService`) always derives
`state_id` deterministically from `(decision_id, cycle_number,
current_status, current_experiment_id)` - never a fresh `uuid4()` - so
two concurrent `advance_cycle` calls that would otherwise both try to
create "the same next state" collide on the exact same DynamoDB item key.
The conditional write (`Attr("PK").not_exists()`) means only one of them
actually creates the record; the loser gets `ConflictError`, which this
repository catches and turns into "return the record that already won"
- exactly like `app.memory.memory_repository.MemoryRepository
.create_learning`'s own idempotent-duplicate-write handling. No
experiment (or adaptive state) can ever be duplicated by a race.
"""

from contextlib import suppress
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from boto3.dynamodb.conditions import Attr, Key

from app.adaptive.schemas import AdaptiveExperimentState
from app.core.errors import ConflictError
from app.core.logging import get_logger
from app.repositories.dynamodb import DynamoDBGateway

logger = get_logger(__name__)


def _decision_pk(decision_id: UUID | str) -> str:
    return f"DECISION#{decision_id}"


def _adaptive_sk(state_id: UUID | str) -> str:
    return f"ADAPTIVE_STATE#{state_id}"


class AdaptiveStateRepository:
    """Stores `AdaptiveExperimentState` records for decisions.

    Contains no cycle-selection logic - that lives entirely in
    `app.adaptive.service.AdaptiveExperimentService`. This class only
    knows how to read and write the already-computed state against the
    existing table.
    """

    def __init__(self, gateway: DynamoDBGateway | None = None) -> None:
        self._gateway = gateway if gateway is not None else DynamoDBGateway()

    def create_adaptive_state(
        self, state: AdaptiveExperimentState
    ) -> tuple[AdaptiveExperimentState, bool]:
        """Persist a new state, idempotently.

        `state.state_id` MUST be deterministically derived by the caller
        (see module docstring) so that two concurrent callers computing
        "the same next transition" collide on the same key rather than
        creating two records. Returns `(state, True)` if this call
        actually created the record, or `(existing, False)` if another
        request already had - the second element lets the caller log
        "duplicate advance prevented" without a separate existence check.
        """
        item = _state_to_item(state)
        try:
            self._gateway.put_item(item, condition=Attr("PK").not_exists())
        except ConflictError:
            existing = self.get_adaptive_state(state.decision_id, state.state_id)
            logger.info(
                "Duplicate adaptive-state write prevented decision_id=%s state_id=%s "
                "cycle_number=%d status=%s",
                state.decision_id,
                state.state_id,
                state.cycle_number,
                state.current_status.value,
            )
            return existing or state, False
        return state, True

    def get_adaptive_state(
        self, decision_id: UUID, state_id: UUID
    ) -> AdaptiveExperimentState | None:
        item = self._gateway.get_item(
            {"PK": _decision_pk(decision_id), "SK": _adaptive_sk(state_id)}
        )
        return AdaptiveExperimentState.model_validate(_strip_keys(item)) if item else None

    def list_adaptive_states(self, decision_id: UUID) -> list[AdaptiveExperimentState]:
        """Every adaptive state ever recorded for a decision, oldest
        first - the decision's full validation-journey history.

        Explicitly sorted by `created_at` after the query rather than
        relying on DynamoDB's own SK ordering: `SK=ADAPTIVE_STATE#<state_id>`
        sorts lexicographically by the (deterministic, content-derived -
        see `AdaptiveExperimentService._state_id_for`) state id, which has
        no relationship to creation order.
        """
        key_condition = Key("PK").eq(_decision_pk(decision_id)) & Key("SK").begins_with(
            "ADAPTIVE_STATE#"
        )
        items, _ = self._gateway.query(key_condition=key_condition)
        states = [AdaptiveExperimentState.model_validate(_strip_keys(item)) for item in items]
        return sorted(states, key=lambda state: state.created_at)

    def get_latest_adaptive_state(self, decision_id: UUID) -> AdaptiveExperimentState | None:
        """The most recently created state for a decision, or `None` if
        the adaptive loop has never run for it yet - a single, bounded
        `Query` on the decision's own partition, never a scan."""
        states = self.list_adaptive_states(decision_id)
        if not states:
            return None
        return max(states, key=lambda state: state.created_at)

    def update_adaptive_state(
        self,
        decision_id: UUID,
        state_id: UUID,
        current_status: str | None = None,
        stopping_reason: str | None = None,
    ) -> AdaptiveExperimentState | None:
        """Narrow, targeted update to an EXISTING state record - never a
        full overwrite of its snapshot fields (see module docstring).

        The only supported use today is the user manually stopping the
        loop (`current_status=user_stopped`) - see
        `AdaptiveExperimentService.stop`. Returns `None` (never raises)
        if the target record no longer exists, mirroring this codebase's
        general tolerance for best-effort bookkeeping updates.
        """
        set_clauses = ["updated_at = :updated_at"]
        values: dict[str, Any] = {":updated_at": datetime.now(UTC).isoformat()}
        names: dict[str, str] = {}

        if current_status is not None:
            set_clauses.append("#current_status = :current_status")
            values[":current_status"] = current_status
            names["#current_status"] = "current_status"
        if stopping_reason is not None:
            set_clauses.append("stopping_reason = :stopping_reason")
            values[":stopping_reason"] = stopping_reason

        with suppress(Exception):
            updated = self._gateway.update_item(
                key={"PK": _decision_pk(decision_id), "SK": _adaptive_sk(state_id)},
                update_expression="SET " + ", ".join(set_clauses),
                expression_attribute_values=values,
                expression_attribute_names=names or None,
                condition=Attr("PK").exists(),
            )
            return AdaptiveExperimentState.model_validate(_strip_keys(updated))
        return None


def _state_to_item(state: AdaptiveExperimentState) -> dict[str, Any]:
    dumped = state.model_dump(mode="json")
    return {
        "PK": _decision_pk(state.decision_id),
        "SK": _adaptive_sk(state.state_id),
        "entity_type": "ADAPTIVE_STATE",
        **dumped,
    }


def _strip_keys(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in item.items()
        if key not in {"PK", "SK", "GSI1PK", "GSI1SK", "GSI2PK", "GSI2SK", "entity_type"}
    }
