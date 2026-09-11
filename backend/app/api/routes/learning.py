"""Cross-Decision Learning routes (REGRET ENGINE 2.0, Step 23).

Every route here is scoped to `CurrentUserIdDep` - there is no path or
query parameter anywhere in this file that could be used to request
another user's patterns; the user id always comes from the same
placeholder identity resolver every other route already uses (see
`app.dependencies.auth.get_current_user_id`), never from client input.

Reads never trigger detection - `refresh_patterns` (via `POST
/learning/patterns/refresh`) is the only operation that recomputes
patterns, per the service's own module docstring.
"""

from uuid import UUID

from fastapi import APIRouter, Query

from app.core.errors import NotFoundError
from app.dependencies.decisions import CurrentUserIdDep, DecisionServiceDep
from app.dependencies.learning import CrossDecisionLearningServiceDep
from app.learning.schemas import (
    CrossDecisionPatternDetail,
    CrossDecisionPatternListResponse,
    PatternRefreshResponse,
)

router = APIRouter(tags=["learning"])


@router.get("/learning/patterns", response_model=CrossDecisionPatternListResponse)
async def list_learning_patterns(
    learning_service: CrossDecisionLearningServiceDep,
    user_id: CurrentUserIdDep,
    pattern_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    variable: str | None = Query(default=None),
) -> CrossDecisionPatternListResponse:
    """Every cross-decision pattern currently recorded for the caller's
    own decision history - never another user's. Returns whatever the
    last `POST /learning/patterns/refresh` computed; this endpoint never
    triggers detection itself.
    """
    patterns = learning_service.list_patterns_for_user(
        user_id, pattern_type=pattern_type, status=status, domain=domain, variable=variable
    )
    return CrossDecisionPatternListResponse(patterns=patterns)


@router.get("/learning/patterns/{pattern_id}", response_model=CrossDecisionPatternDetail)
async def get_learning_pattern(
    pattern_id: str,
    learning_service: CrossDecisionLearningServiceDep,
    user_id: CurrentUserIdDep,
) -> CrossDecisionPatternDetail:
    """Full detail for one pattern: the pattern itself, every real
    occurrence backing it, and the supporting/contradicting split - the
    "show me why" surface (spec section 17). `404` if the pattern
    doesn't exist for THIS user - a real pattern id belonging to another
    user is indistinguishable from a nonexistent one, by construction
    (see `app.learning.repository`'s partition-key user-scoping).
    """
    detail = learning_service.get_pattern_detail(user_id, pattern_id)
    if detail is None:
        raise NotFoundError(detail=f"Pattern {pattern_id} not found.")
    return detail


@router.post("/learning/patterns/refresh", response_model=PatternRefreshResponse)
async def refresh_learning_patterns(
    learning_service: CrossDecisionLearningServiceDep,
    user_id: CurrentUserIdDep,
) -> PatternRefreshResponse:
    """Rebuilds the caller's own cross-decision patterns from their
    current canonical records. Idempotent - re-running with no new
    evidence reports `patterns_unchanged` rather than creating
    duplicates. Always scoped to the caller's own `user_id`; there is no
    parameter that could target a different user's patterns.
    """
    return learning_service.refresh_patterns(user_id)


@router.get("/decisions/{decision_id}/patterns", response_model=CrossDecisionPatternListResponse)
async def get_patterns_for_decision(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    learning_service: CrossDecisionLearningServiceDep,
    user_id: CurrentUserIdDep,
) -> CrossDecisionPatternListResponse:
    """Patterns relevant to one specific decision - i.e. patterns that
    name this decision as supporting or contradicting evidence. Confirms
    existence and ownership of the decision itself first (raises a plain
    404 for a stranger's decision id, mirroring every other decision-
    scoped route in this codebase) before ever touching the learning
    service.
    """
    decision_service.get_decision(user_id, decision_id)
    patterns = learning_service.get_patterns_for_decision(user_id, decision_id)
    return CrossDecisionPatternListResponse(patterns=patterns)
