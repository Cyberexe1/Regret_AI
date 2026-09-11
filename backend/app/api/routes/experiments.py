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
from app.core.logging import get_logger
from app.dependencies.adaptive import AdaptiveExperimentServiceDep
from app.dependencies.decisions import CurrentUserIdDep, DecisionServiceDep
from app.dependencies.experiments import ExperimentServiceDep, ReEvaluationServiceDep
from app.dependencies.memory import MemoryServiceDep
from app.dependencies.quality import QualityServiceDep
from app.dependencies.value_of_information import ValueOfInformationServiceDep
from app.schemas.decision_resources import AnalysisRunStatus, Experiment
from app.schemas.decision_resources import ExperimentResult as StoredExperimentResult
from app.schemas.experiment_result import ExperimentResultCreate, ExperimentResultResponse
from app.services.decisions import DecisionService

logger = get_logger(__name__)

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
    memory_service: MemoryServiceDep,
    voi_service: ValueOfInformationServiceDep,
    adaptive_service: AdaptiveExperimentServiceDep,
    quality_service: QualityServiceDep,
    decision_service: DecisionServiceDep,
    user_id: CurrentUserIdDep,
) -> ExperimentResultResponse:
    """Submit the observed outcome of running an experiment.

    Marks the experiment `completed`, persists the result, and immediately
    triggers deterministic re-evaluation of the target threshold and any
    assumptions/regret scenarios it relates to - see `ReEvaluationService`.
    The response summarizes the outcome; the full `ExperimentResult`/
    `ReEvaluation` records remain retrievable via their own GET endpoints.

    REGRET ENGINE 2.0: also updates this decision's Decision Memory -
    `MemoryService.update_memory_from_reevaluation` reads the
    already-computed `result`/`reevaluation` below and records durable
    `MemoryLearning`s from them. This never re-runs the analysis pipeline
    and never calls an LLM; a failure here is logged and does not fail
    the request, since the result/re-evaluation have already been
    successfully persisted and returning them to the caller must not be
    blocked by a memory-layer problem.

    REGRET ENGINE 2.0 (Step 20): also recomputes this decision's
    Value-of-Information analysis, since the just-persisted re-evaluation
    may have changed an assumption's evidence status or a threshold's
    validation - the uncertainty that was previously highest-priority may
    now be resolved, and a different one may become primary. The
    previous VOI analysis is marked superseded, never deleted (see
    `app.agents.value_of_information`'s versioning docstring). A failure
    here is likewise logged and never fails the request.

    REGRET ENGINE 2.0 (Step 21): also marks this decision's adaptive
    loop `ready_for_next_experiment` if the loop was tracking this
    exact experiment - see `AdaptiveExperimentService
    .mark_experiment_completed`. This endpoint deliberately does NOT
    select or create the next experiment itself; the separate, explicit
    `POST /decisions/{id}/adaptive/advance` endpoint does that. A
    failure here is likewise logged and never fails the request.
    """
    experiment = experiment_service.get_experiment(experiment_id)
    _ensure_owns_parent_decision(decision_service, user_id, experiment)

    result, reevaluation = re_evaluation_service.submit_result(
        experiment.decision_id, experiment_id, payload
    )

    try:
        memory_service.update_memory_from_reevaluation(
            experiment.decision_id, experiment_id, result, reevaluation
        )
    except Exception:  # noqa: BLE001 - memory is a secondary concern; never fail the submission
        logger.exception(
            "Memory update failed decision_id=%s experiment_id=%s result_id=%s",
            experiment.decision_id,
            experiment_id,
            result.id,
        )

    try:
        decision = decision_service.get_decision(user_id, experiment.decision_id)
        voi_service.compute_and_persist(decision, user_id=user_id)
    except Exception:  # noqa: BLE001 - VOI recompute is additive; never fail the submission
        logger.exception(
            "Value-of-Information recompute failed decision_id=%s experiment_id=%s result_id=%s",
            experiment.decision_id,
            experiment_id,
            result.id,
        )

    try:
        # REGRET ENGINE 2.0 (Step 21): mark this cycle ready for the next
        # experiment to be SELECTED - deliberately does NOT select or
        # create the next experiment itself here (see spec section 13's
        # preferred safer approach). A no-op if the adaptive loop was
        # never started for this decision, or if this experiment wasn't
        # the one the loop was currently tracking.
        adaptive_service.mark_experiment_completed(experiment.decision_id, experiment_id, result.id)
    except Exception:  # noqa: BLE001 - adaptive bookkeeping is additive; never fail the submission
        logger.exception(
            "Adaptive state update failed decision_id=%s experiment_id=%s result_id=%s",
            experiment.decision_id,
            experiment_id,
            result.id,
        )

    try:
        # REGRET ENGINE 2.0 (Step 24): re-runs the deterministic quality
        # checks now that a new result/re-evaluation exists - e.g. a
        # threshold that was merely "moderate" quality before may now be
        # "strong" (a real comparison exists), or a new inconsistency may
        # have appeared. Never blocks the submission itself.
        quality_service.run_quality_check(experiment.decision_id, user_id)
    except Exception:  # noqa: BLE001 - quality check is additive; never fail the submission
        logger.exception(
            "Quality check failed decision_id=%s experiment_id=%s result_id=%s",
            experiment.decision_id,
            experiment_id,
            result.id,
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
