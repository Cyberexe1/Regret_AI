"""Decision routes.

Thin by design: request/response validation happens via Pydantic models,
authentication resolves through `CurrentUserIdDep` (a placeholder until real
auth exists), and everything else is delegated to `DecisionService`.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.dependencies.decisions import CurrentUserIdDep, DecisionServiceDep
from app.schemas.decision import (
    DecisionCreate,
    DecisionListResponse,
    DecisionResponse,
    DecisionUpdate,
)

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.post("", response_model=DecisionResponse, status_code=status.HTTP_201_CREATED)
async def create_decision(
    payload: DecisionCreate,
    service: DecisionServiceDep,
    user_id: CurrentUserIdDep,
) -> DecisionResponse:
    """Submit a new decision for future analysis.

    No AI processing happens yet - this only persists the decision to
    DynamoDB as a ``draft``.
    """
    return service.create_decision(user_id, payload)


@router.get("", response_model=DecisionListResponse)
async def list_decisions(
    service: DecisionServiceDep,
    user_id: CurrentUserIdDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(description="Opaque pagination cursor.")] = None,
) -> DecisionListResponse:
    """List the current user's decisions, newest first.

    Pagination follows DynamoDB's cursor pattern rather than offsets: pass
    the `next_cursor` from a response back as `cursor` to fetch the next
    page. A response with no `next_cursor` means there is no more data.
    """
    return service.list_decisions(user_id, limit=limit, cursor=cursor)


@router.get("/{decision_id}", response_model=DecisionResponse)
async def get_decision(
    decision_id: UUID,
    service: DecisionServiceDep,
    user_id: CurrentUserIdDep,
) -> DecisionResponse:
    """Fetch a single decision by id.

    Related resources (assumptions, evidence, etc.) are not included here
    and are not yet exposed via their own endpoints - fetching a decision
    never implicitly pulls in everything attached to it.
    """
    return service.get_decision(user_id, decision_id)


@router.patch("/{decision_id}", response_model=DecisionResponse)
async def update_decision(
    decision_id: UUID,
    payload: DecisionUpdate,
    service: DecisionServiceDep,
    user_id: CurrentUserIdDep,
) -> DecisionResponse:
    """Partially update a decision.

    Set `expected_updated_at` in the payload to guard against overwriting a
    change made by another request since you last read this decision.
    """
    return service.update_decision(user_id, decision_id, payload)


@router.delete("/{decision_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_decision(
    decision_id: UUID,
    service: DecisionServiceDep,
    user_id: CurrentUserIdDep,
) -> None:
    """Delete a decision."""
    service.delete_decision(user_id, decision_id)
