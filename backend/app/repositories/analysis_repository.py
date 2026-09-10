"""DynamoDB-backed analysis run storage.

Key layout: PK=DECISION#<decision_id>  SK=ANALYSIS#<run_id>

An analysis run tracks one pass of the full agent pipeline (Decision
Analyzer through Experiment Planner) over a decision: when it started,
its per-stage progress (`agent_statuses`), whether it finished, and why it
failed if it did. `created_at` is set once at creation; `updated_at` is
bumped on every `update_status` call, so a caller polling
`GET /decisions/{id}/analysis/{run_id}` can see the record is still making
progress, not just that it's stuck `running`.

Exposed read-only via `GET /decisions/{decision_id}/analysis/{run_id}`
(see `app.api.routes.analysis`); only `AnalysisOrchestrator` ever creates
or updates a run.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from boto3.dynamodb.conditions import Attr, Key

from app.repositories.dynamodb import DynamoDBGateway
from app.schemas.decision_resources import AgentRunStatus, AnalysisRun, AnalysisRunStatus


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
        now = datetime.now(UTC).isoformat()
        item = {
            "PK": _decision_pk(decision_id),
            "SK": _analysis_sk(run_id),
            "entity_type": "ANALYSIS",
            "id": str(run_id),
            "decision_id": str(decision_id),
            "status": AnalysisRunStatus.QUEUED.value,
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "completed_at": None,
            "error_message": None,
            "result": None,
            "agent_statuses": None,
        }
        self._gateway.put_item(item)
        return AnalysisRun.model_validate(_strip_keys(item))

    def get(self, decision_id: UUID, run_id: UUID) -> AnalysisRun | None:
        item = self._gateway.get_item(
            {"PK": _decision_pk(decision_id), "SK": _analysis_sk(run_id)}
        )
        return AnalysisRun.model_validate(_strip_keys(item)) if item is not None else None

    def list_for_decision(self, decision_id: UUID) -> list[AnalysisRun]:
        key_condition = Key("PK").eq(_decision_pk(decision_id)) & Key("SK").begins_with("ANALYSIS#")
        items, _ = self._gateway.query(key_condition=key_condition)
        return [AnalysisRun.model_validate(_strip_keys(item)) for item in items]

    def get_active_run(self, decision_id: UUID) -> AnalysisRun | None:
        """Return an in-flight (`queued`/`running`) run for this decision, if any.

        Used by `AnalysisOrchestrator.run_analysis` for idempotency: a
        second `POST /decisions/{id}/analyze` call while one is already
        in flight returns the existing run rather than starting a
        duplicate, expensive pipeline. `list_for_decision` is a single,
        bounded `Query` on the decision's own partition (never a scan),
        so checking this on every `/analyze` call stays cheap even as a
        decision accumulates many historical runs.
        """
        for run in self.list_for_decision(decision_id):
            if run.status in (AnalysisRunStatus.QUEUED, AnalysisRunStatus.RUNNING):
                return run
        return None

    def update_status(
        self,
        decision_id: UUID,
        run_id: UUID,
        status: AnalysisRunStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error_message: str | None = None,
        result: dict[str, Any] | None = None,
        agent_statuses: dict[str, AgentRunStatus] | None = None,
    ) -> AnalysisRun:
        set_clauses = ["#status = :status", "updated_at = :updated_at"]
        values: dict[str, Any] = {
            ":status": status.value,
            ":updated_at": datetime.now(UTC).isoformat(),
        }
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
        if result is not None:
            set_clauses.append("#result = :result")
            values[":result"] = result
            names["#result"] = "result"
        if agent_statuses is not None:
            set_clauses.append("agent_statuses = :agent_statuses")
            values[":agent_statuses"] = {
                agent_id: agent_status.value for agent_id, agent_status in agent_statuses.items()
            }

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
