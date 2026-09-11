"""DynamoDB-backed Quality Assessment & Calibration storage (REGRET
ENGINE 2.0, Step 24).

Uses the EXISTING single-table design (see `app.repositories.dynamodb`)
- no second database, no new table. Key layout:

    QualityAssessment:   PK=DECISION#<decision_id>   SK=QUALITY#<quality_id>
    CalibrationInsight:  PK=USER#<user_id>            SK=CALIBRATION#<calibration_id>

`QualityAssessment` lives in the same decision partition as every other
per-decision entity (mirrors `ValueOfInformationRepository`/
`AdaptiveStateRepository` exactly - append-only, a new assessment never
overwrites a previous one, so the full "how much did we trust this
analysis, and when" history stays reconstructable).

`CalibrationInsight` lives under `PK=USER#<user_id>`, the SAME
user-scoped partition `CrossDecisionLearningRepository` introduced in
Step 23 - the partition key itself is what makes cross-user leakage
structurally impossible, not merely a convention. `CalibrationInsight`
is upserted by a deterministic id (same variable/user always updates the
SAME record) since it's a rolling aggregate, not an append-only history
of its own - the underlying `ThresholdComparison`/`ReEvaluation` records
it's computed from remain the append-only source of truth.
"""

from typing import Any

from boto3.dynamodb.conditions import Key

from app.learning.normalization import normalize_variable
from app.quality.calibration import CalibrationInsight, deterministic_calibration_id
from app.quality.schemas import QualityAssessment
from app.repositories.dynamodb import DynamoDBGateway


def _decision_pk(decision_id: str) -> str:
    return f"DECISION#{decision_id}"


def _quality_sk(quality_id: str) -> str:
    return f"QUALITY#{quality_id}"


def _user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def _calibration_sk(calibration_id: str) -> str:
    return f"CALIBRATION#{calibration_id}"


class QualityRepository:
    """Stores `QualityAssessment` records for decisions. Contains no
    check logic - that lives entirely in `app.quality.rules`/
    `app.quality.service`. This class only knows how to read and write
    the already-computed assessment against the existing table."""

    def __init__(self, gateway: DynamoDBGateway | None = None) -> None:
        self._gateway = gateway if gateway is not None else DynamoDBGateway()

    def create(self, assessment: QualityAssessment) -> QualityAssessment:
        """Persist a new assessment. Never overwrites a previous one -
        append-only, exactly like `ValueOfInformationRepository.create`."""
        item = _assessment_to_item(assessment)
        self._gateway.put_item(item)
        return assessment

    def get(self, decision_id: str, quality_id: str) -> QualityAssessment | None:
        item = self._gateway.get_item(
            {"PK": _decision_pk(decision_id), "SK": _quality_sk(quality_id)}
        )
        return QualityAssessment.model_validate(_strip_keys(item)) if item else None

    def list_for_decision(self, decision_id: str) -> list[QualityAssessment]:
        """Every quality assessment ever computed for a decision, oldest
        first - a single, bounded `Query` on the decision's own
        partition, never a scan."""
        key_condition = Key("PK").eq(_decision_pk(decision_id)) & Key("SK").begins_with("QUALITY#")
        items, _ = self._gateway.query(key_condition=key_condition)
        assessments = [QualityAssessment.model_validate(_strip_keys(item)) for item in items]
        return sorted(assessments, key=lambda a: a.generated_at)

    def get_latest(self, decision_id: str) -> QualityAssessment | None:
        assessments = self.list_for_decision(decision_id)
        if not assessments:
            return None
        return max(assessments, key=lambda a: a.generated_at)


class CalibrationRepository:
    """Stores `CalibrationInsight` records, always scoped to one user's
    own partition - mirrors `CrossDecisionLearningRepository`'s own
    module docstring on why this is structurally, not just
    conventionally, user-isolated."""

    def __init__(self, gateway: DynamoDBGateway | None = None) -> None:
        self._gateway = gateway if gateway is not None else DynamoDBGateway()

    def upsert(self, insight: CalibrationInsight) -> CalibrationInsight:
        """Create or replace one user's calibration insight for one
        variable. Deterministic `calibration_id` (see
        `app.quality.calibration.deterministic_calibration_id`) means a
        later recompute always updates the SAME record."""
        item = _insight_to_item(insight)
        self._gateway.put_item(item)
        return insight

    def get(self, user_id: str, calibration_id: str) -> CalibrationInsight | None:
        item = self._gateway.get_item(
            {"PK": _user_pk(user_id), "SK": _calibration_sk(calibration_id)}
        )
        return CalibrationInsight.model_validate(_strip_keys(item)) if item else None

    def list_for_user(self, user_id: str) -> list[CalibrationInsight]:
        """Every calibration insight recorded for one user - a single,
        bounded `Query` on that user's own partition, `user_id` is
        REQUIRED so this can never return more than one user's data."""
        key_condition = Key("PK").eq(_user_pk(user_id)) & Key("SK").begins_with("CALIBRATION#")
        items, _ = self._gateway.query(key_condition=key_condition)
        insights = [CalibrationInsight.model_validate(_strip_keys(item)) for item in items]
        return sorted(insights, key=lambda i: i.observation_count, reverse=True)

    def get_for_variable(self, user_id: str, variable: str) -> CalibrationInsight | None:
        """Looks up by the deterministic id derived from the SAME
        normalization the aggregation itself uses - see
        `app.quality.calibration.deterministic_calibration_id`."""
        key = normalize_variable(variable)
        if key is None:
            return None
        return self.get(user_id, deterministic_calibration_id(user_id, key))


def _assessment_to_item(assessment: QualityAssessment) -> dict[str, Any]:
    dumped = assessment.model_dump(mode="json")
    return {
        "PK": _decision_pk(assessment.decision_id),
        "SK": _quality_sk(assessment.quality_id),
        "entity_type": "QUALITY_ASSESSMENT",
        **dumped,
    }


def _insight_to_item(insight: CalibrationInsight) -> dict[str, Any]:
    dumped = insight.model_dump(mode="json")
    return {
        "PK": _user_pk(insight.user_id),
        "SK": _calibration_sk(insight.calibration_id),
        "entity_type": "CALIBRATION_INSIGHT",
        **dumped,
    }


def _strip_keys(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in item.items()
        if key not in {"PK", "SK", "GSI1PK", "GSI1SK", "GSI2PK", "GSI2SK", "entity_type"}
    }
