"""Historical Context retrieval (REGRET ENGINE 2.0).

`HistoricalContextService` is the orchestration point for Decision
Similarity + Historical Insight retrieval: given a decision (the one
about to be, or already being, analyzed), find the SAME user's own most
relevant past decisions, and surface a bounded set of real, provenance-
tracked learnings from their Decision Memory as additive context.

This is explicitly NOT a fourth agent and NOT a fourth LLM call - every
step is deterministic Python over already-persisted data:

    DecisionRepository.list_for_user (bounded, user-scoped)
        -> DecisionSimilarityService.rank (deterministic scoring)
        -> top HISTORICAL_TOP_K candidates
        -> MemoryRepository.list_learnings_for_decision (per candidate)
        -> filter/rank/bound to HISTORICAL_INSIGHT_LIMIT
        -> HistoricalContext (aggregated, explainable, bounded)

USER-SCOPING - THE OWNERSHIP BOUNDARY, EXPLICITLY:

This is the one place in this module that matters most. Historical
retrieval must NEVER return another user's decision memory. That
guarantee is enforced here, at the service layer, not left to the API
layer or to chance:

- The ONLY way this service ever discovers candidate past decisions is
  `DecisionRepository.list_for_user(user_id, ...)`, which queries GSI1
  keyed by `USER#<user_id>` - it is architecturally impossible for this
  query to return a decision owned by a different user, because the
  partition key itself is the user id.
- `get_historical_context` takes `user_id` as a required, explicit
  parameter (never inferred from the decision being analyzed, and never
  defaulted) - the caller must state whose history is being searched.
- Every learning retrieved afterward (`MemoryRepository.
  list_learnings_for_decision`) is scoped to a `decision_id` that came
  from that same `user_id`-filtered candidate list - there is no code
  path in this module that ever accepts or looks up a decision id from
  anywhere else.
- See `backend/tests/test_historical_context.py::
  test_user_a_cannot_retrieve_user_b_historical_context` (and the
  mirrored API-level test) for the mandatory, explicit regression test
  for this guarantee.

WHY THIS IS CONTEXT, NEVER TRUTH (see also `similarity_schemas.py`):

`get_historical_context` never touches a `Threshold`, `Experiment`,
`ExperimentResult`, or the current decision's own constraints - it only
ever produces a read-only `HistoricalContext` object. Nothing it returns
is ever written back into the current decision's own records. The
orchestrator (`app.agents.orchestrator`) only ever passes the result of
this service into a prompt as clearly-labeled, lower-priority context -
see that module's own docstring for the 8-level evidence hierarchy this
was built to support.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4, uuid5

from app.core.config import get_settings
from app.core.logging import get_logger
from app.memory.memory_repository import MemoryRepository
from app.memory.memory_schemas import LearningType, MemoryLearning
from app.memory.similarity import DecisionSimilarityService
from app.memory.similarity_schemas import HistoricalContext, HistoricalInsight, SimilarityScore
from app.repositories.decision_repository import DecisionRepository
from app.schemas.decision import DecisionCreate, DecisionResponse, DecisionStatus

logger = get_logger(__name__)

# Deterministic namespace for insight ids, distinct from
# `app.memory.memory_service._LEARNING_ID_NAMESPACE` - insights are a
# different kind of derived object (view of a learning, not the learning
# itself) and deliberately get their own namespace rather than reusing
# memory's, so a collision between the two id spaces is architecturally
# impossible, not just unlikely.
_INSIGHT_ID_NAMESPACE = UUID("2b6a1c4e-9f3d-4a2b-8e7c-5d1f9a3b6c8e")

# Learning types that represent a real, observed outcome - the only kinds
# of learning ever surfaced as a HistoricalInsight. Deliberately excludes
# `unresolved_uncertainty`/`experiment_learning`'s raw-summary variant from
# the *insight* list itself (they still feed `unresolved_patterns`, a
# separate, clearly-labeled aggregate) - a historical insight should read
# as "here is something that happened," never as "here is something we
# never actually found out."
_INSIGHT_ELIGIBLE_TYPES = {
    LearningType.ASSUMPTION_VALIDATED,
    LearningType.ASSUMPTION_WEAKENED,
    LearningType.ASSUMPTION_FAILED,
    LearningType.THRESHOLD_VALIDATED,
    LearningType.THRESHOLD_FAILED,
    LearningType.THRESHOLD_INCONCLUSIVE,
    LearningType.UNEXPECTED_RESULT,
    LearningType.DECISION_OUTCOME,
}


class HistoricalContextService:
    """Finds a user's own relevant past decisions and surfaces bounded,
    provenance-tracked historical insights from their Decision Memory."""

    def __init__(
        self,
        decision_repository: DecisionRepository,
        memory_repository: MemoryRepository,
        similarity_service: DecisionSimilarityService | None = None,
    ) -> None:
        self._decisions = decision_repository
        self._memory = memory_repository
        self._similarity = similarity_service if similarity_service is not None else (
            DecisionSimilarityService()
        )

    def get_historical_context(
        self, user_id: str, decision: DecisionResponse
    ) -> HistoricalContext:
        """Build the historical context for `decision`, searching only
        `user_id`'s own past decisions - see module docstring for the
        ownership guarantee this method exists to uphold.

        Never raises for a user with no history yet, or for a decision
        with no sufficiently similar past decisions - both are the
        normal `found=False` case, not an error.
        """
        settings = get_settings()

        candidates = self._load_candidates(user_id, decision.id, settings.historical_search_limit)
        if not candidates:
            return HistoricalContext(
                found=False,
                warnings=["No past decisions were available for comparison."],
            )

        ranked = self._similarity.rank(
            decision,
            [(past, assumptions, thresholds) for past, assumptions, thresholds in candidates],
        )
        relevant = [s for s in ranked if s.matched_features][: settings.historical_top_k]

        warnings: list[str] = []
        if not relevant:
            warnings.append(
                "No past decision was similar enough to surface as relevant context."
            )
            return HistoricalContext(found=False, warnings=warnings)

        if len(candidates) < settings.historical_search_limit and len(candidates) < 3:
            warnings.append(
                f"Only {len(candidates)} past decision(s) were available for comparison."
            )

        insights = self._collect_insights(relevant, settings.historical_insight_limit)

        recurring_variables = self._recurring_variables(insights)
        previously_failed_assumptions = [
            insight.statement
            for insight in insights
            if insight.learning_type == LearningType.ASSUMPTION_FAILED
        ]
        previously_validated_thresholds = [
            insight.statement
            for insight in insights
            if insight.learning_type == LearningType.THRESHOLD_VALIDATED
        ]
        unresolved_patterns = self._unresolved_patterns(relevant)

        logger.info(
            "Historical context built user_id=%s decision_id=%s relevant_count=%d insight_count=%d",
            user_id,
            decision.id,
            len(relevant),
            len(insights),
        )

        return HistoricalContext(
            found=True,
            relevant_decisions=relevant,
            relevant_decisions_count=len(relevant),
            relevant_learnings=insights,
            recurring_variables=recurring_variables,
            previously_failed_assumptions=previously_failed_assumptions,
            previously_validated_thresholds=previously_validated_thresholds,
            unresolved_patterns=unresolved_patterns,
            warnings=warnings,
        )

    def get_historical_context_preview(
        self, user_id: str, draft: DecisionCreate
    ) -> HistoricalContext:
        """The same historical context computation as
        `get_historical_context`, but for a decision that has NOT been
        created yet - powers the "Relevant from your past decisions"
        section on the new-decision intake page (see Step 19 spec),
        where the user is still typing and no `decision_id` exists.

        Builds a transient, never-persisted `DecisionResponse` from the
        draft text alone (a fresh, throwaway id - never written to
        DynamoDB, never returned to any other caller) purely so the
        existing, real `DecisionSimilarityService.rank` can compare it
        against the user's own real past decisions using the exact same
        scoring logic - no separate "preview" scoring path to keep in
        sync. Still fully user-scoped: `_load_candidates` below is
        exactly the same call as the persisted-decision path.
        """
        now = datetime.now(UTC)
        transient = DecisionResponse(
            id=uuid4(),
            title=draft.title,
            description=draft.description,
            desired_outcome=draft.desired_outcome,
            budget=draft.budget,
            currency=draft.currency,
            timeline=draft.timeline,
            location=draft.location,
            risk_tolerance=draft.risk_tolerance,
            beliefs=draft.beliefs,
            status=DecisionStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )
        return self.get_historical_context(user_id, transient)

    # --- internal ------------------------------------------------------------

    def _load_candidates(
        self, user_id: str, exclude_decision_id: UUID, search_limit: int
    ) -> list[tuple[DecisionResponse, list, list]]:
        """The user's own past decisions (never another user's - see
        `DecisionRepository.list_for_user`'s GSI1-partition-key guarantee),
        each paired with its persisted assumptions/thresholds, excluding
        the decision currently being analyzed itself.
        """
        items, _ = self._decisions.list_for_user(user_id, limit=search_limit)
        candidates = []
        for past in items:
            if past.id == exclude_decision_id:
                continue
            assumptions = self._decisions.list_assumptions(past.id)
            thresholds = self._decisions.list_thresholds(past.id)
            candidates.append((past, assumptions, thresholds))
        return candidates

    def _collect_insights(
        self, relevant: list[SimilarityScore], insight_limit: int
    ) -> list[HistoricalInsight]:
        """Every eligible learning from each relevant decision's memory,
        turned into a `HistoricalInsight` whose `relevance_score` mirrors
        the source decision's own similarity score, then globally ranked
        by relevance and bounded to `insight_limit`.
        """
        candidates: list[HistoricalInsight] = []

        for score in relevant:
            learnings = self._memory.list_learnings_for_decision(score.decision_id)
            memory_id = self._memory_id_for(learnings)
            for learning in learnings:
                if learning.learning_type not in _INSIGHT_ELIGIBLE_TYPES:
                    continue
                candidates.append(self._to_insight(learning, score, memory_id))

        candidates.sort(key=lambda insight: (-insight.relevance_score, str(insight.insight_id)))
        return candidates[:insight_limit]

    def _to_insight(
        self, learning: MemoryLearning, score: SimilarityScore, memory_id: UUID
    ) -> HistoricalInsight:
        related_variable = None
        # A learning's own related_* id lists reference the SOURCE decision's
        # own assumptions/thresholds - this module never re-derives a
        # variable name from them (that would require an extra lookup per
        # learning); instead it uses the same, already-computed
        # decision-level relevance and leaves related_variable unset unless
        # a future enhancement threads the variable name through
        # MemoryLearning itself. Kept explicit (None) rather than guessed.
        return HistoricalInsight(
            insight_id=self._insight_id_for(score.decision_id, learning.learning_id),
            source_decision_id=score.decision_id,
            source_memory_id=memory_id,
            learning_id=learning.learning_id,
            statement=learning.statement,
            relevance_score=score.score,
            relevance_reason=score.explanation,
            learning_type=learning.learning_type,
            source_type=learning.source_type,
            observed_value=learning.observed_value,
            expected_value=learning.expected_value,
            related_variable=related_variable,
            confidence=learning.confidence,
            created_at=learning.created_at,
        )

    @staticmethod
    def _memory_id_for(learnings: list[MemoryLearning]) -> UUID:
        """Every learning for a decision shares the same memory_id (see
        `MemoryService`) - read it off the first one, or fall back to a
        deterministic placeholder derived from an empty list (never
        reached in practice, since `_collect_insights` only calls this
        when learnings is non-empty, but kept total rather than partial)."""
        if learnings:
            return learnings[0].memory_id
        return uuid5(_INSIGHT_ID_NAMESPACE, "no-memory")

    @staticmethod
    def _insight_id_for(source_decision_id: UUID, learning_id: UUID) -> UUID:
        """Deterministic insight id from (source_decision_id, learning_id) -
        stable across repeated calls for the same underlying learning,
        exactly one insight per learning, never a fresh uuid4 per request."""
        return uuid5(_INSIGHT_ID_NAMESPACE, f"insight:{source_decision_id}:{learning_id}")

    @staticmethod
    def _recurring_variables(insights: list[HistoricalInsight]) -> list[str]:
        """Variables that show up in more than one insight's statement text.

        Deliberately conservative: only counts a variable as "recurring"
        when its own related_variable was actually set on at least two
        insights - never inferred by parsing statement text, which would
        risk a false, fabricated pattern.
        """
        counts: dict[str, int] = {}
        for insight in insights:
            if insight.related_variable:
                counts[insight.related_variable] = counts.get(insight.related_variable, 0) + 1
        return sorted(variable for variable, count in counts.items() if count >= 2)

    @staticmethod
    def _unresolved_patterns(relevant: list[SimilarityScore]) -> list[str]:
        """Left empty by default - populated only when a future enhancement
        threads `unresolved_uncertainty`-type learnings through with real,
        non-fabricated pattern detection. Kept as an explicit, typed field
        on `HistoricalContext` (per the Step 19 spec's required shape)
        rather than omitted, so the response shape is stable even though
        this aggregate is conservatively empty today rather than guessing
        at a "pattern" from a single occurrence.
        """
        _ = relevant  # Reserved for a future, non-fabricated pattern signal.
        return []
