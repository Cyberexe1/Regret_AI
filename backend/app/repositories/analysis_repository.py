"""DynamoDB-backed analysis run storage.

Key layout: PK=DECISION#<decision_id>  SK=ANALYSIS#<run_id>

An analysis run tracks one pass of the (not-yet-implemented) agent
pipeline over a decision: when it started, whether it finished, and why it
failed if it did. No AI or Strands/Bedrock code exists yet - this is only
the storage shape a future orchestrator would write into.

Not exposed through any public route yet.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from boto3.dynamodb.conditions import Attr, Key

from app.repositories.dynamodb import DynamoDBGateway
from app.schemas.decision_resources import AnalysisRun, AnalysisRunStatus


def _decision_pk(decision_id: UUID | str) -> str:
    return f"DECISION#{decision_id}"


def _analysis_sk(run_id: UUID | str) -> str:
    return f"ANALYSIS#{run_id}"


class AnalysisRepository:
    """Stores analysis run records for decisions."""

    def __init__(self, gateway: DynamoDBGateway | None = None) -> None:
        self._gateway = gateway if gateway is not None else DynamoDBGateway()

    def create(self, decision_id: UUID) -> AnalysisRun:
        run_id = uuid4()
        item = {
            "PK": _decision_pk(decision_id),
            "SK": _analysis_sk(run_id),
            "entity_type": "ANALYSIS",
            "id": str(run_id),
            "decision_id": str(decision_id),
            "status": AnalysisRunStatus.QUEUED.value,
            "started_at": None,
            "completed_at": None,
            "error_message": None,
        }
        self._gateway.put_item(item)
        return AnalysisRun.model_validate(_strip_keys(item))

    def get(self, decision_id: UUID, run_id: UUID) -> AnalysisRun | None:
        item = self._gateway.get_item(
            {"PK": _decision_pk(decision_id), "SK": _analysis_sk(run_id)}
        )
        return AnalysisRun.model_validate(_strip_keys(item)) if item is not None else None

    def list_for_decision(self, decision_id: UUID) -> list[AnalysisRun]:
        items, _ = self._gateway.query(
            key_condition=Key("PK").eq(_decision_pk(decision_id)) & Key("SK").begins_with("ANALYSIS#")
        )
        return [AnalysisRun.model_validate(_strip_keys(item)) for item in items]

    def update_status(
        self,
        decision_id: UUID,
        run_id: UUID,
        status: AnalysisRunStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error_message: str | None = None,
    ) -> AnalysisRun:
        set_clauses = ["#status = :status"]
        values: dict[str, Any] = {":status": status.value}
        names: dict[str, str] = {"#status": "status"}

        if started_at is not None:
            set_clauses.append("started_at = :started_at")
            values[":started_at"] = started_at.isoformat()
        if completed_at is not None:
            set_clauses.append("completed_at = :completed_at")
            values[":completed_at"] = completed_at.isoformat()
        if error_message is not None:
            set_clauses.append("error_message = :error_message")
            values[":error_message"] = error_message

        updated = self._gateway.update_item(
            key={"PK": _decision_pk(decision_id), "SK": _analysis_sk(run_id)},
            update_expression="SET " + ", ".join(set_clauses),
            expression_attribute_values=values,
            expression_attribute_names=names,
            condition=Attr("PK").exists(),
        )
        return AnalysisRun.model_validate(_strip_keys(updated))


def _strip_keys(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if key not in {"PK", "SK", "entity_type"}}
