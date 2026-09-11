"""Value-of-Information routes (REGRET ENGINE 2.0, Step 20).

Mirrors `app.api.routes.memory`/`app.api.routes.historical_context`'s
pattern exactly: nested under a decision, confirms existence and
ownership via `DecisionServiceDep` before ever touching the feature's own
service, so a stranger's decision id returns a plain 404 before any VOI
computation happens.

`GET` returns the most recently computed analysis (or a clear 404 if none
exists yet - a decision that hasn't reached the Threshold Engine stage
yet legitimately has nothing to report). `POST .../recompute` computes a
fresh one on demand, e.g. after an experiment result changes the
evidence - see `app.agents.value_of_information` module docstring's
versioning section. This mirrors `POST /decisions/{id}/analyze`'s own
"the route can be re-triggered without deleting prior state" convention.
"""

from uuid import UUID

from fastapi import APIRouter, status

from app.agents.value_of_information_schemas import ValueOfInformationAnalysis
from app.core.errors import NotFoundError
from app.dependencies.decisions import CurrentUserIdDep, DecisionServiceDep
from app.dependencies.value_of_information import ValueOfInformationServiceDep

router = APIRouter(prefix="/decisions", tags=["value-of-information"])


@router.get(
    "/{decision_id}/value-of-information",
    response_model=ValueOfInformationAnalysis,
)
async def get_value_of_information(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    voi_service: ValueOfInformationServiceDep,
    user_id: CurrentUserIdDep,
) -> ValueOfInformationAnalysis:
    """Return the most recently computed Value-of-Information analysis
    for a decision: which uncertainty is most worth resolving before
    committing, ranked alongside the rest, with a documented rationale
    for each.

    Raises 404 if no analysis has been computed yet for this decision
    (e.g. the analysis pipeline hasn't reached the Threshold Engine
    stage) - use `POST .../recompute` to compute one on demand.
    """
    decision_service.get_decision(user_id, decision_id)  # existence + ownership, raises 404
    analysis = voi_service.get_latest(decision_id)
    if analysis is None:
        raise NotFoundError(
            detail=f"No Value-of-Information analysis has been computed yet for decision "
            f"{decision_id}."
        )
    return analysis


@router.post(
    "/{decision_id}/value-of-information/recompute",
    response_model=ValueOfInformationAnalysis,
    status_code=status.HTTP_201_CREATED,
)
async def recompute_value_of_information(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    voi_service: ValueOfInformationServiceDep,
    user_id: CurrentUserIdDep,
) -> ValueOfInformationAnalysis:
    """Recompute the Value-of-Information analysis from this decision's
    current assumptions/blindspots/thresholds/regret scenarios/
    experiments - e.g. after an experiment result changed the evidence
    (see `POST /experiments/{id}/results`).

    Always creates a NEW analysis record; the previous one (if any) is
    marked superseded but never deleted, so the decision's full
    prioritization history remains reconstructable - see
    `app.agents.value_of_information`'s versioning docstring.
    """
    decision = decision_service.get_decision(user_id, decision_id)  # existence + ownership
    return voi_service.compute_and_persist(decision, user_id=user_id)
