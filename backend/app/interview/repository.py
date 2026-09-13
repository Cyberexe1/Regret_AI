"""DynamoDB-backed Adaptive Decision Interview storage (REGRET ENGINE
2.0, Step 27).

Uses the EXISTING single-table design (see `app.repositories.dynamodb`)
- no new database. Key layout (spec section 26):

    DecisionInterviewState:  PK=DECISION#<decision_id>   SK=INTERVIEW#<interview_id>
    InterviewTurn:           PK=INTERVIEW#<interview_id>  SK=TURN#<turn_number>

The interview STATE lives in the same decision partition as every other
per-decision entity (mirrors `ValueOfInformationRepository`/
`QualityRepository` exactly), so "get everything about this decision"
stays a single `Query` on `PK=DECISION#<id>`. Turns live under their own
`INTERVIEW#<id>` partition (not nested under the decision partition)
specifically so `TURN#<turn_number>` sorts numerically as a clean range
query independent of however many other entity types a decision
accumulates - this is the same "child records get their own natural
partition when they have a strong 1:many relationship to a NON-decision
parent" pattern `CrossDecisionLearningRepository` uses for
`PatternOccurrence` under `PATTERN#<id>`.
"""

from typing import Any

from boto3.dynamodb.conditions import Key

from app.interview.schemas import DecisionInterviewState, InterviewTurn
from app.repositories.dynamodb import DynamoDBGateway


def _decision_pk(decision_id: str) -> str:
    return f"DECISION#{decision_id}"


def _interview_sk(interview_id: str) -> str:
    return f"INTERVIEW#{interview_id}"


def _interview_pk(interview_id: str) -> str:
    return f"INTERVIEW#{interview_id}"


def _turn_sk(turn_number: int) -> str:
    # Zero-padded so lexicographic SK sort order matches numeric turn
    # order even past 9 turns (max_turns defaults well under 100, but
    # this removes any ambiguity for a future higher cap).
    return f"TURN#{turn_number:04d}"


class InterviewRepository:
    """Stores `DecisionInterviewState`/`InterviewTurn` records. Contains
    no interview logic itself - that lives entirely in
    `app.interview.service`/`app.interview.state`/
    `app.interview.question_selector`. This class only knows how to
    read and write already-computed state against the existing table.
    """

    def __init__(self, gateway: DynamoDBGateway | None = None) -> None:
        self._gateway = gateway if gateway is not None else DynamoDBGateway()

    # --- interview state -------------------------------------------------------

    def save_state(self, state: DecisionInterviewState) -> DecisionInterviewState:
        """Create or fully replace the interview's state record.
        `interview_id` is stable for the lifetime of one interview (see
        `InterviewService.start_interview`'s idempotent-lookup-by-decision
        behavior - spec section 27), so this always updates the SAME
        item rather than creating a duplicate."""
        item = _state_to_item(state)
        self._gateway.put_item(item)
        return state

    def get_state(self, decision_id: str, interview_id: str) -> DecisionInterviewState | None:
        item = self._gateway.get_item(
            {"PK": _decision_pk(decision_id), "SK": _interview_sk(interview_id)}
        )
        return DecisionInterviewState.model_validate(_strip_keys(item)) if item else None

    def get_state_by_interview_id(self, interview_id: str) -> DecisionInterviewState | None:
        """Looks up an interview's state without already knowing its
        decision id - used by the `interview_id`-only routes (spec
        section 25's `POST /interviews/{id}/respond|complete|skip` and
        `GET /interviews/{id}`, none of which have `decision_id` in
        their URL at all).

        Backed by a small, explicit lookup record
        (`PK=INTERVIEW#<id> SK=LOOKUP`) written once at interview
        creation (see `save_lookup`) purely to make this a single,
        targeted `get_item` rather than a table scan - this table has
        no secondary index for "find a decision by an arbitrary child
        entity's id" today.
        """
        item = self._gateway.get_item({"PK": _interview_pk(interview_id), "SK": _LOOKUP_SK})
        if item is None:
            return None
        decision_id = item.get("decision_id")
        if not decision_id:
            return None
        return self.get_state(decision_id, interview_id)

    def get_active_interview_for_decision(self, decision_id: str) -> DecisionInterviewState | None:
        """The most recent NON-terminal interview for a decision, if
        any - the idempotency guard behind spec section 27 ("starting an
        interview should not accidentally create multiple active
        interviews for the same decision"). A single, bounded `Query` on
        the decision's own partition, never a scan.
        """
        key_condition = Key("PK").eq(_decision_pk(decision_id)) & Key("SK").begins_with(
            "INTERVIEW#"
        )
        items, _ = self._gateway.query(key_condition=key_condition)
        states = [DecisionInterviewState.model_validate(_strip_keys(item)) for item in items]
        active = [
            s
            for s in states
            if s.status
            in {
                "not_started",
                "active",
                "awaiting_answer",
                "ready",
            }
        ]
        if not active:
            return None
        return max(active, key=lambda s: s.updated_at)

    def list_interviews_for_decision(self, decision_id: str) -> list[DecisionInterviewState]:
        key_condition = Key("PK").eq(_decision_pk(decision_id)) & Key("SK").begins_with(
            "INTERVIEW#"
        )
        items, _ = self._gateway.query(key_condition=key_condition)
        states = [DecisionInterviewState.model_validate(_strip_keys(item)) for item in items]
        return sorted(states, key=lambda s: s.created_at)

    def save_lookup(self, interview_id: str, decision_id: str) -> None:
        """Persists the small `interview_id -> decision_id` lookup record
        that makes `get_state_by_interview_id` a targeted `get_item`
        rather than a scan - written once, at interview creation, right
        alongside the state record itself."""
        self._gateway.put_item(
            {
                "PK": _interview_pk(interview_id),
                "SK": _LOOKUP_SK,
                "entity_type": "INTERVIEW_LOOKUP",
                "interview_id": interview_id,
                "decision_id": decision_id,
            }
        )

    # --- turns -------------------------------------------------------------------

    def save_turn(self, turn: InterviewTurn) -> InterviewTurn:
        """Create or replace one turn. `turn_number` is deterministic per
        interview, so re-submitting a response for the SAME turn number
        (e.g. a client retry) upserts the same row instead of creating a
        duplicate - the idempotency behavior spec section 27 requires
        for "responding to the same turn/request.\" """
        item = _turn_to_item(turn)
        self._gateway.put_item(item)
        return turn

    def get_turn(self, interview_id: str, turn_number: int) -> InterviewTurn | None:
        item = self._gateway.get_item(
            {"PK": _interview_pk(interview_id), "SK": _turn_sk(turn_number)}
        )
        return InterviewTurn.model_validate(_strip_keys(item)) if item else None

    def list_turns(self, interview_id: str) -> list[InterviewTurn]:
        """Every turn for one interview, in order - a single, bounded
        `Query` on the interview's own partition, never a scan."""
        key_condition = Key("PK").eq(_interview_pk(interview_id)) & Key("SK").begins_with("TURN#")
        items, _ = self._gateway.query(key_condition=key_condition)
        turns = [InterviewTurn.model_validate(_strip_keys(item)) for item in items]
        return sorted(turns, key=lambda t: t.turn_number)


_LOOKUP_SK = "LOOKUP"


def _state_to_item(state: DecisionInterviewState) -> dict[str, Any]:
    dumped = state.model_dump(mode="json")
    return {
        "PK": _decision_pk(state.decision_id),
        "SK": _interview_sk(state.interview_id),
        "entity_type": "INTERVIEW_STATE",
        **dumped,
    }


def _turn_to_item(turn: InterviewTurn) -> dict[str, Any]:
    dumped = turn.model_dump(mode="json")
    return {
        "PK": _interview_pk(turn.interview_id),
        "SK": _turn_sk(turn.turn_number),
        "entity_type": "INTERVIEW_TURN",
        **dumped,
    }


def _strip_keys(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in item.items()
        if key not in {"PK", "SK", "GSI1PK", "GSI1SK", "GSI2PK", "GSI2SK", "entity_type"}
    }
