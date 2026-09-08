"""DynamoDB-backed evidence metadata storage.

Key layout: PK=DECISION#<decision_id>  SK=EVIDENCE#<evidence_id>

Only metadata and references are stored here - large uploaded documents are
never written to DynamoDB. `storage_key` is reserved for an eventual Amazon
S3 object key once document ingestion is implemented; this step only
prepares the shape.

Not exposed through any public route yet.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from boto3.dynamodb.conditions import Key

from app.repositories.dynamodb import DynamoDBGateway
from app.schemas.decision_resources import Evidence, SourceType


def _decision_pk(decision_id: UUID | str) -> str:
    return f"DECISION#{decision_id}"


def _evidence_sk(evidence_id: UUID | str) -> str:
    return f"EVIDENCE#{evidence_id}"


class EvidenceRepository:
    """Stores evidence metadata for decisions."""

    def __init__(self, gateway: DynamoDBGateway | None = None) -> None:
        self._gateway = gateway if gateway is not None else DynamoDBGateway()

    def create(
        self,
        decision_id: UUID,
        title: str,
        source_type: SourceType,
        source_url: str | None = None,
        storage_key: str | None = None,
        content_reference: str | None = None,
        credibility: str | None = None,
    ) -> Evidence:
        evidence_id = uuid4()
        now = datetime.now(UTC).isoformat()

        item = {
            "PK": _decision_pk(decision_id),
            "SK": _evidence_sk(evidence_id),
            "entity_type": "EVIDENCE",
            "id": str(evidence_id),
            "decision_id": str(decision_id),
            "title": title,
            "source_type": source_type.value,
            "source_url": source_url,
            "storage_key": storage_key,
            "content_reference": content_reference,
            "credibility": credibility,
            "created_at": now,
        }
        self._gateway.put_item(item)
        return Evidence.model_validate(_strip_keys(item))

    def get(self, decision_id: UUID, evidence_id: UUID) -> Evidence | None:
        item = self._gateway.get_item(
            {"PK": _decision_pk(decision_id), "SK": _evidence_sk(evidence_id)}
        )
        return Evidence.model_validate(_strip_keys(item)) if item is not None else None

    def list_for_decision(self, decision_id: UUID) -> list[Evidence]:
        items, _ = self._gateway.query(
            key_condition=Key("PK").eq(_decision_pk(decision_id)) & Key("SK").begins_with("EVIDENCE#")
        )
        return [Evidence.model_validate(_strip_keys(item)) for item in items]


def _strip_keys(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if key not in {"PK", "SK", "entity_type"}}
