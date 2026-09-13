"""Adaptive Decision Interview routes (REGRET ENGINE 2.0, Step 27).

Two route groups (spec section 25):

- Decision-scoped (`/decisions/{decision_id}/interview/start`) - confirms
  the decision exists and is owned by the caller before starting an
  interview, mirroring every other decision-scoped route in this
  codebase (e.g. `app.api.routes.analysis`).
- Interview-scoped (`/interviews/{interview_id}/...`) - ownership is
  checked inside `InterviewService` itself (every method verifies
  `state.user_id == user_id` before returning anything), since these
  routes never see a `decision_id` in their own URL.
"""

from uuid import UUID

from fastapi import APIRouter

from app.dependencies.decisions import CurrentUserIdDep, DecisionServiceDep
from app.dependencies.interview import InterviewServiceDep
from app.interview.schemas import (
    CompleteInterviewResponse,
    DecisionInterviewState,
    RespondRequest,
    RespondResponse,
    StartInterviewRequest,
    StartInterviewResponse,
)

router = APIRouter(tags=["interview"])


@router.post("/decisions/{decision_id}/interview/start", response_model=StartInterviewResponse)
async def start_interview(
    decision_id: UUID,
    payload: StartInterviewRequest,
    decision_service: DecisionServiceDep,
    interview_service: InterviewServiceDep,
    user_id: CurrentUserIdDep,
) -> StartInterviewResponse:
    """Starts (or resumes) the adaptive interview for a decision.

    Idempotent: revisiting this endpoint for a decision that already has
    an active interview returns that SAME interview rather than starting
    a second, concurrent one (spec section 27).
    """
    decision_service.get_decision(user_id, decision_id)  # existence + ownership, raises 404
    state, first_question = interview_service.start_interview(
        user_id, str(decision_id), payload.selected_categories
    )
    return StartInterviewResponse(
        interview_id=state.interview_id, first_question=first_question, state=state
    )


@router.post("/interviews/{interview_id}/respond", response_model=RespondResponse)
async def respond_to_interview(
    interview_id: str,
    payload: RespondRequest,
    interview_service: InterviewServiceDep,
    user_id: CurrentUserIdDep,
) -> RespondResponse:
    """Submits one answer and returns REGRET's next question (or a
    closing message once the interview is ready/stopped).

    Idempotent for a duplicate submission of the same in-flight turn -
    see `InterviewService.respond`'s own docstring.
    """
    return await interview_service.respond(
        interview_id, user_id, payload.message, payload.expected_turn_number
    )


@router.get("/interviews/{interview_id}", response_model=DecisionInterviewState)
async def get_interview(
    interview_id: str,
    interview_service: InterviewServiceDep,
    user_id: CurrentUserIdDep,
) -> DecisionInterviewState:
    """Fetch the current state of one interview."""
    return interview_service.get_state(interview_id, user_id)


@router.post("/interviews/{interview_id}/complete", response_model=CompleteInterviewResponse)
async def complete_interview(
    interview_id: str,
    interview_service: InterviewServiceDep,
    user_id: CurrentUserIdDep,
) -> CompleteInterviewResponse:
    """Finalizes the interview and applies its `DecisionSnapshot` to the
    decision's own fields, ready for the EXISTING
    `POST /decisions/{id}/analyze` pipeline - see
    `InterviewService.complete_interview`.
    """
    snapshot, readiness = interview_service.complete_interview(interview_id, user_id)
    return CompleteInterviewResponse(
        snapshot=snapshot, readiness=readiness, missing_information=snapshot.missing_information
    )


@router.post("/interviews/{interview_id}/skip", response_model=CompleteInterviewResponse)
async def skip_interview(
    interview_id: str,
    interview_service: InterviewServiceDep,
    user_id: CurrentUserIdDep,
) -> CompleteInterviewResponse:
    """Ends the interview EARLY at the user's own request (spec section
    14) - preserves everything collected so far and still hands off to
    the existing analysis pipeline via `InterviewService.skip_interview`.
    """
    snapshot, readiness = interview_service.skip_interview(interview_id, user_id)
    return CompleteInterviewResponse(
        snapshot=snapshot, readiness=readiness, missing_information=snapshot.missing_information
    )
