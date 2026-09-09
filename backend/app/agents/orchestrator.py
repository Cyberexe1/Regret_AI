"""Analysis orchestration.

`AnalysisOrchestrator` is the only thing that calls into an agent. Routes
never call an agent directly, and no agent ever touches a repository - the
flow is always:

    API -> Orchestrator -> Agent -> structured result -> Repository -> DynamoDB

This step's workflow is intentionally linear and synchronous (no task
queue): load decision -> load evidence -> create AnalysisRun -> run the
Decision Analyzer -> validate its output -> persist it -> update the run's
status -> return. Only one agent exists so far; the orchestrator's shape is
ready for more agents to be added as additional steps in the same
workflow later.
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError as PydanticValidationError

from app.agents.context import AnalysisContext
from app.agents.decision_analyzer import run_decision_analyzer
from app.agents.schemas import DecisionAnalysis
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.decision_repository import DecisionRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.schemas.decision_resources import AnalysisRun, AnalysisRunStatus

logger = get_logger(__name__)

# Bound on how much of the underlying model/provider error is logged.
# Never included in what's returned to the API caller.
_MAX_LOGGED_ERROR_CHARS = 500


class AnalysisOrchestrator:
    """Coordinates one analysis run for a decision."""

    def __init__(
        self,
        decision_repository: DecisionRepository,
        evidence_repository: EvidenceRepository,
        analysis_repository: AnalysisRepository,
    ) -> None:
        self._decisions = decision_repository
        self._evidence = evidence_repository
        self._analyses = analysis_repository

    async def run_analysis(self, user_id: str, decision_id: UUID) -> AnalysisRun:
        """Run the Decision Analyzer for a decision and persist the result.

        Raises `NotFoundError` if the decision doesn't exist or isn't owned
        by `user_id` - this happens before any AnalysisRun is created, so a
        stranger's decision id never creates orphaned run records.

        On agent/model failure, the created AnalysisRun is marked `failed`
        with a safe, generic error message (never the raw provider error)
        and returned rather than raised - the caller can inspect
        `run.status` instead of having to catch an exception to learn the
        outcome.
        """
        decision_record = self._decisions.get_raw(decision_id)
        if decision_record is None or decision_record.get("user_id") != user_id:
            raise NotFoundError(detail=f"Decision {decision_id} not found.")
        decision = DecisionRepository.to_response(decision_record)

        evidence = self._evidence.list_for_decision(decision_id)

        run = self._analyses.create(decision_id)
        context = AnalysisContext(decision=decision, evidence=evidence)

        run = self._analyses.update_status(
            decision_id=decision_id,
            run_id=run.id,
            status=AnalysisRunStatus.RUNNING,
            started_at=datetime.now(UTC),
        )

        try:
            analysis = await run_decision_analyzer(context.decision, context.evidence)
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any agent/model failure lands here
            logger.error(
                "Decision analyzer failed decision_id=%s run_id=%s error=%s",
                decision_id,
                run.id,
                str(exc)[:_MAX_LOGGED_ERROR_CHARS],
            )
            return self._analyses.update_status(
                decision_id=decision_id,
                run_id=run.id,
                status=AnalysisRunStatus.FAILED,
                completed_at=datetime.now(UTC),
                error_message="The decision analysis could not be completed. Please try again.",
            )

        validated = self._validate_analysis(analysis)
        if validated is None:
            logger.error(
                "Decision analyzer returned invalid structured output decision_id=%s run_id=%s",
                decision_id,
                run.id,
            )
            return self._analyses.update_status(
                decision_id=decision_id,
                run_id=run.id,
                status=AnalysisRunStatus.FAILED,
                completed_at=datetime.now(UTC),
                error_message="The decision analysis produced an invalid result. Please try again.",
            )

        context.agent_results["decision_analyzer"] = validated

        return self._analyses.update_status(
            decision_id=decision_id,
            run_id=run.id,
            status=AnalysisRunStatus.COMPLETED,
            completed_at=datetime.now(UTC),
            result=validated.model_dump(mode="json"),
        )

    @staticmethod
    def _validate_analysis(analysis: DecisionAnalysis) -> DecisionAnalysis | None:
        """Re-validate the agent's output against the schema.

        The Strands SDK already validates structured output against the
        Pydantic model before returning it, but this re-validation is kept
        as an explicit, independent check - if the SDK's guarantee ever
        changes, this is where malformed data gets caught rather than
        silently persisted.
        """
        try:
            return DecisionAnalysis.model_validate(analysis.model_dump())
        except PydanticValidationError:
            return None
