"""Decision Memory routes.

Two route groups, mirroring the pattern already established by
`app.api.routes.decision_analysis_resources`/`app.api.routes.experiments`:

- Nested under a decision (`/decisions/{decision_id}/memory`,
  `/decisions/{decision_id}/learnings`) - both confirm the decision exists
  and is owned by the caller via `DecisionServiceDep`, reusing the same
  ownership-check logic every other decision-scoped route uses.
- Top-level (`/memory/{memory_id}`) for fetching a single memory record
  once its id is known, independent of its parent decision - mirrors
  `GET /experiments/{experiment_id}`.

Nothing here creates or mutates memory directly - memory is a consequence
of submitting an experiment result (see
`POST /experiments/{experiment_id}/results` in
`app.api.routes.experiments`, which now also calls `MemoryService` after
re-evaluation completes). These routes are read-only.
"""

from uuid import UUID

from fastapi import APIRouter

from app.core.errors import NotFoundError
from app.dependencies.decisions import CurrentUserIdDep, DecisionServiceDep
from app.dependencies.memory import MemoryServiceDep
from app.memory.memory_schemas import DecisionMemoryResponse, MemoryLearning

decision_memory_router = APIRouter(prefix="/decisions", tags=["memory"])
memory_router = APIRouter(prefix="/memory", tags=["memory"])


@decision_memory_router.get("/{decision_id}/memory", response_model=DecisionMemoryResponse)
async def get_decision_memory(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    memory_service: MemoryServiceDep,
    user_id: CurrentUserIdDep,
) -> DecisionMemoryResponse:
    """Return everything REGRET ENGINE remembers about this decision:
    its memory summary, the learnings extracted from it, the real
    experiments and re-evaluations (assessments) it references, and its
    current unresolved uncertainties.

    Never raises 404 for a decision with no memory yet - only for an
    unknown/not-owned decision id. A decision that has been analyzed but
    never had an experiment result submitted legitimately has an empty
    (but valid) memory context.
    """
    decision_service.get_decision(user_id, decision_id)  # existence + ownership, raises 404
    return memory_service.get_memory_context(decision_id)


@decision_memory_router.get(
    "/{decision_id}/learnings", response_model=list[MemoryLearning]
)
async def list_decision_learnings(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    memory_service: MemoryServiceDep,
    user_id: CurrentUserIdDep,
) -> list[MemoryLearning]:
    """List every learning ever recorded for a decision, oldest first.

    Empty until at least one experiment result has been submitted and
    re-evaluated for this decision.
    """
    decision_service.get_decision(user_id, decision_id)
    return memory_service.list_learnings(decision_id)


@memory_router.get("/{memory_id}", response_model=DecisionMemoryResponse)
async def get_memory_by_id(
    memory_id: UUID,
    memory_service: MemoryServiceDep,
) -> DecisionMemoryResponse:
    """Fetch a single memory object by its own id, independent of its
    parent decision. Raises 404 if no memory with this id exists.

    Deliberately does not perform an ownership check here (unlike the
    decision-scoped routes above) - matching this project's existing
    placeholder-auth posture (see `app.dependencies.auth`): every
    resource is currently attributed to the single default user, so
    there is no other user's data to protect against yet. This mirrors
    `GET /experiments/{experiment_id}`, which has the same property.
    """
    memory = memory_service.get_memory_by_id(memory_id)
    if memory is None:
        raise NotFoundError(detail=f"Memory {memory_id} not found.")

    return memory_service.get_memory_context(memory.decision_id)
