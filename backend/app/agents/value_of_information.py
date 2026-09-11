"""Value-of-Information orchestration (REGRET ENGINE 2.0, Step 20).

`ValueOfInformationService` is the orchestration point for this feature -
mirrors `app.memory.historical_context.HistoricalContextService`'s shape
exactly: load already-persisted entities, hand them to a deterministic
scoring function (`app.services.value_of_information_service
.compute_analysis`), persist the result, return it. No LLM call happens
anywhere in this module or the one it delegates scoring to - see that
module's own docstring for the full, documented formula.

Despite living under `app.agents` (matching this project's existing
convention of naming pipeline-adjacent orchestration modules after the
concept they add, e.g. `app.agents.orchestrator`, `app.agents.context`),
this module contains NO `strands.Agent` and makes NO Bedrock call -
Value-of-Information is a purely deterministic feature, per the Step 20
spec's own "use Strands/Bedrock only where genuine qualitative
interpretation is necessary" instruction and this feature's inputs
already being fully structured (enums/floats) rather than free text.

RECOMPUTE / VERSIONING (spec sections 20-21):

`compute_and_persist` always creates a NEW `ValueOfInformationAnalysis`
record - it never overwrites a previous one. If a previous analysis
exists for the decision, it is marked `superseded_by_analysis_id`
(pointing at the new one) but is never deleted, mirroring
`ReEvaluation`'s own "history is never destroyed" convention. This is
what lets a decision's full prioritization history stay reconstructable:
"before the experiment, retention was VERY_HIGH priority; after, it
dropped and a different uncertainty became primary" - exactly the
before/after story Step 21's adaptive loop will build on, without this
step needing to implement that loop itself.
"""

from uuid import UUID

from app.core.logging import get_logger
from app.memory.historical_context import HistoricalContextService
from app.memory.similarity_schemas import HistoricalContext
from app.repositories.decision_repository import DecisionRepository
from app.repositories.value_of_information_repository import ValueOfInformationRepository
from app.schemas.decision import DecisionResponse
from app.services.value_of_information_service import compute_analysis

logger = get_logger(__name__)


class ValueOfInformationService:
    """Computes, persists, and retrieves Value-of-Information analyses."""

    def __init__(
        self,
        decision_repository: DecisionRepository,
        voi_repository: ValueOfInformationRepository,
        historical_context_service: HistoricalContextService | None = None,
    ) -> None:
        self._decisions = decision_repository
        self._voi = voi_repository
        # Optional: when provided, Step 19's historical context is folded
        # in as a last-resort tiebreaker only - see
        # `app.services.value_of_information_service` module docstring
        # step 5. `None` is a fully valid, common case (e.g. the
        # decision's own orchestrator run already computed historical
        # context and can pass it in directly instead of recomputing it).
        self._historical_context = historical_context_service

    def compute_and_persist(
        self,
        decision: DecisionResponse,
        user_id: str | None = None,
        historical_context: HistoricalContext | None = None,
    ):
        """Compute a fresh analysis from this decision's current,
        already-persisted assumptions/blindspots/thresholds/regret
        scenarios/experiments, persist it, and supersede the previous
        analysis (if one exists) without deleting it.

        `historical_context`, if given, is used directly. Otherwise, if
        this service was constructed with a `HistoricalContextService`
        AND `user_id` is provided, historical context is fetched fresh.
        Otherwise the analysis proceeds with `historical_context=None` -
        historical relevance is always a tiebreaker only, never required
        for scoring to succeed (see the evidence-hierarchy principle
        carried over from Step 19).
        """
        decision_id = decision.id
        assumptions = self._decisions.list_assumptions(decision_id)
        blindspots = self._decisions.list_blindspots(decision_id)
        thresholds = self._decisions.list_thresholds(decision_id)
        regret_scenarios = self._decisions.list_regret_scenarios(decision_id)
        experiments = self._decisions.list_experiments(decision_id)

        if historical_context is None and self._historical_context is not None and user_id:
            try:
                historical_context = self._historical_context.get_historical_context(
                    user_id, decision
                )
            except Exception:  # noqa: BLE001 - historical context is a tiebreaker only, never required
                logger.exception(
                    "Historical context lookup failed during VOI computation decision_id=%s",
                    decision_id,
                )
                historical_context = None

        analysis = compute_analysis(
            decision, assumptions, blindspots, thresholds, regret_scenarios, experiments,
            historical_context,
        )

        previous = self._voi.get_latest(decision_id)
        self._voi.create(analysis)
        if previous is not None:
            self._voi.mark_superseded(decision_id, previous.analysis_id, analysis.analysis_id)

        logger.info(
            "Value-of-Information analysis computed decision_id=%s analysis_id=%s "
            "uncertainty_count=%d primary_uncertainty_id=%s",
            decision_id,
            analysis.analysis_id,
            len(analysis.ranked_uncertainties),
            analysis.primary_uncertainty_id,
        )
        return analysis

    def get_latest(self, decision_id: UUID):
        """The most recently computed analysis for a decision, or `None`
        if none has ever been computed - never an error; a decision that
        hasn't reached this pipeline stage yet legitimately has nothing
        to report."""
        return self._voi.get_latest(decision_id)

    def list_history(self, decision_id: UUID):
        """Every VOI analysis ever computed for a decision, oldest first -
        the decision's full prioritization history (see module
        docstring's recompute/versioning section)."""
        return self._voi.list_for_decision(decision_id)
