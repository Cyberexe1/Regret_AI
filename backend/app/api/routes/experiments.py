"""Experiment routes.

Three route groups, all thin, mirroring `app.api.routes.evidence`:

- Nested under a decision (`/decisions/{decision_id}/experiments`,
  `/decisions/{decision_id}/experiment-results`) for listing - confirms
  the decision exists and is owned by the caller via `DecisionServiceDep`,
  reusing the same ownership-check logic the decision routes already use.
- Top-level (`/experiments/{experiment_id}`,
  `/experiments/{experiment_id}/results`) for a single experiment (and
  its results) once its id is known, independent of its parent decision.

Experiments themselves are only ever created by the Experiment Planner via
`AnalysisOrchestrator` (triggered by `POST /decisions/{decision_id}/analyze`)
- there is no direct creation endpoint here. Submitting a *result* for an
experiment (`POST /experiments/{experiment_id}/results`) is the entry
point into the re-evaluation loop - see `ReEvaluationService`.
"""

from uuid import UUID

from fastapi import APIRouter, status

from app.core.errors import NotFoundError
from app.dependencies.decisions import CurrentUserIdDep, DecisionServiceDep
from app.dependencies.experiments import ExperimentServiceDep, ReEvaluationServiceDep
from app.schemas.decision_resources import AnalysisRunStatus, Experiment
from app.schemas.decision_resources import ExperimentResult as StoredExperimentResult
from app.schemas.experiment_result import ExperimentResultCreate, ExperimentResultResponse
from app.services.decisions import DecisionService

decision_experiments_router = APIRouter(prefix="/decisions", tags=["experiments"])
experiments_router = APIRouter(prefix="/experiments", tags=["experiments"])


@decision_experiments_router.get("/{decision_id}/experiments", response_model=list[Experiment])
async def list_experiments(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    experiment_service: ExperimentServiceDep,
    user_id: CurrentUserIdDep,
) -> list[Experiment]:
    """List the experiments recommended for a decision.

    Returns whatever the Experiment Planner produced on the most recent
    successful analysis run - empty if no analysis has completed that
    stage yet.
    """
    decision_service.get_decision(user_id, decision_id)  # existence + ownership, raises 404
    return experiment_service.list_experiments(decision_id)


@decision_experiments_router.get(
    "/{decision_id}/experiment-results", response_model=list[StoredExperimentResult]
)
async def list_experiment_results_for_decision(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    experiment_service: ExperimentServiceDep,
    user_id: CurrentUserIdDep,
) -> list[StoredExperimentResult]:
    """List every experiment result submitted for a decision, across all its experiments."""
    decision_service.get_decision(user_id, decision_id)
    return experiment_service.list_results_for_decision(decision_id)


@experiments_router.get("/{experiment_id}", response_model=Experiment)
async def get_experiment(
    experiment_id: UUID,
    experiment_service: ExperimentServiceDep,
    decision_service: DecisionServiceDep,
    user_id: CurrentUserIdDep,
) -> Experiment:
    """Fetch a single experiment by id.

    Ownership is enforced via the experiment's parent decision - a missing
    experiment id and one belonging to a decision the caller doesn't own
    both surface as the same 404.
    """
    experiment = experiment_service.get_experiment(experiment_id)
    _ensure_owns_parent_decision(decision_service, user_id, experiment)
    return experiment


@experiments_router.post(
    "/{experiment_id}/results",
    response_model=ExperimentResultResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_experiment_result(
    experiment_id: UUID,
    payload: ExperimentResultCreate,
    experiment_service: ExperimentServiceDep,
    re_evaluation_service: ReEvaluationServiceDep,
    decision_service: DecisionServiceDep,
    user_id: CurrentUserIdDep,
) -> ExperimentResultResponse:
    """Submit the observed outcome of running an experiment.

    Marks the experiment `completed`, persists the result, and immediately
    triggers deterministic re-evaluation of the target threshold and any
    assumptions/regret scenarios it relates to - see `ReEvaluationService`.
    The response summarizes the outcome; the full `ExperimentResult`/
    `ReEvaluation` records remain retrievable via their own GET endpoints.
    """
    experiment = experiment_service.get_experiment(experiment_id)
    _ensure_owns_parent_decision(decision_service, user_id, experiment)

    result, reevaluation = re_evaluation_service.submit_result(
        experiment.decision_id, experiment_id, payload
    )
    return ExperimentResultResponse(
        experiment_id=experiment_id,
        result_id=result.id,
        reevaluation_id=reevaluation.id,
        status=AnalysisRunStatus.COMPLETED,
        decision_assessment=reevaluation.decision_assessment.status,
        key_learning=reevaluation.key_learning,
        next_step=reevaluation.recommended_next_step,
    )


@experiments_router.get("/{experiment_id}/results", response_model=list[StoredExperimentResult])
async def list_experiment_results(
    experiment_id: UUID,
    experiment_service: ExperimentServiceDep,
    decision_service: DecisionServiceDep,
    user_id: CurrentUserIdDep,
) -> list[StoredExperimentResult]:
    """List every result submitted for a single experiment."""
    experiment = experiment_service.get_experiment(experiment_id)
    _ensure_owns_parent_decision(decision_service, user_id, experiment)
    return experiment_service.list_results_for_experiment(experiment.decision_id, experiment_id)


def _ensure_owns_parent_decision(
    decision_service: DecisionService, user_id: str, experiment: Experiment
) -> None:
    try:
        decision_service.get_decision(user_id, experiment.decision_id)
    except NotFoundError as exc:
        # Re-raised as experiment-not-found rather than decision-not-found,
        # since the caller asked about the experiment id, not the decision.
        raise NotFoundError(detail=f"Experiment {experiment.id} not found.") from exc
