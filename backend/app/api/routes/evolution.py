"""Decision Evolution & Causal Timeline routes (REGRET ENGINE 2.0, Step 22).

Mirrors `app.api.routes.adaptive`'s pattern: nested under a decision,
confirms existence and ownership via `DecisionServiceDep` before ever
touching the feature's own service, so a stranger's decision id returns a
plain 404 before any evolution assembly happens.

A single bounded call (`GET .../evolution`) returns the complete,
already-ordered timeline plus the current state and major changes - no
per-event API calls are needed to render the full "Decision Evolution"
section (spec section 22's performance requirement).
"""

from uuid import UUID

from fastapi import APIRouter

from app.dependencies.decisions import CurrentUserIdDep, DecisionServiceDep
from app.dependencies.evolution import DecisionEvolutionServiceDep
from app.evolution.schemas import DecisionDelta, DecisionEvolution, DecisionEvolutionEvent

router = APIRouter(prefix="/decisions", tags=["evolution"])


@router.get("/{decision_id}/evolution", response_model=DecisionEvolution)
async def get_decision_evolution(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    evolution_service: DecisionEvolutionServiceDep,
    user_id: CurrentUserIdDep,
) -> DecisionEvolution:
    """The complete, bounded evolution timeline for a decision: current
    state, every derivable event (oldest first, bounded by
    `EVOLUTION_MAX_EVENTS`), and a compact "major changes" list.

    Never 404s once the decision itself exists - a brand-new decision
    with no analysis yet simply gets a timeline containing only its own
    `decision_created` event, exactly mirroring how `DecisionMemory`
    already tolerates "nothing happened yet" as a normal state rather
    than an error.
    """
    decision_service.get_decision(user_id, decision_id)  # existence + ownership, raises 404
    return evolution_service.get_evolution(decision_id)


@router.get("/{decision_id}/evolution/{event_id}", response_model=DecisionEvolutionEvent)
async def get_decision_evolution_event(
    decision_id: UUID,
    event_id: str,
    decision_service: DecisionServiceDep,
    evolution_service: DecisionEvolutionServiceDep,
    user_id: CurrentUserIdDep,
) -> DecisionEvolutionEvent:
    """Detailed information for one specific timeline event - used by the
    frontend's event-detail panel when a user clicks a timeline entry.
    """
    decision_service.get_decision(user_id, decision_id)
    return evolution_service.get_event(decision_id, event_id)


@router.get(
    "/{decision_id}/evolution/{event_id}/delta",
    response_model=DecisionDelta,
)
async def get_decision_evolution_delta(
    decision_id: UUID,
    event_id: str,
    decision_service: DecisionServiceDep,
    evolution_service: DecisionEvolutionServiceDep,
    user_id: CurrentUserIdDep,
) -> DecisionDelta:
    """The structured "what changed?" delta for one specific event -
    powers the `DecisionDeltaCard` component: before/after, what was
    affected, and a plain-language explanation built only from real,
    comparable fields.
    """
    decision_service.get_decision(user_id, decision_id)
    return evolution_service.get_decision_delta(decision_id, event_id)
