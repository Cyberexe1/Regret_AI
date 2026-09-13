"""Adaptive Decision Interview orchestration (REGRET ENGINE 2.0, Step
27).

`InterviewService` is the one place that:
  - calls the Strands Interview Agent (`app.interview.prompts.run_interview_turn`),
  - chooses the next question topic deterministically (`question_selector.py`),
  - merges extracted fields into state (`state.py`),
  - decides readiness/stopping (`state.py`/`question_selector.py`),
  - and, on completion/skip, maps the resulting `DecisionSnapshot` onto
    the EXISTING `DecisionUpdate` contract and calls the EXISTING
    `DecisionService.update_decision` - the existing analysis pipeline
    (`AnalysisOrchestrator.run_analysis`) needs ZERO changes, since it
    already reads a decision's own persisted fields directly (see
    `app.agents.orchestrator.run_analysis`).

Mirrors `AnalysisOrchestrator`'s own contract: on any agent/model
failure, this service never raises the raw provider error - it falls
back to a deterministic canned question (spec section 29) and keeps the
interview alive, or (if even that can't produce a next step) marks the
interview `blocked` while preserving every answer already collected
(spec section 28's "do not lose collected information").
"""

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import ValidationError as PydanticValidationError

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.interview import question_selector
from app.interview import state as state_helpers
from app.interview.prompts import run_interview_turn
from app.interview.question_selector import FALLBACK_QUESTIONS, suggested_chips_for_topic
from app.interview.repository import InterviewRepository
from app.interview.schemas import (
    DecisionInterviewState,
    DecisionSnapshot,
    ExtractedFields,
    InterviewStatus,
    InterviewTurn,
    QuestionType,
    ReadinessLevel,
    RespondResponse,
    TurnRole,
)
from app.repositories.decision_repository import DecisionRepository
from app.schemas.decision import DecisionUpdate

logger = get_logger(__name__)

# Bound on how much of the underlying model/provider error is logged -
# mirrors `AnalysisOrchestrator._MAX_LOGGED_ERROR_CHARS` exactly. Never
# included in what's returned to the API caller.
_MAX_LOGGED_ERROR_CHARS = 500


class InterviewNotFoundError(NotFoundError):
    detail = "Interview not found."


class InterviewService:
    def __init__(
        self,
        interview_repository: InterviewRepository,
        decision_repository: DecisionRepository,
    ) -> None:
        self._interviews = interview_repository
        self._decisions = decision_repository

    # --- start -------------------------------------------------------------------

    def start_interview(
        self, user_id: str, decision_id: str, selected_categories: list[str]
    ) -> tuple[DecisionInterviewState, str]:
        """Starts (or resumes) the interview for a decision.

        Idempotent (spec section 27): if this decision already has an
        active interview, that one is returned instead of creating a
        second, concurrent interview - revisiting the intake flow never
        spawns a duplicate conversation.
        """
        decision_record = self._decisions.get_raw(decision_id)
        if decision_record is None or decision_record.get("user_id") != user_id:
            raise NotFoundError(detail=f"Decision {decision_id} not found.")
        decision = DecisionRepository.to_response(decision_record)

        existing = self._interviews.get_active_interview_for_decision(decision_id)
        if existing is not None:
            logger.info(
                "Reusing active interview decision_id=%s interview_id=%s",
                decision_id,
                existing.interview_id,
            )
            return existing, existing.current_question or self._first_question_text(existing)

        now = datetime.now(UTC)
        interview_id = str(uuid4())
        first_topic = question_selector.select_next_topic(
            DecisionInterviewState(
                interview_id=interview_id,
                decision_id=str(decision_id),
                user_id=user_id,
                decision_text=decision.description[:600],
                selected_categories=selected_categories,
                created_at=now,
                updated_at=now,
            )
        )
        first_topic = first_topic or QuestionType.GOAL
        first_question = FALLBACK_QUESTIONS[first_topic]

        state = DecisionInterviewState(
            interview_id=interview_id,
            decision_id=str(decision_id),
            user_id=user_id,
            status=InterviewStatus.AWAITING_ANSWER,
            max_turns=get_settings().interview_max_turns,
            decision_text=decision.description[:600],
            selected_categories=selected_categories,
            current_question=first_question,
            questions_asked=[first_topic],
            created_at=now,
            updated_at=now,
        )
        self._interviews.save_lookup(interview_id, str(decision_id))
        self._interviews.save_state(state)
        logger.info("Interview started decision_id=%s interview_id=%s", decision_id, interview_id)
        return state, first_question

    def _first_question_text(self, state: DecisionInterviewState) -> str:
        topic = state.questions_asked[-1] if state.questions_asked else QuestionType.GOAL
        return FALLBACK_QUESTIONS.get(topic, FALLBACK_QUESTIONS[QuestionType.GOAL])

    # --- respond -----------------------------------------------------------------

    async def respond(
        self,
        interview_id: str,
        user_id: str,
        message: str,
        expected_turn_number: int | None = None,
    ) -> RespondResponse:
        """Processes one user answer: extracts structured fields, merges
        them into state, and selects + phrases the next question (or
        closes the interview if ready/at the turn ceiling).

        Idempotent for a duplicate submission of the SAME turn (spec
        section 27), two ways:
          - If the interview is not currently `awaiting_answer`/`active`
            at all (already ready/completed/stopped/blocked), the
            CURRENT state is returned unchanged.
          - If the caller passes `expected_turn_number` (the turn number
            it last saw) and the interview has ALREADY advanced past
            that turn since, this is a stale duplicate/retry (e.g. a
            dropped response that the client is re-sending) - the
            CURRENT state is returned unchanged rather than processing
            the message as an answer to a question the caller was never
            actually shown.
        """
        state = self._get_owned_state(interview_id, user_id)

        is_stale_retry = (
            expected_turn_number is not None and state.turn_number != expected_turn_number
        )
        if is_stale_retry:
            logger.info(
                "Ignoring stale respond() interview_id=%s expected_turn=%s actual_turn=%d",
                interview_id,
                expected_turn_number,
                state.turn_number,
            )
            return RespondResponse(
                response=state.current_question or state.readiness_reason,
                extracted_fields=ExtractedFields(),
                current_state=state,
                next_question=state.current_question,
                readiness=state.readiness,
                turn_number=state.turn_number,
                suggested_chips=[],
            )

        if state.status not in (InterviewStatus.AWAITING_ANSWER, InterviewStatus.ACTIVE):
            # Already completed/stopped/blocked/ready - or a duplicate
            # request for a turn that already advanced. Return the
            # current state as-is rather than reprocessing.
            logger.info(
                "Ignoring duplicate/late respond() interview_id=%s status=%s",
                interview_id,
                state.status.value,
            )
            return RespondResponse(
                response=state.current_question or "",
                extracted_fields=ExtractedFields(),
                current_state=state,
                next_question=state.current_question,
                readiness=state.readiness,
                turn_number=state.turn_number,
                suggested_chips=[],
            )

        pending_topic = state.questions_asked[-1] if state.questions_asked else QuestionType.GOAL

        turn_number = state.turn_number + 1
        user_turn = InterviewTurn(
            turn_id=str(uuid4()),
            interview_id=interview_id,
            turn_number=turn_number,
            role=TurnRole.USER,
            message=message[:2000],
            question_type=pending_topic,
            created_at=datetime.now(UTC),
        )

        (
            extracted,
            agent_selected_topic,
            agent_next_question,
            agent_failed,
        ) = await self._extract_and_phrase(state, pending_topic, message)
        user_turn.extracted_fields = extracted
        self._interviews.save_turn(user_turn)

        state = state_helpers.merge_extracted_fields(state, extracted)
        state.turn_number = turn_number
        state.answers = [*state.answers, message[:2000]][:50]

        readiness, readiness_reason = state_helpers.compute_readiness(state)
        state.readiness = readiness
        state.readiness_reason = readiness_reason

        next_topic = None
        if not question_selector.should_stop(state):
            # Prefer the deterministic selector's own next topic; only
            # fall back to whatever the agent chose if it's still a
            # valid, not-yet-covered topic AND the selector had nothing
            # left (keeps topic choice authoritative in the selector,
            # per this module's own design principle).
            next_topic = question_selector.select_next_topic(state)

        if next_topic is None or readiness == ReadinessLevel.READY:
            # Stopping now, either because the deterministic selector has
            # nothing left to ask (every priority topic covered, or the
            # turn ceiling was reached - see `should_stop`) or because
            # readiness itself has already reached its strongest band.
            # `BLOCKED` (spec section 2's own status) is reserved for the
            # one genuinely unhappy case: the turn ceiling was hit while
            # readiness never even reached `ENOUGH` - everything collected
            # so far is still preserved and still handed to the existing
            # analysis pipeline (spec section 14's "if the user stops
            # early... continue into REGRET analysis").
            hit_ceiling_while_still_early = (
                state.turn_number >= state.max_turns and readiness == ReadinessLevel.EARLY
            )
            state.status = (
                InterviewStatus.BLOCKED if hit_ceiling_while_still_early else InterviewStatus.READY
            )
            state.current_question = None
            closing_message = readiness_reason
            regret_turn = InterviewTurn(
                turn_id=str(uuid4()),
                interview_id=interview_id,
                turn_number=turn_number,
                role=TurnRole.REGRET,
                message=closing_message,
                created_at=datetime.now(UTC),
            )
            self._interviews.save_turn(regret_turn)
            state.updated_at = datetime.now(UTC)
            self._interviews.save_state(state)
            return RespondResponse(
                response=closing_message,
                extracted_fields=extracted,
                current_state=state,
                next_question=None,
                readiness=readiness,
                turn_number=turn_number,
                suggested_chips=[],
                agent_available=not agent_failed,
            )

        question_text = (
            agent_next_question
            if (not agent_failed and agent_selected_topic == next_topic and agent_next_question)
            else FALLBACK_QUESTIONS[next_topic]
        )

        state.status = InterviewStatus.AWAITING_ANSWER
        state.current_question = question_text
        state.questions_asked = [*state.questions_asked, next_topic]
        state.updated_at = datetime.now(UTC)

        regret_turn = InterviewTurn(
            turn_id=str(uuid4()),
            interview_id=interview_id,
            turn_number=turn_number,
            role=TurnRole.REGRET,
            message=question_text,
            question_type=next_topic,
            created_at=datetime.now(UTC),
        )
        self._interviews.save_turn(regret_turn)
        self._interviews.save_state(state)

        return RespondResponse(
            response=question_text,
            extracted_fields=extracted,
            current_state=state,
            next_question=question_text,
            readiness=readiness,
            turn_number=turn_number,
            suggested_chips=suggested_chips_for_topic(next_topic),
            agent_available=not agent_failed,
        )

    async def _extract_and_phrase(
        self,
        state: DecisionInterviewState,
        pending_topic: QuestionType,
        message: str,
    ) -> tuple[ExtractedFields, QuestionType | None, str | None, bool]:
        """Calls the Strands Interview Agent, returning
        `(extracted_fields, selected_topic, next_question, failed)`.
        NEVER raises - any model/validation failure is caught here and
        reported back as `failed=True` with an empty extraction, so the
        caller can fall back to a deterministic question and the
        interview is never lost (spec sections 28/29).
        """
        try:
            output = await run_interview_turn(state, pending_topic, message)
            return output.extracted, output.selected_topic, output.next_question, False
        except TimeoutError:
            logger.warning(
                "Interview agent timed out interview_id=%s turn=%d",
                state.interview_id,
                state.turn_number + 1,
            )
            return ExtractedFields(), None, None, True
        except (ValueError, PydanticValidationError) as exc:
            logger.warning(
                "Interview agent returned invalid output interview_id=%s: %s",
                state.interview_id,
                str(exc)[:_MAX_LOGGED_ERROR_CHARS],
            )
            return ExtractedFields(), None, None, True
        except Exception as exc:  # noqa: BLE001 - never let a raw provider error escape
            logger.error(
                "Interview agent call failed interview_id=%s: %s",
                state.interview_id,
                str(exc)[:_MAX_LOGGED_ERROR_CHARS],
            )
            return ExtractedFields(), None, None, True

    # --- get / complete / skip ----------------------------------------------------

    def get_state(self, interview_id: str, user_id: str) -> DecisionInterviewState:
        return self._get_owned_state(interview_id, user_id)

    def complete_interview(
        self, interview_id: str, user_id: str
    ) -> tuple[DecisionSnapshot, ReadinessLevel]:
        """Finalizes a `ready`/`active` interview: builds the
        `DecisionSnapshot`, persists it as `completed`, and updates the
        EXISTING decision's own fields via `DecisionService`-equivalent
        logic so the existing `/analyze` pipeline picks up the richer
        context automatically - no orchestrator change required.
        """
        state = self._get_owned_state(interview_id, user_id)
        snapshot = self._build_snapshot(state)
        readiness = state.readiness
        state.status = InterviewStatus.COMPLETED
        state.updated_at = datetime.now(UTC)
        self._interviews.save_state(state)

        self._apply_snapshot_to_decision(state.user_id, state.decision_id, snapshot)
        logger.info(
            "Interview completed interview_id=%s decision_id=%s", interview_id, state.decision_id
        )
        return snapshot, readiness

    def skip_interview(
        self, interview_id: str, user_id: str
    ) -> tuple[DecisionSnapshot, ReadinessLevel]:
        """Completes the interview EARLY at the user's own request (spec
        section 14) - preserves everything collected so far, marks it
        `user_stopped`, and still hands off to the existing analysis
        pipeline via the same snapshot-application path as a full
        completion.
        """
        state = self._get_owned_state(interview_id, user_id)
        snapshot = self._build_snapshot(state)
        readiness = state.readiness
        state.status = InterviewStatus.USER_STOPPED
        state.current_question = None
        state.updated_at = datetime.now(UTC)
        self._interviews.save_state(state)

        self._apply_snapshot_to_decision(state.user_id, state.decision_id, snapshot)
        logger.info(
            "Interview skipped interview_id=%s decision_id=%s", interview_id, state.decision_id
        )
        return snapshot, readiness

    def _build_snapshot(self, state: DecisionInterviewState) -> DecisionSnapshot:
        missing = state_helpers.missing_information(state)
        summary_parts = [
            f"Interview covered {len(state.questions_asked)} topic(s) over "
            f"{state.turn_number} turn(s)."
        ]
        if missing:
            summary_parts.append(f"Not covered: {', '.join(missing)}.")
        return DecisionSnapshot(
            decision=state.decision_text,
            goal=state.desired_outcome,
            constraints=list(state.constraints),
            commitments=list(state.commitments),
            beliefs=list(state.beliefs) + list(state.discovered_assumptions),
            uncertainties=list(state.uncertainties) + list(state.discovered_unknowns),
            alternatives=list(state.alternatives),
            evidence=list(state.evidence_summary),
            important_variables=list(state.important_variables),
            stakeholders=list(state.stakeholders),
            decision_criteria=[],
            missing_information=missing,
            interview_summary=" ".join(summary_parts),
        )

    def _apply_snapshot_to_decision(
        self, user_id: str, decision_id: str, snapshot: DecisionSnapshot
    ) -> None:
        """Maps `DecisionSnapshot` onto the EXISTING `DecisionUpdate`
        contract (spec section 35: "map InterviewSnapshot -> existing
        Decision schema, maintain backward compatibility") and applies
        it via the repository directly (mirrors
        `DecisionService.update_decision`'s own ownership-then-update
        sequence, without introducing a circular import on
        `DecisionService` itself).

        Fields with no dedicated backend column (constraints/beliefs/
        uncertainties/alternatives/commitments/evidence) are folded into
        `beliefs`/`description`-adjacent text exactly like
        `frontend/src/lib/decisionPayload.ts` already does for the
        intake form - this interview is simply a different FRONT END to
        the same backend contract, never a parallel one.
        """
        from uuid import UUID as _UUID

        record = self._decisions.get_raw(_UUID(decision_id))
        if record is None or record.get("user_id") != user_id:
            raise NotFoundError(detail=f"Decision {decision_id} not found.")

        beliefs_text = _compose_beliefs_text(snapshot)
        payload = DecisionUpdate(
            desired_outcome=snapshot.goal or None,
            beliefs=beliefs_text or None,
        )
        self._decisions.update(_UUID(decision_id), payload)

    # --- internal ------------------------------------------------------------------

    def _get_owned_state(self, interview_id: str, user_id: str) -> DecisionInterviewState:
        state = self._interviews.get_state_by_interview_id(interview_id)
        if state is None or state.user_id != user_id:
            raise InterviewNotFoundError(detail=f"Interview {interview_id} not found.")
        return state


def _compose_beliefs_text(snapshot: DecisionSnapshot) -> str:
    parts: list[str] = []
    if snapshot.beliefs:
        parts.append("Beliefs: " + "; ".join(snapshot.beliefs))
    if snapshot.constraints:
        parts.append("Constraints: " + "; ".join(snapshot.constraints))
    if snapshot.uncertainties:
        parts.append("Uncertainties: " + "; ".join(snapshot.uncertainties))
    if snapshot.alternatives:
        parts.append("Alternatives: " + "; ".join(snapshot.alternatives))
    if snapshot.commitments:
        parts.append("At stake: " + "; ".join(snapshot.commitments))
    if snapshot.evidence:
        parts.append("Evidence mentioned: " + "; ".join(snapshot.evidence))
    return "\n".join(parts)[:5000]
