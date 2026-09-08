"""DynamoDB-backed decision storage.

Single-table design. Key layout:

- Decision item:      PK=DECISION#<id>          SK=METADATA
                       GSI1PK=USER#<user_id>     GSI1SK=DECISION#<created_at>#<id>
- Child entities live under the same decision partition, e.g.:
                       PK=DECISION#<id>          SK=ASSUMPTION#<assumption_id>
                       PK=DECISION#<id>          SK=BLINDSPOT#<blindspot_id>
                       PK=DECISION#<id>          SK=SCENARIO#<scenario_id>
                       PK=DECISION#<id>          SK=THRESHOLD#<threshold_id>
                       PK=DECISION#<id>          SK=EXPERIMENT#<experiment_id>

Putting every entity that belongs to a decision under the `DECISION#<id>`
partition means "get everything about this decision" is a single Query on
PK, with no scan. Listing a user's decisions instead goes through GSI1,
which is the only access pattern that needs to fan out across decisions
rather than within one.

Evidence and analysis runs have their own repository files
(`evidence_repository.py`, `analysis_repository.py`) per the spec, but
follow the exact same partitioning scheme.
"""

import base64
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from boto3.dynamodb.conditions import Attr, Key

from app.repositories.dynamodb import DynamoDBGateway
from app.schemas.decision import DecisionCreate, DecisionResponse, DecisionStatus, DecisionUpdate
from app.schemas.decision_resources import Assumption, Blindspot, Experiment, Scenario, Threshold

_METADATA_SK = "METADATA"


def _decision_pk(decision_id: UUID | str) -> str:
    return f"DECISION#{decision_id}"


def _user_gsi1pk(user_id: str) -> str:
    return f"USER#{user_id}"


def _decision_gsi1sk(created_at: str, decision_id: UUID | str) -> str:
    return f"DECISION#{created_at}#{decision_id}"


def _encode_cursor(last_evaluated_key: dict[str, Any] | None) -> str | None:
    if not last_evaluated_key:
        return None
    raw = json.dumps(last_evaluated_key, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(cursor: str | None) -> dict[str, Any] | None:
    if not cursor:
        return None
    raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
    return json.loads(raw)


class DecisionRepository:
    """CRUD + query operations for decisions and their child entities."""

    def __init__(self, gateway: DynamoDBGateway | None = None) -> None:
        self._gateway = gateway if gateway is not None else DynamoDBGateway()

    # --- Decision CRUD -------------------------------------------------------

    def create(self, user_id: str, payload: DecisionCreate) -> DecisionResponse:
        decision_id = uuid4()
        now = datetime.now(UTC).isoformat()

        item = {
            "PK": _decision_pk(decision_id),
            "SK": _METADATA_SK,
            "entity_type": "DECISION",
            "GSI1PK": _user_gsi1pk(user_id),
            "GSI1SK": _decision_gsi1sk(now, decision_id),
            "id": str(decision_id),
            "user_id": user_id,
            "title": payload.title,
            "description": payload.description,
            "desired_outcome": payload.desired_outcome,
            "budget": payload.budget,
            "currency": payload.currency,
            "timeline": payload.timeline,
            "location": payload.location,
            "risk_tolerance": payload.risk_tolerance,
            "beliefs": payload.beliefs,
            "status": DecisionStatus.DRAFT.value,
            "created_at": now,
            "updated_at": now,
        }
        # A decision id is freshly generated, so this should never collide -
        # the condition exists purely as a safety net against a UUID clash.
        self._gateway.put_item(item, condition=Attr("PK").not_exists())
        return self.to_response(item)

    def get(self, decision_id: UUID) -> DecisionResponse | None:
        item = self._gateway.get_item({"PK": _decision_pk(decision_id), "SK": _METADATA_SK})
        return self.to_response(item) if item is not None else None

    def get_raw(self, decision_id: UUID) -> dict[str, Any] | None:
        """Internal variant that also exposes `user_id`, for ownership checks."""
        return self._gateway.get_item({"PK": _decision_pk(decision_id), "SK": _METADATA_SK})

    def list_for_user(
        self, user_id: str, limit: int = 20, cursor: str | None = None
    ) -> tuple[list[DecisionResponse], str | None]:
        items, last_evaluated_key = self._gateway.query(
            key_condition=Key("GSI1PK").eq(_user_gsi1pk(user_id)),
            index_name="GSI1",
            limit=limit,
            exclusive_start_key=_decode_cursor(cursor),
            scan_index_forward=False,  # newest first
        )
        return [self.to_response(item) for item in items], _encode_cursor(last_evaluated_key)

    def update(self, decision_id: UUID, payload: DecisionUpdate) -> DecisionResponse:
        now = datetime.now(UTC).isoformat()
        fields = payload.model_dump(exclude_unset=True, exclude={"expected_updated_at"})

        set_clauses = ["updated_at = :updated_at"]
        values: dict[str, Any] = {":updated_at": now}
        names: dict[str, str] = {}

        for field_name, value in fields.items():
            placeholder = f":{field_name}"
            name_placeholder = f"#{field_name}"
            set_clauses.append(f"{name_placeholder} = {placeholder}")
            values[placeholder] = value.value if isinstance(value, DecisionStatus) else value
            names[name_placeholder] = field_name

        update_expression = "SET " + ", ".join(set_clauses)

        condition = Attr("PK").exists()
        if payload.expected_updated_at is not None:
            condition = condition & Attr("updated_at").eq(payload.expected_updated_at.isoformat())

        updated = self._gateway.update_item(
            key={"PK": _decision_pk(decision_id), "SK": _METADATA_SK},
            update_expression=update_expression,
            expression_attribute_values=values,
            expression_attribute_names=names or None,
            condition=condition,
        )
        return self.to_response(updated)

    def delete(self, decision_id: UUID) -> None:
        self._gateway.delete_item(
            key={"PK": _decision_pk(decision_id), "SK": _METADATA_SK},
            condition=Attr("PK").exists(),
        )

    # --- Child entity reads ---------------------------------------------------
    # None of these are exposed through public routes yet; they exist so the
    # future analysis pipeline has somewhere concrete to read from once it
    # starts writing assumptions/blindspots/scenarios/thresholds/experiments.

    def list_assumptions(self, decision_id: UUID) -> list[Assumption]:
        items = self._query_children(decision_id, "ASSUMPTION#")
        return [Assumption.model_validate(_strip_keys(item)) for item in items]

    def list_blindspots(self, decision_id: UUID) -> list[Blindspot]:
        items = self._query_children(decision_id, "BLINDSPOT#")
        return [Blindspot.model_validate(_strip_keys(item)) for item in items]

    def list_scenarios(self, decision_id: UUID) -> list[Scenario]:
        items = self._query_children(decision_id, "SCENARIO#")
        return [Scenario.model_validate(_strip_keys(item)) for item in items]

    def list_thresholds(self, decision_id: UUID) -> list[Threshold]:
        items = self._query_children(decision_id, "THRESHOLD#")
        return [Threshold.model_validate(_strip_keys(item)) for item in items]

    def list_experiments(self, decision_id: UUID) -> list[Experiment]:
        items = self._query_children(decision_id, "EXPERIMENT#")
        return [Experiment.model_validate(_strip_keys(item)) for item in items]

    def _query_children(self, decision_id: UUID, sk_prefix: str) -> list[dict[str, Any]]:
        items, _ = self._gateway.query(
            key_condition=Key("PK").eq(_decision_pk(decision_id)) & Key("SK").begins_with(sk_prefix)
        )
        return items

    @staticmethod
    def to_response(item: dict[str, Any]) -> DecisionResponse:
        return DecisionResponse(
            id=item["id"],
            title=item["title"],
            description=item["description"],
            desired_outcome=item.get("desired_outcome"),
            budget=item.get("budget"),
            currency=item.get("currency"),
            timeline=item.get("timeline"),
            location=item.get("location"),
            risk_tolerance=item.get("risk_tolerance"),
            beliefs=item.get("beliefs"),
            status=item["status"],
            created_at=item["created_at"],
            updated_at=item["updated_at"],
        )


def _strip_keys(item: dict[str, Any]) -> dict[str, Any]:
    """Drop DynamoDB key/index attributes before validating into a schema."""
    return {
        key: value
        for key, value in item.items()
        if key not in {"PK", "SK", "GSI1PK", "GSI1SK", "entity_type"}
    }
