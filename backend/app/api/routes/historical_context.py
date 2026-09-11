"""Historical Context routes (REGRET ENGINE 2.0: Decision Similarity &
Historical Insight Engine).

One route, mirroring the pattern established by `app.api.routes.memory`:
nested under a decision (`/decisions/{decision_id}/historical-context`),
confirming the decision exists and is owned by the caller via
`DecisionServiceDep` before ever calling `HistoricalContextService` - the
same ownership check every other decision-scoped route in this codebase
uses, so a stranger's decision id returns a plain 404 before any
historical lookup ever happens.

Read-only: nothing here creates or mutates anything. This computes the
same historical context the analysis pipeline gathers as an additive
pre-Stage-1 step (see `AnalysisOrchestrator._gather_historical_context`),
exposed as its own endpoint so a caller can inspect it independently of
running a full analysis - e.g. for the "Relevant from your past
decisions" section on the new-decision intake page, or for re-fetching a
completed decision's own historical context later without re-running the
whole pipeline.
"""

from uuid import UUID

from fastapi import APIRouter

from app.dependencies.decisions import CurrentUserIdDep, DecisionServiceDep
from app.dependencies.historical_context import HistoricalContextServiceDep
from app.memory.similarity_schemas import HistoricalContext
from app.schemas.decision import DecisionCreate

router = APIRouter(prefix="/decisions", tags=["historical-context"])


@router.post("/historical-context/preview", response_model=HistoricalContext)
async def preview_historical_context(
    draft: DecisionCreate,
    historical_context_service: HistoricalContextServiceDep,
    user_id: CurrentUserIdDep,
) -> HistoricalContext:
    """Return the Decision Similarity + Historical Insight context for a
    decision that has NOT been created yet.

    Powers the "Relevant from your past decisions" section on the
    new-decision intake page (REGRET ENGINE 2.0 Step 19), where the user
    is still typing and no `decision_id` exists yet. Nothing here is
    persisted - `draft` is used only in memory, for this one comparison,
    against the caller's own real past decisions (see
    `HistoricalContextService.get_historical_context_preview`). Searches
    ONLY the caller's own history - never another user's.

    """
    return historical_context_service.get_historical_context_preview(user_id, draft)


@router.get("/{decision_id}/historical-context", response_model=HistoricalContext)
async def get_decision_historical_context(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    historical_context_service: HistoricalContextServiceDep,
    user_id: CurrentUserIdDep,
) -> HistoricalContext:
    """Return the Decision Similarity + Historical Insight context for a decision.

    Searches ONLY the caller's own past decisions (see
    `app.memory.historical_context`'s module docstring for the ownership
    guarantee) - never another user's. Returns a valid `found=False`
    result (never a 404 or an error) when the user has no sufficiently
    similar past decisions yet; a 404 is raised only if `decision_id`
    itself doesn't exist or isn't owned by the caller.
    """
    # existence + ownership, raises 404
    decision = decision_service.get_decision(user_id, decision_id)
    return historical_context_service.get_historical_context(user_id, decision)
