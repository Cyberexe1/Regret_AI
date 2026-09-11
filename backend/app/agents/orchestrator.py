"""Analysis orchestration.

`AnalysisOrchestrator` is the only thing that calls into an agent. Routes
never call an agent directly, and no agent ever touches a repository - the
flow is always:

    API -> Orchestrator -> Agent(s) -> structured result -> Repository -> DynamoDB

This step's workflow is intentionally linear and synchronous (no task
queue):

    1. Load decision
    2. Load evidence
    3. Create AnalysisRun
    4. Run Decision Analyzer
    5. Validate Decision Analyzer output
    6. Persist Decision Analysis (as part of the run's combined result)
    7. Run Assumption Hunter (consuming the Decision Analyzer's output)
    8. Validate Assumption Hunter output
    9. Persist assumptions
    10. Run Blindspot Hunter (consuming Decision Analyzer + persisted assumptions)
    11. Validate Blindspot Hunter output
    12. Persist blindspots
    12a. Run Research Agent (OPTIONAL - consuming Decision Analyzer +
         persisted assumptions/blindspots + evidence; only runs if a
         research provider is configured; a provider failure marks this
         stage `unavailable`, never `failed`, and never blocks the rest of
         the pipeline)
    12b. Persist external evidence, if any was found
    13. Run Evidence Agent (consuming Decision Analyzer + persisted
        assumptions/blindspots + evidence + external evidence)
    14. Validate Evidence Agent output
    15. Persist evidence findings
    16. Run Devil's Advocate (consuming Decision Analyzer + persisted
        assumptions/blindspots/evidence findings)
    17. Validate Devil's Advocate output
    18. Persist challenges
    19. Run Regret Simulator (consuming Decision Analyzer + persisted
        assumptions/blindspots/evidence findings/challenges)
    20. Validate Regret Simulator output
    21. Persist regret scenarios
    22. Run Threshold Engine (consuming Decision Analyzer + persisted
        assumptions/blindspots/evidence findings/challenges/regret scenarios)
    23. Validate Threshold Engine output (including independently
        recomputing any calculated threshold's arithmetic)
    24. Persist thresholds
    25. Run Experiment Planner (consuming Decision Analyzer + persisted
        assumptions/blindspots/evidence findings/challenges/regret
        scenarios/thresholds)
    26. Validate Experiment Planner output
    27. Persist experiments
    28. Update AnalysisRun with the final status and combined result, and
        move the decision to `needs_validation` if a recommended
        experiment exists

Each stage only runs if every stage before it succeeded. If a stage fails
or produces invalid output, every stage after it is skipped - there is
nothing valid for a downstream agent to consume yet - and the run is
persisted as `failed` with whatever earlier stages *did* complete still
intact in `result`/`agent_statuses`. Nothing downstream is ever silently
marked successful because an upstream stage failed.
"""

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError as PydanticValidationError

from app.agents.assumption_hunter import run_assumption_hunter
from app.agents.blindspot_hunter import run_blindspot_hunter
from app.agents.context import AnalysisContext
from app.agents.decision_analyzer import run_decision_analyzer
from app.agents.devils_advocate import run_devils_advocate
from app.agents.evidence_agent import run_evidence_agent
from app.agents.experiment_planner import run_experiment_planner
from app.agents.regret_simulator import run_regret_simulator
from app.agents.research_agent import run_research_agent
from app.agents.schemas import (
    AssumptionAnalysis,
    BlindspotAnalysis,
    DecisionAnalysis,
    DevilAdvocateAnalysis,
    EvidenceAnalysis,
    ExperimentPlan,
    RegretSimulation,
    ResearchAnalysis,
    ThresholdAnalysis,
)
from app.agents.threshold_engine import run_threshold_engine
from app.agents.value_of_information import ValueOfInformationService
from app.agents.value_of_information_schemas import ValueOfInformationAnalysis
from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.learning.repository import CrossDecisionLearningRepository
from app.learning.service import CrossDecisionLearningService
from app.memory.historical_context import HistoricalContextService
from app.memory.memory_repository import MemoryRepository
from app.memory.similarity_schemas import HistoricalContext
from app.quality.repository import QualityRepository
from app.quality.service import QualityService
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.decision_repository import DecisionRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.value_of_information_repository import ValueOfInformationRepository
from app.research.service import ResearchService, ResearchUnavailable
from app.schemas.decision import DecisionResponse, DecisionStatus, DecisionUpdate
from app.schemas.decision_resources import AgentRunStatus, AnalysisRun, AnalysisRunStatus, Evidence

logger = get_logger(__name__)

# Bound on how much of the underlying model/provider error is logged.
# Never included in what's returned to the API caller.
_MAX_LOGGED_ERROR_CHARS = 500

# Process-wide cap on how many analysis pipelines can run concurrently -
# each one makes up to ~10 sequential Bedrock calls, so an unbounded
# number of simultaneous `/analyze` calls (for *different* decisions - the
# same decision is already deduplicated via `get_active_run`) could
# exhaust Bedrock capacity or this process's own connection pool. Created
# lazily (not at import time) so `Settings.max_concurrent_analyses` is
# read from the environment that's actually active when the first
# analysis runs, matching every other lazily-cached provider in this
# codebase (`get_bedrock_model`, `get_dynamodb_resource`).
_analysis_semaphore: asyncio.Semaphore | None = None


def _get_analysis_semaphore() -> asyncio.Semaphore:
    global _analysis_semaphore
    if _analysis_semaphore is None:
        _analysis_semaphore = asyncio.Semaphore(get_settings().max_concurrent_analyses)
    return _analysis_semaphore


_HISTORICAL_CONTEXT = "historical_context"
_VALUE_OF_INFORMATION = "value_of_information"
_DECISION_ANALYZER = "decision_analyzer"
_ASSUMPTION_HUNTER = "assumption_hunter"
_BLINDSPOT_HUNTER = "blindspot_hunter"
_RESEARCH_AGENT = "research_agent"
_EVIDENCE_AGENT = "evidence_agent"
_DEVILS_ADVOCATE = "devils_advocate"
_REGRET_SIMULATOR = "regret_simulator"
_THRESHOLD_ENGINE = "threshold_engine"
_EXPERIMENT_PLANNER = "experiment_planner"

# Generic, safe error messages returned to the API caller - never the raw
# provider/model error, which might contain request ids or other internal
# detail. Keyed by stage so each failure path uses consistent wording.
_SAFE_MODEL_FAILURE_MESSAGE = "The decision analysis could not be completed. Please try again."
_SAFE_INVALID_OUTPUT_MESSAGE = "The decision analysis produced an invalid result. Please try again."


class AnalysisOrchestrator:
    """Coordinates one analysis run for a decision."""

    def __init__(
        self,
        decision_repository: DecisionRepository,
        evidence_repository: EvidenceRepository,
        analysis_repository: AnalysisRepository,
        research_service: ResearchService | None = None,
        historical_context_service: HistoricalContextService | None = None,
        value_of_information_service: ValueOfInformationService | None = None,
    ) -> None:
        self._decisions = decision_repository
        self._evidence = evidence_repository
        self._analyses = analysis_repository
        # Defaults to a fresh `ResearchService`, which reads
        # `Settings.research_provider` and is a no-op (`enabled=False`)
        # unless a provider has actually been configured - research is
        # opt-in, never on by default. Injectable for tests.
        self._research = research_service if research_service is not None else ResearchService()
        # REGRET ENGINE 2.0: gathers Decision Similarity + Historical
        # Insight context from the SAME user's own past decisions - see
        # `app.memory.historical_context`'s module docstring for the
        # user-scoping guarantee. Defaults to a fresh service built from
        # this orchestrator's own `decision_repository` (never a different
        # repository instance), so historical retrieval always shares the
        # exact same DynamoDB access this orchestrator already uses.
        self._historical_context = (
            historical_context_service
            if historical_context_service is not None
            else HistoricalContextService(decision_repository, MemoryRepository())
        )
        # REGRET ENGINE 2.0, Step 20: ranks which uncertainty is most
        # worth resolving before commitment - purely deterministic, no
        # LLM call (see app.services.value_of_information_service).
        # Defaults to a fresh service sharing this orchestrator's own
        # decision_repository, exactly like `_historical_context` above.
        # REGRET ENGINE 2.0, Step 23: enriches VOI's ranked items with a
        # read-only cross-decision-pattern signal - never re-scores or
        # reorders anything VOI already decided (see
        # `ValueOfInformationService._apply_cross_decision_signals`).
        self._cross_decision_learning = CrossDecisionLearningService(
            decision_repository, MemoryRepository(), CrossDecisionLearningRepository()
        )
        # REGRET ENGINE 2.0, Step 24: deterministic quality checking, run
        # additively as the pipeline's final stage - never blocks or
        # changes this run's own completion status (see
        # `_run_quality_check`/Stage 9 below).
        self._quality = QualityService(
            decision_repository,
            EvidenceRepository(),
            analysis_repository,
            MemoryRepository(),
            CrossDecisionLearningRepository(),
            QualityRepository(),
        )
        self._value_of_information = (
            value_of_information_service
            if value_of_information_service is not None
            else ValueOfInformationService(
                decision_repository,
                ValueOfInformationRepository(),
                self._historical_context,
                self._cross_decision_learning,
            )
        )

    async def run_analysis(self, user_id: str, decision_id: UUID) -> AnalysisRun:
        """Run the full analysis pipeline (Decision Analyzer -> Assumption
        Hunter -> Blindspot Hunter -> Evidence Agent -> Devil's Advocate ->
        Regret Simulator -> Threshold Engine -> Experiment Planner) for a
        decision and persist the results.

        Raises `NotFoundError` if the decision doesn't exist or isn't owned
        by `user_id` - this happens before any AnalysisRun is created, so a
        stranger's decision id never creates orphaned run records.

        Idempotent: if this decision already has an active run
        (`queued`/`running`), that existing run is returned immediately
        instead of starting a second, concurrent, expensive pipeline - see
        `AnalysisRepository.get_active_run`. A run stuck `running` past
        `analysis_max_duration_seconds` + `analysis_lock_grace_seconds`
        (e.g. the process crashed mid-run, so it was never transitioned to
        a terminal status) is treated as abandoned rather than active, so
        a decision can never be wedged permanently unable to re-analyze.

        On any agent/model failure, the created AnalysisRun is marked
        `failed` with a safe, generic error message (never the raw provider
        error) and returned rather than raised - the caller can inspect
        `run.status` instead of having to catch an exception to learn the
        outcome. Every stage after the failing one is marked `skipped`, and
        every stage's successful result that was persisted before the
        failure remains intact.
        """
        decision_record = self._decisions.get_raw(decision_id)
        if decision_record is None or decision_record.get("user_id") != user_id:
            raise NotFoundError(detail=f"Decision {decision_id} not found.")
        decision = DecisionRepository.to_response(decision_record)

        active_run = self._analyses.get_active_run(decision_id)
        if active_run is not None and not self._is_abandoned(active_run):
            logger.info(
                "Reusing active analysis run decision_id=%s run_id=%s status=%s",
                decision_id,
                active_run.id,
                active_run.status,
            )
            return active_run

        evidence = self._evidence.list_for_decision(decision_id)

        # Bounds how many pipelines run concurrently across all decisions
        # in this process - see `_get_analysis_semaphore`'s docstring. This
        # can make the request wait if the process is already at capacity,
        # rather than starting an unbounded number of simultaneous Bedrock
        # call chains.
        async with _get_analysis_semaphore():
            return await self._run_analysis_pipeline(user_id, decision, evidence)

    async def _run_analysis_pipeline(
        self, user_id: str, decision: DecisionResponse, evidence: list[Evidence]
    ) -> AnalysisRun:
        """The actual pipeline body, run while holding a concurrency slot -
        split out from `run_analysis` purely so the semaphore-acquisition
        wrapper above stays easy to read."""
        decision_id = decision.id
        run = self._analyses.create(decision_id)
        context = AnalysisContext(decision=decision, evidence=evidence)

        # --- Stage 0: Historical Context (REGRET ENGINE 2.0, additive) -----
        # Gathered BEFORE Stage 1 so the Decision Analyzer can reference it
        # as clearly-labeled context - see `AnalysisContext.historical_context`'s
        # docstring and `app.memory.historical_context`'s module docstring
        # for the user-scoping guarantee and evidence-hierarchy rationale.
        # A failure here is logged and NEVER fails the run, and NEVER
        # blocks/skips any other stage - it only means this run proceeds
        # with `historical_context=None` (rendered as "no historical
        # context available" in the prompt), exactly like the optional
        # Research Agent stage's own failure handling.
        context.historical_context = self._gather_historical_context(user_id, decision)

        agent_statuses: dict[str, AgentRunStatus] = {
            _DECISION_ANALYZER: AgentRunStatus.PENDING,
            _ASSUMPTION_HUNTER: AgentRunStatus.PENDING,
            _BLINDSPOT_HUNTER: AgentRunStatus.PENDING,
            _RESEARCH_AGENT: AgentRunStatus.PENDING,
            _EVIDENCE_AGENT: AgentRunStatus.PENDING,
            _DEVILS_ADVOCATE: AgentRunStatus.PENDING,
            _REGRET_SIMULATOR: AgentRunStatus.PENDING,
            _THRESHOLD_ENGINE: AgentRunStatus.PENDING,
            _EXPERIMENT_PLANNER: AgentRunStatus.PENDING,
        }
        result: dict[str, object] = {}

        run = self._analyses.update_status(
            decision_id=decision_id,
            run_id=run.id,
            status=AnalysisRunStatus.RUNNING,
            started_at=datetime.now(UTC),
            agent_statuses=agent_statuses,
        )

        # --- Stage 1: Decision Analyzer --------------------------------------
        agent_statuses[_DECISION_ANALYZER] = AgentRunStatus.RUNNING
        decision_analysis = await self._run_decision_analyzer_step(
            decision_id, run.id, context, agent_statuses
        )
        if decision_analysis is None:
            # Nothing downstream ever runs: there is nothing valid yet for
            # any of them to consume. The failure has already been persisted.
            self._skip_remaining(
                agent_statuses,
                _ASSUMPTION_HUNTER,
                _BLINDSPOT_HUNTER,
                _RESEARCH_AGENT,
                _EVIDENCE_AGENT,
                _DEVILS_ADVOCATE,
                _REGRET_SIMULATOR,
                _THRESHOLD_ENGINE,
                _EXPERIMENT_PLANNER,
            )
            return self._analyses.update_status(
                decision_id=decision_id,
                run_id=run.id,
                status=AnalysisRunStatus.FAILED,
                agent_statuses=agent_statuses,
            )
        agent_statuses[_DECISION_ANALYZER] = AgentRunStatus.COMPLETED
        context.agent_results[_DECISION_ANALYZER] = decision_analysis
        result[_DECISION_ANALYZER] = decision_analysis.model_dump(mode="json")
        # REGRET ENGINE 2.0: recorded in the run's own result alongside
        # every stage's output - additive metadata about what historical
        # context was available, never something that changes any other
        # stage's persisted result. See `GET /decisions/{id}/historical-context`
        # for the equivalent standalone endpoint.
        if context.historical_context is not None:
            result[_HISTORICAL_CONTEXT] = context.historical_context.model_dump(mode="json")

        # --- Stage 2: Assumption Hunter --------------------------------------
        agent_statuses[_ASSUMPTION_HUNTER] = AgentRunStatus.RUNNING
        assumption_analysis = await self._run_assumption_hunter_step(
            decision_id, run.id, context, agent_statuses
        )
        if assumption_analysis is None:
            self._skip_remaining(
                agent_statuses,
                _BLINDSPOT_HUNTER,
                _RESEARCH_AGENT,
                _EVIDENCE_AGENT,
                _DEVILS_ADVOCATE,
                _REGRET_SIMULATOR,
                _THRESHOLD_ENGINE,
                _EXPERIMENT_PLANNER,
            )
            return self._analyses.update_status(
                decision_id=decision_id,
                run_id=run.id,
                status=AnalysisRunStatus.FAILED,
                completed_at=datetime.now(UTC),
                agent_statuses=agent_statuses,
                result=result,
            )
        agent_statuses[_ASSUMPTION_HUNTER] = AgentRunStatus.COMPLETED
        context.agent_results[_ASSUMPTION_HUNTER] = assumption_analysis
        result[_ASSUMPTION_HUNTER] = assumption_analysis.model_dump(mode="json")

        # Persist assumptions as their own entities before the Blindspot
        # Hunter runs - it needs their real, persisted ids to reference.
        context.assumptions = self._decisions.create_assumptions(
            decision_id,
            [finding.model_dump(mode="json") for finding in assumption_analysis.assumptions],
        )

        # --- Stage 3: Blindspot Hunter ----------------------------------------
        agent_statuses[_BLINDSPOT_HUNTER] = AgentRunStatus.RUNNING
        blindspot_analysis = await self._run_blindspot_hunter_step(
            decision_id, run.id, context, agent_statuses
        )
        if blindspot_analysis is None:
            self._skip_remaining(
                agent_statuses,
                _RESEARCH_AGENT,
                _EVIDENCE_AGENT,
                _DEVILS_ADVOCATE,
                _REGRET_SIMULATOR,
                _THRESHOLD_ENGINE,
                _EXPERIMENT_PLANNER,
            )
            return self._analyses.update_status(
                decision_id=decision_id,
                run_id=run.id,
                status=AnalysisRunStatus.FAILED,
                completed_at=datetime.now(UTC),
                agent_statuses=agent_statuses,
                result=result,
            )
        agent_statuses[_BLINDSPOT_HUNTER] = AgentRunStatus.COMPLETED
        context.agent_results[_BLINDSPOT_HUNTER] = blindspot_analysis
        result[_BLINDSPOT_HUNTER] = blindspot_analysis.model_dump(mode="json")

        # Persist blindspots before the Evidence Agent runs - it needs
        # their real, persisted ids to reference.
        context.blindspots = self._decisions.create_blindspots(
            decision_id,
            [finding.model_dump(mode="json") for finding in blindspot_analysis.blindspots],
        )

        # --- Stage 3a: Research Agent (OPTIONAL) --------------------------------
        # Unlike every other stage, a failure here never fails the run - it
        # only means external research is unavailable for this analysis.
        # See `_run_research_agent_step`'s docstring.
        agent_statuses[_RESEARCH_AGENT] = AgentRunStatus.RUNNING
        research_outcome = await self._run_research_agent_step(
            decision_id, run.id, context, agent_statuses
        )
        valid_assumption_ids = {str(item.id) for item in context.assumptions}
        valid_blindspot_ids = {str(item.id) for item in context.blindspots}
        if research_outcome is not None:
            research_analysis, research_results = research_outcome
            context.agent_results[_RESEARCH_AGENT] = research_analysis
            result[_RESEARCH_AGENT] = research_analysis.model_dump(mode="json")

            # Every finding's `research_result_id` MUST correspond to a
            # real result actually retrieved this run - anything else is
            # dropped, mirroring the fabrication guard already used for
            # the Evidence Agent's `evidence_id`.
            results_by_id = {str(item.id): item for item in research_results}
            external_evidence_to_persist = []
            for finding in research_analysis.findings:
                source_result = results_by_id.get(finding.research_result_id)
                if source_result is None:
                    logger.warning(
                        "Dropping external evidence finding with unrecognized "
                        "research_result_id decision_id=%s run_id=%s",
                        decision_id,
                        run.id,
                    )
                    continue
                dumped = finding.model_dump(mode="json")
                dumped["related_assumption_ids"] = [
                    aid for aid in dumped["related_assumption_ids"] if aid in valid_assumption_ids
                ]
                dumped["related_blindspot_ids"] = [
                    bid for bid in dumped["related_blindspot_ids"] if bid in valid_blindspot_ids
                ]
                # related_threshold_ids can't be validated yet - no
                # thresholds exist this early in the pipeline. Cleared
                # here rather than persisted as an unverifiable claim.
                dumped["related_threshold_ids"] = []
                dumped["source_url"] = source_result.url
                dumped["source_name"] = source_result.source_name
                dumped["published_at"] = (
                    source_result.published_at.isoformat() if source_result.published_at else None
                )
                dumped["retrieved_at"] = source_result.retrieved_at.isoformat()
                external_evidence_to_persist.append(dumped)
            context.external_evidence = self._decisions.create_external_evidence(
                decision_id, external_evidence_to_persist
            )

        # --- Stage 4: Evidence Agent -------------------------------------------
        agent_statuses[_EVIDENCE_AGENT] = AgentRunStatus.RUNNING
        evidence_analysis = await self._run_evidence_agent_step(
            decision_id, run.id, context, agent_statuses
        )
        if evidence_analysis is None:
            self._skip_remaining(
                agent_statuses,
                _DEVILS_ADVOCATE,
                _REGRET_SIMULATOR,
                _THRESHOLD_ENGINE,
                _EXPERIMENT_PLANNER,
            )
            return self._analyses.update_status(
                decision_id=decision_id,
                run_id=run.id,
                status=AnalysisRunStatus.FAILED,
                completed_at=datetime.now(UTC),
                agent_statuses=agent_statuses,
                result=result,
            )
        agent_statuses[_EVIDENCE_AGENT] = AgentRunStatus.COMPLETED
        context.agent_results[_EVIDENCE_AGENT] = evidence_analysis
        result[_EVIDENCE_AGENT] = evidence_analysis.model_dump(mode="json")

        # Persist evidence findings, separate from the source evidence they
        # analyze (see `DecisionRepository.create_evidence_findings`).
        valid_evidence_ids = {str(item.id) for item in evidence}
        valid_assumption_ids = {str(item.id) for item in context.assumptions}
        valid_blindspot_ids = {str(item.id) for item in context.blindspots}
        evidence_findings_to_persist = []
        for finding in evidence_analysis.findings:
            if finding.evidence_id not in valid_evidence_ids:
                # The model referenced an evidence_id it was never given -
                # drop it rather than persist a finding pointing at a
                # nonexistent (or worse, fabricated) source.
                logger.warning(
                    "Dropping evidence finding with unrecognized evidence_id "
                    "decision_id=%s run_id=%s",
                    decision_id,
                    run.id,
                )
                continue
            dumped = finding.model_dump(mode="json")
            dumped["related_assumption_ids"] = [
                aid for aid in dumped["related_assumption_ids"] if aid in valid_assumption_ids
            ]
            dumped["related_blindspot_ids"] = [
                bid for bid in dumped["related_blindspot_ids"] if bid in valid_blindspot_ids
            ]
            evidence_findings_to_persist.append(dumped)
        context.evidence_findings = self._decisions.create_evidence_findings(
            decision_id, evidence_findings_to_persist
        )

        # --- Stage 5: Devil's Advocate -----------------------------------------
        agent_statuses[_DEVILS_ADVOCATE] = AgentRunStatus.RUNNING
        devil_advocate_analysis = await self._run_devils_advocate_step(
            decision_id, run.id, context, agent_statuses
        )
        if devil_advocate_analysis is None:
            self._skip_remaining(
                agent_statuses, _REGRET_SIMULATOR, _THRESHOLD_ENGINE, _EXPERIMENT_PLANNER
            )
            return self._analyses.update_status(
                decision_id=decision_id,
                run_id=run.id,
                status=AnalysisRunStatus.FAILED,
                completed_at=datetime.now(UTC),
                agent_statuses=agent_statuses,
                result=result,
            )
        agent_statuses[_DEVILS_ADVOCATE] = AgentRunStatus.COMPLETED
        context.agent_results[_DEVILS_ADVOCATE] = devil_advocate_analysis
        result[_DEVILS_ADVOCATE] = devil_advocate_analysis.model_dump(mode="json")

        # Persist challenges before the Regret Simulator runs - it needs
        # their real, persisted ids to reference.
        valid_evidence_finding_ids = {str(item.id) for item in context.evidence_findings}
        challenges_to_persist = []
        for challenge in devil_advocate_analysis.challenges:
            dumped = challenge.model_dump(mode="json")
            dumped["related_assumption_ids"] = [
                aid for aid in dumped["related_assumption_ids"] if aid in valid_assumption_ids
            ]
            dumped["related_blindspot_ids"] = [
                bid for bid in dumped["related_blindspot_ids"] if bid in valid_blindspot_ids
            ]
            dumped["related_evidence_finding_ids"] = [
                fid
                for fid in dumped["related_evidence_finding_ids"]
                if fid in valid_evidence_finding_ids
            ]
            challenges_to_persist.append(dumped)
        context.challenges = self._decisions.create_challenges(decision_id, challenges_to_persist)

        # --- Stage 6: Regret Simulator ------------------------------------------
        agent_statuses[_REGRET_SIMULATOR] = AgentRunStatus.RUNNING
        regret_simulation = await self._run_regret_simulator_step(
            decision_id, run.id, context, agent_statuses
        )
        if regret_simulation is None:
            self._skip_remaining(agent_statuses, _THRESHOLD_ENGINE, _EXPERIMENT_PLANNER)
            return self._analyses.update_status(
                decision_id=decision_id,
                run_id=run.id,
                status=AnalysisRunStatus.FAILED,
                completed_at=datetime.now(UTC),
                agent_statuses=agent_statuses,
                result=result,
            )
        agent_statuses[_REGRET_SIMULATOR] = AgentRunStatus.COMPLETED
        context.agent_results[_REGRET_SIMULATOR] = regret_simulation
        result[_REGRET_SIMULATOR] = regret_simulation.model_dump(mode="json")

        # Persist regret scenarios before the Threshold Engine runs - it
        # needs their real, persisted ids to reference. The agent's own
        # response-scoped `id` (used only so highest_risk_scenario_id can
        # self-reference a sibling scenario within one response) is never
        # carried into storage - a fresh, real, persisted id is assigned
        # instead.
        valid_challenge_ids = {str(item.id) for item in context.challenges}
        scenarios_to_persist = []
        for scenario in regret_simulation.scenarios:
            dumped = scenario.model_dump(mode="json")
            dumped.pop("id", None)
            dumped["related_assumption_ids"] = [
                aid for aid in dumped["related_assumption_ids"] if aid in valid_assumption_ids
            ]
            dumped["related_challenge_ids"] = [
                cid for cid in dumped["related_challenge_ids"] if cid in valid_challenge_ids
            ]
            scenarios_to_persist.append(dumped)
        context.regret_scenarios = self._decisions.create_regret_scenarios(
            decision_id, scenarios_to_persist
        )

        # --- Stage 7: Threshold Engine ------------------------------------------
        agent_statuses[_THRESHOLD_ENGINE] = AgentRunStatus.RUNNING
        threshold_analysis = await self._run_threshold_engine_step(
            decision_id, run.id, context, agent_statuses
        )
        if threshold_analysis is None:
            self._skip_remaining(agent_statuses, _EXPERIMENT_PLANNER)
            return self._analyses.update_status(
                decision_id=decision_id,
                run_id=run.id,
                status=AnalysisRunStatus.FAILED,
                completed_at=datetime.now(UTC),
                agent_statuses=agent_statuses,
                result=result,
            )
        agent_statuses[_THRESHOLD_ENGINE] = AgentRunStatus.COMPLETED
        context.agent_results[_THRESHOLD_ENGINE] = threshold_analysis
        result[_THRESHOLD_ENGINE] = threshold_analysis.model_dump(mode="json")

        # Persist thresholds before the Experiment Planner runs - it needs
        # their real, persisted ids to reference. The agent's own
        # response-scoped `id` (used only so primary_threshold_id can
        # self-reference a sibling threshold within one response) is never
        # carried into storage - a fresh, real, persisted id is assigned
        # instead.
        valid_regret_scenario_ids = {str(item.id) for item in context.regret_scenarios}
        thresholds_to_persist = []
        for threshold in threshold_analysis.thresholds:
            dumped = threshold.model_dump(mode="json")
            dumped.pop("id", None)
            dumped["related_assumption_ids"] = [
                aid for aid in dumped["related_assumption_ids"] if aid in valid_assumption_ids
            ]
            dumped["related_regret_scenario_ids"] = [
                sid
                for sid in dumped["related_regret_scenario_ids"]
                if sid in valid_regret_scenario_ids
            ]
            thresholds_to_persist.append(dumped)
        context.thresholds = self._decisions.create_thresholds(decision_id, thresholds_to_persist)

        # --- Stage 7a: Value-of-Information (REGRET ENGINE 2.0, Step 20, additive) ---
        # Deterministic - no LLM call, never blocks or fails the run. Ranks
        # which uncertainty is most worth resolving before commitment, from
        # everything persisted so far (assumptions/blindspots/thresholds/
        # regret scenarios) - the Experiment Planner below reads its
        # primary_uncertainty_id/primary_threshold_id as a preference hint,
        # never a rule that overrides its own judgment (see
        # app.agents.experiment_planner's SYSTEM_PROMPT rule 13). A failure
        # here is logged and the run proceeds with voi_analysis=None,
        # exactly like the optional historical-context gathering step.
        context.value_of_information = self._compute_value_of_information(
            decision_id, user_id, context
        )
        if context.value_of_information is not None:
            result[_VALUE_OF_INFORMATION] = context.value_of_information.model_dump(mode="json")

        # --- Stage 8: Experiment Planner ----------------------------------------
        agent_statuses[_EXPERIMENT_PLANNER] = AgentRunStatus.RUNNING
        experiment_plan = await self._run_experiment_planner_step(
            decision_id, run.id, context, agent_statuses
        )
        if experiment_plan is None:
            return self._analyses.update_status(
                decision_id=decision_id,
                run_id=run.id,
                status=AnalysisRunStatus.FAILED,
                completed_at=datetime.now(UTC),
                agent_statuses=agent_statuses,
                result=result,
            )
        agent_statuses[_EXPERIMENT_PLANNER] = AgentRunStatus.COMPLETED
        context.agent_results[_EXPERIMENT_PLANNER] = experiment_plan
        result[_EXPERIMENT_PLANNER] = experiment_plan.model_dump(mode="json")

        # Persist experiments. The agent's own response-scoped `id` (used
        # only so recommended_experiment_id can self-reference a sibling
        # experiment within one response) is never carried into storage -
        # a fresh, real, persisted id is assigned instead. Every
        # experiment must target a real, persisted threshold - one
        # referencing a threshold id the model was never given is dropped
        # entirely rather than persisted with a dangling/fabricated target.
        valid_threshold_ids = {str(item.id) for item in context.thresholds}
        experiments_to_persist = []
        for experiment in experiment_plan.experiments:
            if experiment.target_threshold_id not in valid_threshold_ids:
                logger.warning(
                    "Dropping experiment with unrecognized target_threshold_id "
                    "decision_id=%s run_id=%s",
                    decision_id,
                    run.id,
                )
                continue
            dumped = experiment.model_dump(mode="json")
            dumped.pop("id", None)
            dumped["related_assumption_ids"] = [
                aid for aid in dumped["related_assumption_ids"] if aid in valid_assumption_ids
            ]
            dumped["related_regret_scenario_ids"] = [
                sid
                for sid in dumped["related_regret_scenario_ids"]
                if sid in valid_regret_scenario_ids
            ]
            experiments_to_persist.append(dumped)
        context.experiments = self._decisions.create_experiments(
            decision_id, experiments_to_persist
        )

        # A meaningful analysis that produced at least one recommended
        # experiment means there is now something concrete for the user to
        # go validate before committing further - move the decision out of
        # its prior state into `needs_validation`. Never marked "approved"
        # or "rejected": REGRET ENGINE validates decisions, it doesn't make
        # them.
        if context.experiments:
            self._decisions.update(
                decision_id, DecisionUpdate(status=DecisionStatus.NEEDS_VALIDATION)
            )

        completed_run = self._analyses.update_status(
            decision_id=decision_id,
            run_id=run.id,
            status=AnalysisRunStatus.COMPLETED,
            completed_at=datetime.now(UTC),
            agent_statuses=agent_statuses,
            result=result,
        )

        # --- Stage 9: Quality Check (REGRET ENGINE 2.0, Step 24, additive) ---
        # Deterministic - no LLM call, never blocks or fails the run. Runs
        # AFTER the run is already marked completed (spec section 18: quality
        # checking happens after the structured pipeline, on its way to the
        # Decision Report) - a quality-check failure here can never change
        # this run's own completion status. Mirrors
        # `_compute_value_of_information`/`_gather_historical_context`'s own
        # try/except-log-never-block pattern exactly.
        try:
            self._run_quality_check(decision_id, user_id)
        except Exception:  # noqa: BLE001 - quality check is additive; never fail the run
            logger.exception("Quality check failed decision_id=%s run_id=%s", decision_id, run.id)

        return completed_run

    def _run_quality_check(self, decision_id: UUID, user_id: str) -> None:
        """Runs the deterministic Quality Engine (`app.quality`) against
        this decision's just-completed analysis and persists a fresh
        `QualityAssessment`. Never re-implemented here - this method only
        delegates to `self._quality`; see `app.quality.service
        .QualityService.run_quality_check` for the actual checks."""
        self._quality.run_quality_check(decision_id, user_id)

    async def _run_decision_analyzer_step(
        self,
        decision_id: UUID,
        run_id: UUID,
        context: AnalysisContext,
        agent_statuses: dict[str, AgentRunStatus],
    ) -> DecisionAnalysis | None:
        """Run and validate the Decision Analyzer. Returns None on any failure.

        On failure, persists a `failed` status immediately with a safe
        error message - the caller only needs to check for a `None` return
        to know the run has already been finalized.
        """
        try:
            raw_result = await run_decision_analyzer(
                context.decision, context.evidence, context.historical_context
            )
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any agent/model failure lands here
            logger.error(
                "Decision analyzer failed decision_id=%s run_id=%s error=%s",
                decision_id,
                run_id,
                str(exc)[:_MAX_LOGGED_ERROR_CHARS],
            )
            agent_statuses[_DECISION_ANALYZER] = AgentRunStatus.FAILED
            self._analyses.update_status(
                decision_id=decision_id,
                run_id=run_id,
                status=AnalysisRunStatus.FAILED,
                completed_at=datetime.now(UTC),
                error_message=_SAFE_MODEL_FAILURE_MESSAGE,
                agent_statuses=agent_statuses,
            )
            return None

        validated = self._validate(raw_result, DecisionAnalysis)
        if validated is None:
            logger.error(
                "Decision analyzer returned invalid structured output decision_id=%s run_id=%s",
                decision_id,
                run_id,
            )
            agent_statuses[_DECISION_ANALYZER] = AgentRunStatus.FAILED
            self._analyses.update_status(
                decision_id=decision_id,
                run_id=run_id,
                status=AnalysisRunStatus.FAILED,
                completed_at=datetime.now(UTC),
                error_message=_SAFE_INVALID_OUTPUT_MESSAGE,
                agent_statuses=agent_statuses,
            )
            return None

        return validated

    async def _run_assumption_hunter_step(
        self,
        decision_id: UUID,
        run_id: UUID,
        context: AnalysisContext,
        agent_statuses: dict[str, AgentRunStatus],
    ) -> AssumptionAnalysis | None:
        """Run and validate the Assumption Hunter. Returns None on any failure.

        Always called with `context.decision_analysis` already populated -
        the Assumption Hunter consumes that structured result, never the
        raw decision, per the pipeline's design.
        """
        decision_analysis = context.decision_analysis
        assert decision_analysis is not None  # guaranteed by call order in run_analysis

        try:
            raw_result = await run_assumption_hunter(decision_analysis, context.evidence)
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any agent/model failure lands here
            logger.error(
                "Assumption hunter failed decision_id=%s run_id=%s error=%s",
                decision_id,
                run_id,
                str(exc)[:_MAX_LOGGED_ERROR_CHARS],
            )
            agent_statuses[_ASSUMPTION_HUNTER] = AgentRunStatus.FAILED
            return None

        validated = self._validate(raw_result, AssumptionAnalysis)
        if validated is None:
            logger.error(
                "Assumption hunter returned invalid structured output decision_id=%s run_id=%s",
                decision_id,
                run_id,
            )
            agent_statuses[_ASSUMPTION_HUNTER] = AgentRunStatus.FAILED
            return None

        return validated

    async def _run_blindspot_hunter_step(
        self,
        decision_id: UUID,
        run_id: UUID,
        context: AnalysisContext,
        agent_statuses: dict[str, AgentRunStatus],
    ) -> BlindspotAnalysis | None:
        """Run and validate the Blindspot Hunter. Returns None on any failure.

        Always called with `context.decision_analysis` and
        `context.assumptions` (the *persisted* assumptions, with real ids)
        already populated - the Blindspot Hunter consumes those, never the
        raw decision and never the Assumption Hunter's raw output, per the
        pipeline's design.
        """
        decision_analysis = context.decision_analysis
        assert decision_analysis is not None  # guaranteed by call order in run_analysis

        try:
            raw_result = await run_blindspot_hunter(
                decision_analysis, context.assumptions, context.evidence
            )
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any agent/model failure lands here
            logger.error(
                "Blindspot hunter failed decision_id=%s run_id=%s error=%s",
                decision_id,
                run_id,
                str(exc)[:_MAX_LOGGED_ERROR_CHARS],
            )
            agent_statuses[_BLINDSPOT_HUNTER] = AgentRunStatus.FAILED
            return None

        validated = self._validate(raw_result, BlindspotAnalysis)
        if validated is None:
            logger.error(
                "Blindspot hunter returned invalid structured output decision_id=%s run_id=%s",
                decision_id,
                run_id,
            )
            agent_statuses[_BLINDSPOT_HUNTER] = AgentRunStatus.FAILED
            return None

        return validated

    async def _run_research_agent_step(
        self,
        decision_id: UUID,
        run_id: UUID,
        context: AnalysisContext,
        agent_statuses: dict[str, AgentRunStatus],
    ) -> tuple[ResearchAnalysis, list] | None:
        """Run and validate the (optional) Research Agent. Returns None if
        research is unavailable OR genuinely failed - either way, the rest
        of the pipeline proceeds using whatever evidence already exists.

        This is the one stage in the whole pipeline where failure does
        NOT fail the analysis run: `ResearchUnavailable` (no provider
        configured, or the provider failed on every query) marks this
        stage `UNAVAILABLE`, distinct from `FAILED`, and returns `None`
        exactly like a genuine agent/model exception would - the caller
        (`run_analysis`) treats both identically by simply not persisting
        any external evidence and moving on to the Evidence Agent. A
        malformed/missing structured output from either of the Research
        Agent's two internal Strands calls is still logged as a failure
        (not silently ignored), but likewise never blocks the pipeline.
        """
        decision_analysis = context.decision_analysis
        assert decision_analysis is not None  # guaranteed by call order in run_analysis

        try:
            raw_result, research_results = await run_research_agent(
                decision_analysis,
                context.assumptions,
                context.blindspots,
                context.evidence,
                self._research,
            )
        except ResearchUnavailable as exc:
            logger.info(
                "Research agent unavailable decision_id=%s run_id=%s reason=%s",
                decision_id,
                run_id,
                str(exc)[:_MAX_LOGGED_ERROR_CHARS],
            )
            agent_statuses[_RESEARCH_AGENT] = AgentRunStatus.UNAVAILABLE
            return None
        except Exception as exc:  # noqa: BLE001 - any other research failure must not break the pipeline
            logger.error(
                "Research agent failed decision_id=%s run_id=%s error=%s",
                decision_id,
                run_id,
                str(exc)[:_MAX_LOGGED_ERROR_CHARS],
            )
            agent_statuses[_RESEARCH_AGENT] = AgentRunStatus.FAILED
            return None

        validated = self._validate(raw_result, ResearchAnalysis)
        if validated is None:
            logger.error(
                "Research agent returned invalid structured output decision_id=%s run_id=%s",
                decision_id,
                run_id,
            )
            agent_statuses[_RESEARCH_AGENT] = AgentRunStatus.FAILED
            return None

        agent_statuses[_RESEARCH_AGENT] = AgentRunStatus.COMPLETED
        return validated, research_results

    async def _run_evidence_agent_step(
        self,
        decision_id: UUID,
        run_id: UUID,
        context: AnalysisContext,
        agent_statuses: dict[str, AgentRunStatus],
    ) -> EvidenceAnalysis | None:
        """Run and validate the Evidence Agent. Returns None on any failure.

        Always called with `context.decision_analysis`, `context.assumptions`,
        and `context.blindspots` (all persisted, with real ids) already
        populated - the Evidence Agent consumes those plus the decision's
        evidence, never the raw decision and never the upstream agents' raw
        output, per the pipeline's design.
        """
        decision_analysis = context.decision_analysis
        assert decision_analysis is not None  # guaranteed by call order in run_analysis

        try:
            raw_result = await run_evidence_agent(
                decision_analysis,
                context.assumptions,
                context.blindspots,
                context.evidence,
            )
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any agent/model failure lands here
            logger.error(
                "Evidence agent failed decision_id=%s run_id=%s error=%s",
                decision_id,
                run_id,
                str(exc)[:_MAX_LOGGED_ERROR_CHARS],
            )
            agent_statuses[_EVIDENCE_AGENT] = AgentRunStatus.FAILED
            return None

        validated = self._validate(raw_result, EvidenceAnalysis)
        if validated is None:
            logger.error(
                "Evidence agent returned invalid structured output decision_id=%s run_id=%s",
                decision_id,
                run_id,
            )
            agent_statuses[_EVIDENCE_AGENT] = AgentRunStatus.FAILED
            return None

        return validated

    async def _run_devils_advocate_step(
        self,
        decision_id: UUID,
        run_id: UUID,
        context: AnalysisContext,
        agent_statuses: dict[str, AgentRunStatus],
    ) -> DevilAdvocateAnalysis | None:
        """Run and validate the Devil's Advocate. Returns None on any failure.

        Always called with `context.decision_analysis`, `context.assumptions`,
        `context.blindspots`, and `context.evidence_findings` (all
        persisted, with real ids) already populated - the Devil's Advocate
        consumes those, never the raw decision, never raw evidence
        documents, and never any upstream agent's raw output, per the
        pipeline's design.
        """
        decision_analysis = context.decision_analysis
        assert decision_analysis is not None  # guaranteed by call order in run_analysis

        try:
            raw_result = await run_devils_advocate(
                decision_analysis,
                context.assumptions,
                context.blindspots,
                context.evidence_findings,
            )
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any agent/model failure lands here
            logger.error(
                "Devil's advocate failed decision_id=%s run_id=%s error=%s",
                decision_id,
                run_id,
                str(exc)[:_MAX_LOGGED_ERROR_CHARS],
            )
            agent_statuses[_DEVILS_ADVOCATE] = AgentRunStatus.FAILED
            return None

        validated = self._validate(raw_result, DevilAdvocateAnalysis)
        if validated is None:
            logger.error(
                "Devil's advocate returned invalid structured output decision_id=%s run_id=%s",
                decision_id,
                run_id,
            )
            agent_statuses[_DEVILS_ADVOCATE] = AgentRunStatus.FAILED
            return None

        return validated

    async def _run_regret_simulator_step(
        self,
        decision_id: UUID,
        run_id: UUID,
        context: AnalysisContext,
        agent_statuses: dict[str, AgentRunStatus],
    ) -> RegretSimulation | None:
        """Run and validate the Regret Simulator. Returns None on any failure.

        Always called with `context.decision_analysis`, `context.assumptions`,
        `context.blindspots`, `context.evidence_findings`, and
        `context.challenges` (all persisted, with real ids) already
        populated - the Regret Simulator consumes those, never the raw
        decision and never any upstream agent's raw output, per the
        pipeline's design.
        """
        decision_analysis = context.decision_analysis
        assert decision_analysis is not None  # guaranteed by call order in run_analysis

        try:
            raw_result = await run_regret_simulator(
                decision_analysis,
                context.assumptions,
                context.blindspots,
                context.evidence_findings,
                context.challenges,
            )
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any agent/model failure lands here
            logger.error(
                "Regret simulator failed decision_id=%s run_id=%s error=%s",
                decision_id,
                run_id,
                str(exc)[:_MAX_LOGGED_ERROR_CHARS],
            )
            agent_statuses[_REGRET_SIMULATOR] = AgentRunStatus.FAILED
            return None

        validated = self._validate(raw_result, RegretSimulation)
        if validated is None:
            logger.error(
                "Regret simulator returned invalid structured output decision_id=%s run_id=%s",
                decision_id,
                run_id,
            )
            agent_statuses[_REGRET_SIMULATOR] = AgentRunStatus.FAILED
            return None

        return validated

    async def _run_threshold_engine_step(
        self,
        decision_id: UUID,
        run_id: UUID,
        context: AnalysisContext,
        agent_statuses: dict[str, AgentRunStatus],
    ) -> ThresholdAnalysis | None:
        """Run and validate the Threshold Engine. Returns None on any failure.

        Always called with `context.decision_analysis`, `context.assumptions`,
        `context.blindspots`, `context.evidence_findings`,
        `context.challenges`, and `context.regret_scenarios` (all
        persisted, with real ids) already populated - the Threshold Engine
        consumes those, never the raw decision and never any upstream
        agent's raw output, per the pipeline's design. Calculated
        thresholds are independently re-verified deterministically inside
        `run_threshold_engine` itself before this method ever sees them.
        """
        decision_analysis = context.decision_analysis
        assert decision_analysis is not None  # guaranteed by call order in run_analysis

        try:
            raw_result = await run_threshold_engine(
                decision_analysis,
                context.assumptions,
                context.blindspots,
                context.evidence_findings,
                context.challenges,
                context.regret_scenarios,
            )
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any agent/model failure lands here
            logger.error(
                "Threshold engine failed decision_id=%s run_id=%s error=%s",
                decision_id,
                run_id,
                str(exc)[:_MAX_LOGGED_ERROR_CHARS],
            )
            agent_statuses[_THRESHOLD_ENGINE] = AgentRunStatus.FAILED
            return None

        validated = self._validate(raw_result, ThresholdAnalysis)
        if validated is None:
            logger.error(
                "Threshold engine returned invalid structured output decision_id=%s run_id=%s",
                decision_id,
                run_id,
            )
            agent_statuses[_THRESHOLD_ENGINE] = AgentRunStatus.FAILED
            return None

        return validated

    async def _run_experiment_planner_step(
        self,
        decision_id: UUID,
        run_id: UUID,
        context: AnalysisContext,
        agent_statuses: dict[str, AgentRunStatus],
    ) -> ExperimentPlan | None:
        """Run and validate the Experiment Planner. Returns None on any failure.

        Always called with `context.decision_analysis`, `context.assumptions`,
        `context.blindspots`, `context.evidence_findings`,
        `context.challenges`, `context.regret_scenarios`, and
        `context.thresholds` (all persisted, with real ids) already
        populated - the Experiment Planner consumes those, never the raw
        decision and never any upstream agent's raw output, per the
        pipeline's design.
        """
        decision_analysis = context.decision_analysis
        assert decision_analysis is not None  # guaranteed by call order in run_analysis

        try:
            raw_result = await run_experiment_planner(
                decision_analysis,
                context.assumptions,
                context.blindspots,
                context.evidence_findings,
                context.challenges,
                context.regret_scenarios,
                context.thresholds,
                context.value_of_information,
            )
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any agent/model failure lands here
            logger.error(
                "Experiment planner failed decision_id=%s run_id=%s error=%s",
                decision_id,
                run_id,
                str(exc)[:_MAX_LOGGED_ERROR_CHARS],
            )
            agent_statuses[_EXPERIMENT_PLANNER] = AgentRunStatus.FAILED
            return None

        validated = self._validate(raw_result, ExperimentPlan)
        if validated is None:
            logger.error(
                "Experiment planner returned invalid structured output decision_id=%s run_id=%s",
                decision_id,
                run_id,
            )
            agent_statuses[_EXPERIMENT_PLANNER] = AgentRunStatus.FAILED
            return None

        return validated

    def _gather_historical_context(
        self, user_id: str, decision: DecisionResponse
    ) -> HistoricalContext | None:
        """Gather Decision Similarity + Historical Insight context for this
        run - additive, never blocking. Returns `None` (never raises) if
        gathering fails for any reason; the pipeline proceeds exactly as
        it would have with no history at all. Mirrors the Research
        Agent's own "optional stage, failure never fails the run"
        handling, but is not itself a pipeline "stage" with its own
        agent_status - it has no LLM call and nothing about it can be
        "skipped" downstream, since nothing downstream depends on it
        succeeding.
        """
        try:
            return self._historical_context.get_historical_context(user_id, decision)
        except Exception:  # noqa: BLE001 - never let historical lookup block/fail an analysis run
            logger.exception(
                "Historical context gathering failed decision_id=%s user_id=%s",
                decision.id,
                user_id,
            )
            return None

    def _compute_value_of_information(
        self, decision_id: UUID, user_id: str, context: AnalysisContext
    ) -> ValueOfInformationAnalysis | None:
        """Compute and persist this run's Value-of-Information analysis
        (REGRET ENGINE 2.0, Step 20) - additive, never blocking. Returns
        `None` (never raises) if computation fails for any reason; the
        pipeline proceeds exactly as it would have with no VOI ranking at
        all. Mirrors `_gather_historical_context`'s own failure handling.

        Reads directly from `context` (already-persisted assumptions/
        blindspots/thresholds/regret scenarios for THIS run) rather than
        re-querying the repository, since this runs mid-pipeline before
        experiments exist yet - `ValueOfInformationService
        .compute_and_persist` still re-lists experiments itself (there are
        none yet at this point, which is correct: no uncertainty can have
        related_experiment_id set on the very first computation for a
        decision).

        `user_id` is passed through so `compute_and_persist` can enrich
        each ranked item with this same user's own Cross-Decision
        Learning signal (Step 23) - a read-only, additive lookup that
        never affects VOI's own ranking; see
        `ValueOfInformationService._apply_cross_decision_signals`.
        """
        try:
            return self._value_of_information.compute_and_persist(
                context.decision, user_id=user_id, historical_context=context.historical_context
            )
        except Exception:  # noqa: BLE001 - never let VOI computation block/fail an analysis run
            logger.exception("Value-of-Information computation failed decision_id=%s", decision_id)
            return None

    @staticmethod
    def _is_abandoned(run: AnalysisRun) -> bool:
        """Whether an in-flight run should be treated as abandoned rather
        than actually active.

        A `queued` run is never abandoned - it hasn't started yet, so
        there's no "how long has it been running" clock to check (and a
        run only stays `queued` for a moment, transitioning to `running`
        synchronously right after creation). A `running` run past the
        combined `analysis_max_duration_seconds` + `analysis_lock_grace_seconds`
        budget almost certainly means the process that was running it
        crashed or was killed before it could reach a terminal status -
        treating it as still active would wedge the decision, unable to
        ever be re-analyzed.
        """
        if run.status != AnalysisRunStatus.RUNNING or run.started_at is None:
            return False
        settings = get_settings()
        max_age = settings.analysis_max_duration_seconds + settings.analysis_lock_grace_seconds
        age_seconds = (datetime.now(UTC) - run.started_at).total_seconds()
        return age_seconds > max_age

    @staticmethod
    def _skip_remaining(agent_statuses: dict[str, AgentRunStatus], *stage_ids: str) -> None:
        """Mark every listed stage as SKIPPED - there is nothing valid yet
        for any of them to consume, since an earlier stage failed."""
        for stage_id in stage_ids:
            agent_statuses[stage_id] = AgentRunStatus.SKIPPED

    @staticmethod
    def _validate[T](raw: T, schema: type[T]) -> T | None:
        """Re-validate an agent's output against its own schema.

        The Strands SDK already validates structured output against the
        Pydantic model before returning it, but this re-validation is kept
        as an explicit, independent check - if the SDK's guarantee ever
        changes, this is where malformed data gets caught rather than
        silently persisted.
        """
        try:
            return schema.model_validate(raw.model_dump())  # type: ignore[attr-defined]
        except PydanticValidationError:
            return None
