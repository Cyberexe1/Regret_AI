"""DynamoDB-backed Cross-Decision Pattern storage (REGRET ENGINE 2.0,
Step 23).

Uses the EXISTING single-table design (see `app.repositories.dynamodb`)
- no second database, no new table. Key layout:

    CrossDecisionPattern:   PK=USER#<user_id>   SK=PATTERN#<pattern_id>
    PatternOccurrence:      PK=USER#<user_id>   SK=PATTERN#<pattern_id>#OCCURRENCE#<occurrence_id>

This is the first entity in the codebase partitioned by `USER#<user_id>`
rather than `DECISION#<decision_id>` - deliberately so, because a pattern
is fundamentally about ONE user's history across MANY decisions, not
about one decision. Occurrences are nested under the SAME user partition
(never a separate `PATTERN#<id>` top-level partition) specifically so
every single query in this module is trivially, structurally user-scoped
by its own partition key - there is no way to accidentally construct a
query here that could return another user's data, because the partition
key IS the user id.

Both entities are append-only in spirit but upserted by a deterministic
id: `pattern_id` is derived from `(user_id, pattern_type, normalized_key)`
and `occurrence_id` from `(pattern_id, decision_id, source_type,
source_id)` - see `app.learning.pattern_detector` - so re-running
`CrossDecisionLearningService.refresh_patterns` (spec section 11's
"idempotent" requirement) always updates the SAME record rather than
creating a duplicate, exactly like `AdaptiveStateRepository`'s own
deterministic-id convention.
"""

from typing import Any

from boto3.dynamodb.conditions import Key

from app.core.logging import get_logger
from app.learning.schemas import CrossDecisionPattern, PatternOccurrence
from app.repositories.dynamodb import DynamoDBGateway

logger = get_logger(__name__)


def _user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def _pattern_sk(pattern_id: str) -> str:
    return f"PATTERN#{pattern_id}"


def _occurrence_sk(pattern_id: str, occurrence_id: str) -> str:
    return f"PATTERN#{pattern_id}#OCCURRENCE#{occurrence_id}"


class CrossDecisionLearningRepository:
    """Stores `CrossDecisionPattern`/`PatternOccurrence` records, always
    scoped to one user's own partition.

    Contains no pattern-detection logic - that lives entirely in
    `app.learning.pattern_detector`/`app.learning.service`. This class
    only knows how to read and write already-computed patterns against
    the existing table, and it never accepts a query that isn't scoped
    to a specific `user_id`.
    """

    def __init__(self, gateway: DynamoDBGateway | None = None) -> None:
        self._gateway = gateway if gateway is not None else DynamoDBGateway()

    # --- patterns ------------------------------------------------------------

    def upsert_pattern(self, pattern: CrossDecisionPattern) -> CrossDecisionPattern:
        """Create or fully replace a pattern record. Safe to call
        repeatedly with a re-detected pattern for the same
        `(user_id, pattern_type, normalized_key)` - `pattern_id` is
        deterministic (see module docstring), so this always updates the
        SAME item rather than creating a duplicate. No conditional write
        is used here (unlike most other `create_*` methods in this
        codebase) because an upsert is explicitly meant to overwrite the
        previous computation of the SAME pattern - the provenance that
        must never be lost lives in the `PatternOccurrence` rows, which
        are append-only-by-id (see `upsert_occurrence`), not in the
        pattern summary record itself.
        """
        item = _pattern_to_item(pattern)
        self._gateway.put_item(item)
        return pattern

    def get_pattern(self, user_id: str, pattern_id: str) -> CrossDecisionPattern | None:
        item = self._gateway.get_item({"PK": _user_pk(user_id), "SK": _pattern_sk(pattern_id)})
        return CrossDecisionPattern.model_validate(_strip_keys(item)) if item else None

    def list_patterns_for_user(
        self,
        user_id: str,
        pattern_type: str | None = None,
        status: str | None = None,
        domain: str | None = None,
        variable: str | None = None,
    ) -> list[CrossDecisionPattern]:
        """Every pattern ever recorded for one user - a single, bounded
        `Query` on that user's own partition (never a table scan), with
        optional filters applied in-memory afterward. `user_id` is
        REQUIRED (not optional) precisely so this method can never be
        called in a way that would return more than one user's data.
        """
        key_condition = Key("PK").eq(_user_pk(user_id)) & Key("SK").begins_with("PATTERN#")
        items, _ = self._gateway.query(key_condition=key_condition)
        patterns = [
            CrossDecisionPattern.model_validate(_strip_keys(item))
            for item in items
            if "#OCCURRENCE#" not in item["SK"]
        ]

        if pattern_type is not None:
            patterns = [p for p in patterns if p.pattern_type.value == pattern_type]
        if status is not None:
            patterns = [p for p in patterns if p.status.value == status]
        if domain is not None:
            patterns = [p for p in patterns if p.domain == domain]
        if variable is not None:
            patterns = [p for p in patterns if p.variable == variable]

        return sorted(patterns, key=lambda p: p.last_seen_at, reverse=True)

    def get_patterns_for_decision(
        self, user_id: str, decision_id: str
    ) -> list[CrossDecisionPattern]:
        """Every pattern that names this decision as supporting or
        contradicting evidence - filters the user's own (already
        user-scoped) pattern list in-memory rather than a second query,
        since one user's total pattern count is always bounded by their
        own decision count."""
        all_patterns = self.list_patterns_for_user(user_id)
        return [
            p
            for p in all_patterns
            if decision_id in p.supporting_decision_ids
            or decision_id in p.contradicting_decision_ids
        ]

    def find_pattern_by_normalized_key(
        self, user_id: str, pattern_id: str
    ) -> CrossDecisionPattern | None:
        """Looks up a pattern by its own deterministic id - the caller
        (see `app.learning.pattern_detector`) computes `pattern_id` from
        `(user_id, pattern_type, normalized_key)` itself, so this is
        simply `get_pattern` under a name matching the spec's suggested
        method list."""
        return self.get_pattern(user_id, pattern_id)

    # --- occurrences -----------------------------------------------------------

    def upsert_occurrence(self, occurrence: PatternOccurrence) -> PatternOccurrence:
        """Create or replace one provenance record. `occurrence_id` is
        deterministic (see module docstring) so re-detecting the exact
        same real evidence never creates a duplicate occurrence."""
        item = _occurrence_to_item(occurrence)
        self._gateway.put_item(item)
        return occurrence

    def list_pattern_occurrences(self, user_id: str, pattern_id: str) -> list[PatternOccurrence]:
        """Every real occurrence recorded for one pattern - a single,
        bounded `Query` scoped to the user's own partition AND the
        pattern's own SK prefix, never a scan."""
        key_condition = Key("PK").eq(_user_pk(user_id)) & Key("SK").begins_with(
            f"PATTERN#{pattern_id}#OCCURRENCE#"
        )
        items, _ = self._gateway.query(key_condition=key_condition)
        occurrences = [PatternOccurrence.model_validate(_strip_keys(item)) for item in items]
        return sorted(occurrences, key=lambda o: o.observed_at)

    def delete_occurrences_for_pattern(self, user_id: str, pattern_id: str) -> None:
        """Removes every occurrence currently recorded for a pattern -
        used only by `refresh_patterns` immediately before re-writing the
        current set, so a source record that's no longer relevant (e.g.
        it was superseded by a later re-evaluation) doesn't linger as
        stale provenance forever. The pattern's own summary record and
        `first_seen_at` are never touched by this - only its occurrence
        rows are replaced with a fresh, currently-accurate set.
        """
        for occurrence in self.list_pattern_occurrences(user_id, pattern_id):
            self._gateway.delete_item(
                {
                    "PK": _user_pk(user_id),
                    "SK": _occurrence_sk(pattern_id, occurrence.occurrence_id),
                }
            )


def _pattern_to_item(pattern: CrossDecisionPattern) -> dict[str, Any]:
    dumped = pattern.model_dump(mode="json")
    return {
        "PK": _user_pk(pattern.user_id),
        "SK": _pattern_sk(pattern.pattern_id),
        "entity_type": "CROSS_DECISION_PATTERN",
        **dumped,
    }


def _occurrence_to_item(occurrence: PatternOccurrence) -> dict[str, Any]:
    dumped = occurrence.model_dump(mode="json")
    return {
        "PK": _user_pk(occurrence.user_id),
        "SK": _occurrence_sk(occurrence.pattern_id, occurrence.occurrence_id),
        "entity_type": "PATTERN_OCCURRENCE",
        **dumped,
    }


def _strip_keys(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in item.items()
        if key not in {"PK", "SK", "GSI1PK", "GSI1SK", "GSI2PK", "GSI2SK", "entity_type"}
    }
