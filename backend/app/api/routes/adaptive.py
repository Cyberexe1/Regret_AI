"""Adaptive Experiment Loop routes (REGRET ENGINE 2.0, Step 21).

Mirrors `app.api.routes.value_of_information`'s pattern exactly: nested
under a decision, confirms existence and ownership via `DecisionServiceDep`
before ever touching the feature's own service, so a stranger's decision
id returns a plain 404 before any adaptive computation happens.

`GET` returns the most recently recorded state (or a clear 404 if the
loop has never been started yet). `POST .../advance` computes the next
logical state - idempotent: calling it twice with no new evidence never
creates a duplicate state, see `AdaptiveExperimentService.advance_cycle`'s
module docstring.
"""

from uuid import UUID

from fastapi import APIRouter, status

from app.adaptive.schemas import AdaptiveAdvanceResponse, AdaptiveExperimentState
from app.core.errors import NotFoundError
from app.dependencies.adaptive import AdaptiveExperimentServiceDep
from app.dependencies.decisions import CurrentUserIdDep, DecisionServiceDep

router = APIRouter(prefix="/decisions", tags=["adaptive"])


@router.get("/{decision_id}/adaptive", response_model=AdaptiveExperimentState)
async def get_adaptive_state(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    adaptive_service: AdaptiveExperimentServiceDep,
    user_id: CurrentUserIdDep,
) -> AdaptiveExperimentState:
    """Return the current adaptive-loop state for a decision: cycle
    number, validation state, primary uncertainty/threshold, current
    experiment (if any), next recommended action, and stopping reason
    (if concluded).

    Raises 404 if the adaptive loop has never been started for this
    decision - use `POST .../advance` to start it.
    """
    decision_service.get_decision(user_id, decision_id)  # existence + ownership, raises 404
    state = adaptive_service.get_latest(decision_id)
    if state is None:
        raise NotFoundError(
            detail=f"The adaptive experiment loop has not been started yet for decision "
            f"{decision_id}."
        )
    return state


@router.get("/{decision_id}/adaptive/history", response_model=list[AdaptiveExperimentState])
async def list_adaptive_history(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    adaptive_service: AdaptiveExperimentServiceDep,
    user_id: CurrentUserIdDep,
) -> list[AdaptiveExperimentState]:
    """List every adaptive-loop state ever recorded for a decision,
    oldest first - the full validation-journey history (Experiment 1 ->
    Result -> Learning -> Experiment 2 -> ...). Registered ahead of the
    single-state fetch above only conceptually; both are distinct fixed
    paths so there is no ambiguity with `{decision_id}`.
    """
    decision_service.get_decision(user_id, decision_id)
    return adaptive_service.list_history(decision_id)


@router.post(
    "/{decision_id}/adaptive/advance",
    response_model=AdaptiveAdvanceResponse,
    status_code=status.HTTP_200_OK,
)
async def advance_adaptive_cycle(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    adaptive_service: AdaptiveExperimentServiceDep,
    user_id: CurrentUserIdDep,
) -> AdaptiveAdvanceResponse:
    """Advance this decision to its next logical adaptive-loop state.

    Idempotent: if the same state would result (no new evidence since
    the last call), this returns the EXISTING state with
    `outcome=no_change` rather than creating a duplicate - see
    `AdaptiveExperimentService.advance_cycle`'s module docstring. Always
    `200 OK` (never `201 Created`) since a call that produces no new
    state is not creating a resource.
    """
    decision = decision_service.get_decision(user_id, decision_id)  # existence + ownership
    return adaptive_service.advance_cycle(decision, user_id)


@router.post("/{decision_id}/adaptive/stop", response_model=AdaptiveExperimentState)
async def stop_adaptive_loop(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    adaptive_service: AdaptiveExperimentServiceDep,
    user_id: CurrentUserIdDep,
) -> AdaptiveExperimentState:
    """The user manually stops the adaptive loop for this decision - the
    human remains in control; REGRET ENGINE never decides on its own
    that testing is "done" in a way the user cannot override, and never
    executes anything automatically as a result of stopping.
    """
    decision_service.get_decision(user_id, decision_id)
    state = adaptive_service.stop(decision_id)
    if state is None:
        raise NotFoundError(
            detail=f"The adaptive experiment loop has not been started yet for decision "
            f"{decision_id}."
        )
    return state
