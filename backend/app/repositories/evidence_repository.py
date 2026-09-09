"""DynamoDB-backed evidence metadata storage.

Key layout: PK=DECISION#<decision_id>  SK=EVIDENCE#<evidence_id>

Only metadata, a bounded extract of text, and a storage reference are
stored here - the original uploaded file lives in a `StorageBackend` (local
disk today, Amazon S3 later), never inline in DynamoDB.

`get_by_id` supports the `GET /api/v1/evidence/{evidence_id}` and
`DELETE /api/v1/evidence/{evidence_id}` routes, which only have the
evidence id, not its parent decision id. Since the primary key requires
both, this issues a bounded `Query` against a `GSI2` keyed purely on the
evidence id rather than a table-wide `Scan`.
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


def _evidence_gsi2pk(evidence_id: UUID | str) -> str:
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
        storage_key: str | None = None,
        filename: str | None = None,
        file_type: str | None = None,
        size_bytes: int | None = None,
        page_count: int | None = None,
        content_reference: str | None = None,
        content_truncated: bool = False,
        source_url: str | None = None,
        credibility: str | None = None,
    ) -> Evidence:
        evidence_id = uuid4()
        now = datetime.now(UTC).isoformat()

        item = {
            "PK": _decision_pk(decision_id),
            "SK": _evidence_sk(evidence_id),
            "entity_type": "EVIDENCE",
            # GSI2 exists solely so a bare evidence id (no decision id) can
            # be resolved without a table scan - see module docstring.
            "GSI2PK": _evidence_gsi2pk(evidence_id),
            "GSI2SK": _evidence_gsi2pk(evidence_id),
            "id": str(evidence_id),
            "decision_id": str(decision_id),
            "title": title,
            "source_type": source_type.value,
            "source_url": source_url,
            "storage_key": storage_key,
            "filename": filename,
            "file_type": file_type,
            "size_bytes": size_bytes,
            "page_count": page_count,
            "content_reference": content_reference,
            "content_truncated": content_truncated,
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

    def get_by_id(self, evidence_id: UUID) -> Evidence | None:
        """Look up evidence by its own id alone, without knowing its decision."""
        items, _ = self._gateway.query(
            key_condition=Key("GSI2PK").eq(_evidence_gsi2pk(evidence_id)),
            index_name="GSI2",
            limit=1,
        )
        return Evidence.model_validate(_strip_keys(items[0])) if items else None

    def list_for_decision(self, decision_id: UUID) -> list[Evidence]:
        key_condition = Key("PK").eq(_decision_pk(decision_id)) & Key("SK").begins_with("EVIDENCE#")
        items, _ = self._gateway.query(key_condition=key_condition)
        return [Evidence.model_validate(_strip_keys(item)) for item in items]

    def delete(self, decision_id: UUID, evidence_id: UUID) -> None:
        self._gateway.delete_item(
            key={"PK": _decision_pk(decision_id), "SK": _evidence_sk(evidence_id)}
        )


def _strip_keys(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in item.items()
        if key not in {"PK", "SK", "GSI2PK", "GSI2SK", "entity_type"}
    }
