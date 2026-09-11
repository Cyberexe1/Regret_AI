"""DynamoDB-backed Value-of-Information analysis storage (REGRET ENGINE
2.0, Step 20).

Uses the EXISTING single-table design (see `app.repositories.dynamodb`
and `app.repositories.decision_repository`'s module docstring) - no
second database, no new table. Key layout:

    ValueOfInformationAnalysis:  PK=DECISION#<decision_id>   SK=VOI#<analysis_id>

Lives in the same decision partition as every other entity, so "get
everything about this decision" stays a single `Query` on `PK`. Mirrors
`AnalysisRepository`/`app.repositories.decision_repository`'s
`create_reevaluation` in one specific way: append-only. A later recompute
(e.g. after an experiment result changes the evidence - see spec section
21) creates a NEW `SK=VOI#<new_analysis_id>` record; the previous one is
never deleted or overwritten, only marked `superseded_by_analysis_id` via
`mark_superseded` - so the decision's full prioritization history stays
reconstructable, exactly like `ReEvaluation`'s own "nothing is ever
overwritten" convention.
"""

from contextlib import suppress
from typing import Any
from uuid import UUID

from boto3.dynamodb.conditions import Attr, Key

from app.agents.value_of_information_schemas import ValueOfInformationAnalysis
from app.repositories.dynamodb import DynamoDBGateway


def _decision_pk(decision_id: UUID | str) -> str:
    return f"DECISION#{decision_id}"


def _voi_sk(analysis_id: UUID | str) -> str:
    return f"VOI#{analysis_id}"


class ValueOfInformationRepository:
    """Stores `ValueOfInformationAnalysis` records for decisions.

    Contains no scoring logic - that lives entirely in
    `app.services.value_of_information_service`. This class only knows
    how to read and write the already-computed analysis against the
    existing table.
    """

    def __init__(self, gateway: DynamoDBGateway | None = None) -> None:
        self._gateway = gateway if gateway is not None else DynamoDBGateway()

    def create(self, analysis: ValueOfInformationAnalysis) -> ValueOfInformationAnalysis:
        """Persist a new analysis. Guarded by a fresh-id safety net, the
        same convention every other `create()` in this codebase uses."""
        item = _analysis_to_item(analysis)
        self._gateway.put_item(item, condition=Attr("PK").not_exists())
        return analysis

    def get(self, decision_id: UUID, analysis_id: UUID) -> ValueOfInformationAnalysis | None:
        item = self._gateway.get_item(
            {"PK": _decision_pk(decision_id), "SK": _voi_sk(analysis_id)}
        )
        return ValueOfInformationAnalysis.model_validate(_strip_keys(item)) if item else None

    def list_for_decision(self, decision_id: UUID) -> list[ValueOfInformationAnalysis]:
        """Every VOI analysis ever computed for a decision, oldest first -
        the decision's full prioritization history."""
        key_condition = Key("PK").eq(_decision_pk(decision_id)) & Key("SK").begins_with("VOI#")
        items, _ = self._gateway.query(key_condition=key_condition)
        return [ValueOfInformationAnalysis.model_validate(_strip_keys(item)) for item in items]

    def get_latest(self, decision_id: UUID) -> ValueOfInformationAnalysis | None:
        """The most recently computed analysis for a decision (by
        `created_at`), regardless of whether it has since been
        superseded - `superseded_by_analysis_id` on the returned record
        (if set) tells the caller a newer one exists. A single, bounded
        `Query` on the decision's own partition, never a scan.
        """
        analyses = self.list_for_decision(decision_id)
        if not analyses:
            return None
        return max(analyses, key=lambda item: item.created_at)

    def mark_superseded(self, decision_id: UUID, analysis_id: UUID, superseded_by: UUID) -> None:
        """Record that a newer analysis supersedes this one, WITHOUT
        deleting or overwriting anything else about it - see module
        docstring. A no-op (not an error) if the target record no longer
        exists, mirroring this codebase's general tolerance for
        best-effort bookkeeping updates that must never fail a caller's
        primary operation.
        """
        with suppress(Exception):  # best-effort bookkeeping, never fails the caller
            self._gateway.update_item(
                key={"PK": _decision_pk(decision_id), "SK": _voi_sk(analysis_id)},
                update_expression="SET superseded_by_analysis_id = :superseded_by",
                expression_attribute_values={":superseded_by": str(superseded_by)},
                condition=Attr("PK").exists(),
            )


def _analysis_to_item(analysis: ValueOfInformationAnalysis) -> dict[str, Any]:
    dumped = analysis.model_dump(mode="json")
    return {
        "PK": _decision_pk(analysis.decision_id),
        "SK": _voi_sk(analysis.analysis_id),
        "entity_type": "VOI_ANALYSIS",
        **dumped,
    }


def _strip_keys(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in item.items()
        if key not in {"PK", "SK", "GSI1PK", "GSI1SK", "GSI2PK", "GSI2SK", "entity_type"}
    }
