"""Cross-Decision Learning orchestration (REGRET ENGINE 2.0, Step 23).

`CrossDecisionLearningService.refresh_patterns` is the one operation that
actually (re)computes patterns - it is NEVER invoked automatically on
every read (spec section 11: "do not run this automatically on every API
request"). Reads (`list_patterns_for_user`, `get_pattern`,
`get_patterns_for_decision`) only ever return what the last refresh
already persisted.

No LLM call happens anywhere in this module. Every historical record this
service reads already exists because of Steps 18-22
(`DecisionRepository`, `MemoryRepository`) - this module adds no new
canonical data, only a derived, explainable summary of recurring
observations across it.

USER ISOLATION: every public method requires `user_id` and every
downstream repository/detector call is scoped to it - see
`app.learning.repository`'s own module docstring for how the DynamoDB
partition key itself enforces this.
"""

from datetime import UTC, datetime
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger
from app.learning.normalization import normalize_variable
from app.learning.pattern_detector import (
    DecisionSignals,
    PatternCandidate,
    compute_confidence,
    compute_status,
    detect_patterns,
    deterministic_occurrence_id,
    deterministic_pattern_id,
)
from app.learning.repository import CrossDecisionLearningRepository
from app.learning.schemas import (
    CrossDecisionPattern,
    CrossDecisionPatternDetail,
    HistoricalLearningSignal,
    OccurrenceRelation,
    PatternOccurrence,
    PatternRefreshResponse,
    PatternStatus,
)
from app.memory.memory_repository import MemoryRepository
from app.repositories.decision_repository import DecisionRepository

logger = get_logger(__name__)

# Patterns whose very existence signals "this uncertainty is worth
# testing early" - a failed/underperforming history, or a recurring
# unresolved question, both raise the historical-learning signal fed to
# VOI (spec section 14). A validated/successful history LOWERS the
# signal (there's less new information to gain from testing it again).
_RAISES_SIGNAL_PATTERN_TYPES = {
    "recurring_failed_assumption",
    "recurring_threshold_failure",
    "recurring_unresolved_question",
    "recurring_uncertainty",
    "recurring_unexpected_result",
}
_LOWERS_SIGNAL_PATTERN_TYPES = {
    "recurring_validated_assumption",
    "recurring_threshold_validation",
}


class CrossDecisionLearningService:
    """Detects, persists, and explains recurring patterns across ONE
    user's own completed decisions."""

    def __init__(
        self,
        decision_repository: DecisionRepository,
        memory_repository: MemoryRepository,
        learning_repository: CrossDecisionLearningRepository,
    ) -> None:
        self._decisions = decision_repository
        self._memory = memory_repository
        self._learning = learning_repository

    # --- reads (never trigger detection) ------------------------------------

    def list_patterns_for_user(
        self,
        user_id: str,
        pattern_type: str | None = None,
        status: str | None = None,
        domain: str | None = None,
        variable: str | None = None,
    ) -> list[CrossDecisionPattern]:
        return self._learning.list_patterns_for_user(
            user_id, pattern_type=pattern_type, status=status, domain=domain, variable=variable
        )

    def get_pattern(self, user_id: str, pattern_id: str) -> CrossDecisionPattern | None:
        return self._learning.get_pattern(user_id, pattern_id)

    def get_pattern_detail(
        self, user_id: str, pattern_id: str
    ) -> CrossDecisionPatternDetail | None:
        pattern = self._learning.get_pattern(user_id, pattern_id)
        if pattern is None:
            return None
        occurrences = self._learning.list_pattern_occurrences(user_id, pattern_id)
        return CrossDecisionPatternDetail(
            pattern=pattern,
            occurrences=occurrences,
            supporting_occurrences=[
                o
                for o in occurrences
                if o.relation
                in (OccurrenceRelation.SUPPORTS, OccurrenceRelation.PARTIALLY_SUPPORTS)
            ],
            contradicting_occurrences=[
                o for o in occurrences if o.relation == OccurrenceRelation.CONTRADICTS
            ],
        )

    def get_patterns_for_decision(
        self, user_id: str, decision_id: UUID
    ) -> list[CrossDecisionPattern]:
        return self._learning.get_patterns_for_decision(user_id, str(decision_id))

    # --- signal for VOI / Experiment Planner (spec sections 14-15) ---------

    def historical_learning_signal_for_variable(
        self, user_id: str, variable: str | None
    ) -> tuple[HistoricalLearningSignal, str]:
        """How strongly the user's OWN cross-decision history bears on
        one variable - a tiebreaker-strength signal for VOI, never
        something that overrides current evidence (spec section 14: "an
        input to the existing explainable VOI ranking", never authority).

        Returns `(HistoricalLearningSignal.NONE, "")` whenever there is
        no real pattern for this variable - never a fabricated signal.
        """
        key = normalize_variable(variable)
        if key is None:
            return HistoricalLearningSignal.NONE, ""

        patterns = [
            p
            for p in self._learning.list_patterns_for_user(user_id, variable=variable)
            if p.normalized_key == key
        ]
        if not patterns:
            return HistoricalLearningSignal.NONE, ""

        raising = [p for p in patterns if p.pattern_type.value in _RAISES_SIGNAL_PATTERN_TYPES]
        lowering = [p for p in patterns if p.pattern_type.value in _LOWERS_SIGNAL_PATTERN_TYPES]

        if raising:
            strongest = max(raising, key=lambda p: p.occurrence_count)
            if strongest.status == PatternStatus.ESTABLISHED:
                return (
                    HistoricalLearningSignal.STRONG,
                    f"{strongest.title} ({strongest.occurrence_count} past decisions).",
                )
            return (
                HistoricalLearningSignal.MODERATE,
                f"{strongest.title} ({strongest.occurrence_count} past decisions).",
            )

        if lowering:
            strongest = max(lowering, key=lambda p: p.occurrence_count)
            return (
                HistoricalLearningSignal.WEAK,
                f"{strongest.title} - already well-understood from past decisions.",
            )

        return HistoricalLearningSignal.NONE, ""

    # --- refresh (the only operation that (re)computes patterns) -----------

    def refresh_patterns(self, user_id: str) -> PatternRefreshResponse:
        """Rebuilds every cross-decision pattern for one user from their
        current canonical records. Idempotent: re-running with no new
        evidence produces the exact same patterns/occurrences (same
        deterministic ids), reported as `patterns_unchanged` rather than
        `patterns_created`/`patterns_updated`.

        Bounded: only the user's own most recent
        `settings.learning_max_decisions_scanned` decisions are loaded -
        never an unbounded scan of a user's entire history, mirroring
        the same "prevent runaway" bounding pattern already used by
        `historical_search_limit` (Step 19) and `evolution_max_events`
        (Step 22).
        """
        settings = get_settings()
        signals = self._load_signals(user_id, settings.learning_max_decisions_scanned)
        candidates = detect_patterns(signals)

        existing_before = {p.pattern_id: p for p in self._learning.list_patterns_for_user(user_id)}

        created = 0
        updated = 0
        unchanged = 0
        seen_pattern_ids: set[str] = set()

        for candidate in candidates:
            pattern, occurrences = self._build_pattern(user_id, candidate)
            seen_pattern_ids.add(pattern.pattern_id)

            previous = existing_before.get(pattern.pattern_id)
            self._learning.delete_occurrences_for_pattern(user_id, pattern.pattern_id)
            for occurrence in occurrences:
                self._learning.upsert_occurrence(occurrence)

            if previous is None:
                pattern = pattern.model_copy(update={"first_seen_at": pattern.last_seen_at})
                self._learning.upsert_pattern(pattern)
                created += 1
            elif _pattern_content_changed(previous, pattern):
                pattern = pattern.model_copy(update={"first_seen_at": previous.first_seen_at})
                self._learning.upsert_pattern(pattern)
                updated += 1
            else:
                unchanged += 1

        # Patterns that existed before but no longer have qualifying
        # evidence this refresh (e.g. the only supporting decision was
        # deleted) are marked INACTIVE rather than deleted - spec section
        # 19: "do not delete historical patterns merely because they
        # become inactive. Preserve provenance."
        for pattern_id, previous in existing_before.items():
            if pattern_id in seen_pattern_ids or previous.status == PatternStatus.INACTIVE:
                continue
            inactive = previous.model_copy(
                update={"status": PatternStatus.INACTIVE, "updated_at": datetime.now(UTC)}
            )
            self._learning.upsert_pattern(inactive)
            updated += 1

        total = len(self._learning.list_patterns_for_user(user_id))
        return PatternRefreshResponse(
            user_id=user_id,
            patterns_created=created,
            patterns_updated=updated,
            patterns_unchanged=unchanged,
            total_patterns=total,
            refreshed_at=datetime.now(UTC),
        )

    # --- internal ------------------------------------------------------------

    def _load_signals(self, user_id: str, max_decisions: int) -> list[DecisionSignals]:
        """Bounded, paginated load of one user's own decisions and every
        canonical record `pattern_detector` needs from them - mirrors
        `HistoricalContextService._load_candidates`'s own bounded
        `list_for_user` usage exactly, so this never scans more of a
        user's history than the configured limit."""
        decisions, cursor = self._decisions.list_for_user(user_id, limit=max_decisions)
        # `list_for_user` itself already bounds to `limit` per page; a
        # single page is enough for the configured bound - no further
        # pagination is attempted here, since `max_decisions` IS the
        # intended ceiling on how much history one refresh considers.
        del cursor

        signals: list[DecisionSignals] = []
        for decision in decisions:
            decision_id = decision.id
            memory = self._first_or_none(self._memory.list_memory_for_decision(decision_id))
            signals.append(
                DecisionSignals(
                    decision_id=str(decision_id),
                    assumptions=self._decisions.list_assumptions(decision_id),
                    blindspots=self._decisions.list_blindspots(decision_id),
                    thresholds=self._decisions.list_thresholds(decision_id),
                    experiments=self._decisions.list_experiments(decision_id),
                    experiment_results=self._decisions.list_experiment_results(decision_id),
                    reevaluations=self._decisions.list_reevaluations(decision_id),
                    learnings=self._memory.list_learnings_for_decision(decision_id),
                    memory=memory,
                )
            )
        return signals

    @staticmethod
    def _first_or_none(items: list):
        return items[0] if items else None

    def _build_pattern(
        self, user_id: str, candidate: PatternCandidate
    ) -> tuple[CrossDecisionPattern, list[PatternOccurrence]]:
        pattern_id = deterministic_pattern_id(
            user_id, candidate.pattern_type, candidate.normalized_key
        )
        now = datetime.now(UTC)

        supporting_decision_ids = candidate.supporting_decision_ids
        contradicting_decision_ids = candidate.contradicting_decision_ids
        supporting_count = len(supporting_decision_ids)
        contradicting_count = len(contradicting_decision_ids)
        total_decisions = len(set(o.decision_id for o in candidate.occurrences))

        observed_source_types = {"experiment_result", "re_evaluation"}
        observed_count = sum(
            1 for o in candidate.occurrences if o.source_type in observed_source_types
        )

        status = compute_status(supporting_count, contradicting_count, total_decisions)
        confidence, confidence_basis = compute_confidence(
            supporting_count, contradicting_count, observed_count, len(candidate.occurrences)
        )

        occurrences_sorted = sorted(candidate.occurrences, key=lambda o: o.observed_at)
        first_seen = occurrences_sorted[0].observed_at
        last_seen = occurrences_sorted[-1].observed_at

        supporting_learning_ids = sorted(
            {
                o.learning_id
                for o in candidate.occurrences
                if o.learning_id is not None and o.relation != OccurrenceRelation.CONTRADICTS
            }
        )
        supporting_experiment_ids = sorted(
            {
                o.source_id
                for o in candidate.occurrences
                if o.source_type == "experiment_result"
                and o.relation != OccurrenceRelation.CONTRADICTS
            }
        )
        supporting_threshold_ids = sorted(
            {
                o.source_id
                for o in candidate.occurrences
                if o.source_type == "threshold" and o.relation != OccurrenceRelation.CONTRADICTS
            }
        )

        pattern = CrossDecisionPattern(
            pattern_id=pattern_id,
            user_id=user_id,
            pattern_type=candidate.pattern_type,
            title=candidate.title,
            statement=candidate.statement,
            normalized_key=candidate.normalized_key,
            variable=candidate.variable,
            domain=None,
            decision_types=[],
            occurrence_count=len(candidate.occurrences),
            supporting_decision_ids=supporting_decision_ids,
            supporting_learning_ids=supporting_learning_ids,
            supporting_experiment_ids=supporting_experiment_ids,
            supporting_threshold_ids=supporting_threshold_ids,
            contradicting_decision_ids=contradicting_decision_ids,
            evidence_count=len(candidate.occurrences),
            confidence=confidence,
            confidence_basis=confidence_basis,
            first_seen_at=first_seen,
            last_seen_at=last_seen,
            status=status,
            created_at=now,
            updated_at=now,
        )

        occurrences = [
            PatternOccurrence(
                occurrence_id=deterministic_occurrence_id(
                    pattern_id, occurrence.decision_id, occurrence.source_type, occurrence.source_id
                ),
                pattern_id=pattern_id,
                user_id=user_id,
                decision_id=occurrence.decision_id,
                learning_id=occurrence.learning_id,
                source_type=occurrence.source_type,
                source_id=occurrence.source_id,
                observation=occurrence.observation,
                observed_at=occurrence.observed_at,
                relation=occurrence.relation,
                confidence=occurrence.confidence,
            )
            for occurrence in candidate.occurrences
        ]

        return pattern, occurrences


def _pattern_content_changed(previous: CrossDecisionPattern, current: CrossDecisionPattern) -> bool:
    """Whether the SUBSTANCE of a pattern changed since the last refresh
    - never compares `created_at`/`updated_at` (which always differ),
    only the fields a user would actually notice."""
    return (
        previous.occurrence_count != current.occurrence_count
        or previous.status != current.status
        or previous.confidence != current.confidence
        or set(previous.supporting_decision_ids) != set(current.supporting_decision_ids)
        or set(previous.contradicting_decision_ids) != set(current.contradicting_decision_ids)
    )
