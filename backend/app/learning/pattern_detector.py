"""Deterministic recurring-pattern detection (REGRET ENGINE 2.0, Step 23).

No LLM call happens anywhere in this module. Every function here takes
plain, already-persisted records for ONE user's own decisions
(`DecisionSignals` bundles the module docstring below explains) and
groups real observations by a deterministic normalized key (see
`app.learning.normalization`) - never a semantic/embedding-based guess.

MINIMUM EVIDENCE POLICY (spec section 5):

    1 occurrence  -> no pattern at all (never returned as a candidate)
    2 occurrences -> PatternStatus.EMERGING (or REPEATED if genuinely
                     consistent - see `compute_status`)
    3+ occurrences, consistent -> PatternStatus.ESTABLISHED
    contradictory occurrences -> confidence lowered, status downgraded
                                  toward CONTRADICTED

These are heuristics, never statistical significance tests - nothing in
this module computes or claims a p-value, confidence interval, or
percentage likelihood.

CONFLICT HANDLING (spec section 18): a pattern's `supporting`/
`contradicting` occurrence counts are tracked separately and both
surfaced - three assumption outcomes split 2-supported/1-contradicted
never collapse into one unqualified claim.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from app.learning.normalization import normalize_experiment_type, normalize_variable
from app.learning.schemas import (
    OccurrenceRelation,
    PatternConfidence,
    PatternStatus,
    PatternType,
)
from app.memory.memory_schemas import DecisionMemory, LearningType, MemoryLearning
from app.schemas.decision_resources import (
    Assumption,
    Blindspot,
    Experiment,
    ExperimentResult,
    ReEvaluation,
    Threshold,
)

# Deterministic namespace for pattern/occurrence ids - distinct from
# every other namespace already used in this codebase (memory learnings,
# adaptive states, evolution events), so an id collision across features
# is architecturally impossible, not just unlikely.
_PATTERN_NAMESPACE = uuid5(NAMESPACE_URL, "regret-engine:learning:pattern")
_OCCURRENCE_NAMESPACE = uuid5(NAMESPACE_URL, "regret-engine:learning:occurrence")

# spec section 5's exact policy, expressed as constants so the thresholds
# are named once rather than scattered as magic numbers.
_MIN_DECISIONS_FOR_ANY_PATTERN = 2
_MIN_DECISIONS_FOR_ESTABLISHED = 3

_VALIDATED_ASSUMPTION_TYPES = {LearningType.ASSUMPTION_VALIDATED}
_FAILED_ASSUMPTION_TYPES = {LearningType.ASSUMPTION_WEAKENED, LearningType.ASSUMPTION_FAILED}
_VALIDATED_THRESHOLD_TYPES = {LearningType.THRESHOLD_VALIDATED}
_FAILED_THRESHOLD_TYPES = {LearningType.THRESHOLD_FAILED}


@dataclass
class DecisionSignals:
    """Every real, already-persisted record needed to detect patterns
    for ONE decision - a plain data bundle the caller (see
    `app.learning.service.CrossDecisionLearningService`) assembles from
    the existing repositories. Nothing here is fetched by this module
    itself; `pattern_detector` never talks to DynamoDB."""

    decision_id: str
    assumptions: list[Assumption] = field(default_factory=list)
    blindspots: list[Blindspot] = field(default_factory=list)
    thresholds: list[Threshold] = field(default_factory=list)
    experiments: list[Experiment] = field(default_factory=list)
    experiment_results: list[ExperimentResult] = field(default_factory=list)
    reevaluations: list[ReEvaluation] = field(default_factory=list)
    learnings: list[MemoryLearning] = field(default_factory=list)
    memory: DecisionMemory | None = None


@dataclass
class CandidateOccurrence:
    """One real observation contributing to a pattern candidate - always
    traceable to a real record via `source_type`/`source_id`."""

    decision_id: str
    source_type: str
    source_id: str
    observation: str
    observed_at: datetime
    relation: OccurrenceRelation
    confidence: float
    learning_id: str | None = None


@dataclass
class PatternCandidate:
    """A candidate recurring pattern, already grouped and evidence-
    scored, ready for the service layer to validate against the minimum
    evidence policy and persist. Never yet a `CrossDecisionPattern` -
    that conversion (adding ids/timestamps) is `service.py`'s job."""

    pattern_type: PatternType
    normalized_key: str
    variable: str | None
    title: str
    statement: str
    occurrences: list[CandidateOccurrence]

    @property
    def supporting_occurrences(self) -> list[CandidateOccurrence]:
        return [
            o
            for o in self.occurrences
            if o.relation in (OccurrenceRelation.SUPPORTS, OccurrenceRelation.PARTIALLY_SUPPORTS)
        ]

    @property
    def contradicting_occurrences(self) -> list[CandidateOccurrence]:
        return [o for o in self.occurrences if o.relation == OccurrenceRelation.CONTRADICTS]

    @property
    def supporting_decision_ids(self) -> list[str]:
        seen: list[str] = []
        for occurrence in self.supporting_occurrences:
            if occurrence.decision_id not in seen:
                seen.append(occurrence.decision_id)
        return seen

    @property
    def contradicting_decision_ids(self) -> list[str]:
        seen: list[str] = []
        for occurrence in self.contradicting_occurrences:
            if occurrence.decision_id not in seen:
                seen.append(occurrence.decision_id)
        return seen


def deterministic_pattern_id(user_id: str, pattern_type: PatternType, normalized_key: str) -> str:
    """Same user + same recurring concept always upserts the SAME
    record - see `app.learning.repository`'s module docstring for why
    this is what makes `refresh_patterns` idempotent."""
    return str(uuid5(_PATTERN_NAMESPACE, f"{user_id}:{pattern_type.value}:{normalized_key}"))


def deterministic_occurrence_id(
    pattern_id: str, decision_id: str, source_type: str, source_id: str
) -> str:
    """Same real evidence for the same pattern always upserts the SAME
    occurrence record - re-detecting identical evidence on refresh never
    creates a duplicate provenance row."""
    return str(
        uuid5(_OCCURRENCE_NAMESPACE, f"{pattern_id}:{decision_id}:{source_type}:{source_id}")
    )


def compute_status(
    supporting_count: int, contradicting_count: int, total_decisions: int
) -> PatternStatus:
    """Deterministic lifecycle status - spec section 19's exact
    progression: 1 occurrence never reaches this function at all (the
    caller filters those out before status is ever computed); 2 total
    decisions -> EMERGING/REPEATED; 3+ genuinely consistent decisions ->
    ESTABLISHED; meaningful contradicting evidence -> CONTRADICTED,
    never silently absorbed into a confident claim.
    """
    if contradicting_count > 0 and contradicting_count >= supporting_count:
        return PatternStatus.CONTRADICTED
    if total_decisions >= _MIN_DECISIONS_FOR_ESTABLISHED and contradicting_count == 0:
        return PatternStatus.ESTABLISHED
    if total_decisions >= _MIN_DECISIONS_FOR_ESTABLISHED:
        # Established evidence volume, but with SOME contradiction -
        # real, but not yet "established" without qualification.
        return PatternStatus.REPEATED
    return PatternStatus.EMERGING


def compute_confidence(
    supporting_count: int,
    contradicting_count: int,
    observed_result_count: int,
    total_occurrence_count: int,
) -> tuple[PatternConfidence, str]:
    """Evidence-based confidence band plus a plain-language basis -
    NEVER a fabricated percentage (spec section 6). Weighs:

    - how many supporting vs contradicting decisions exist (consistency)
    - how much of the evidence comes from OBSERVED results (experiment
      results / re-evaluations) rather than speculative analysis alone -
      spec section 7's evidence hierarchy: observed results outrank
      memory learnings derived only from analysis-time assumptions.
    """
    if total_occurrence_count == 0:
        return PatternConfidence.LOW, "No supporting evidence."

    contradiction_ratio = contradicting_count / max(supporting_count + contradicting_count, 1)
    observed_ratio = observed_result_count / total_occurrence_count

    if contradicting_count > 0 and contradiction_ratio >= 0.5:
        return (
            PatternConfidence.LOW,
            f"{contradicting_count} of {supporting_count + contradicting_count} observations "
            "contradict this pattern, so confidence is low despite the supporting evidence.",
        )

    if (
        supporting_count >= _MIN_DECISIONS_FOR_ESTABLISHED
        and observed_ratio >= 0.5
        and contradicting_count == 0
    ):
        return (
            PatternConfidence.HIGH,
            f"{supporting_count} independent decisions support this pattern with no "
            f"contradicting evidence, and {round(observed_ratio * 100)}% of the evidence comes "
            "from observed experiment results or re-evaluations rather than analysis alone.",
        )

    if supporting_count >= _MIN_DECISIONS_FOR_ANY_PATTERN:
        basis = f"{supporting_count} decisions support this pattern"
        if contradicting_count > 0:
            basis += f", with {contradicting_count} contradicting."
        else:
            basis += "."
        return PatternConfidence.MEDIUM, basis

    return PatternConfidence.LOW, "Not yet enough independent decisions to raise confidence."


def _resolve_variable_for_assumption(assumption: Assumption, thresholds: list[Threshold]) -> str:
    """Prefer the REAL, structured `Threshold.variable` linked to this
    assumption (via the threshold's own `related_assumption_ids`) over
    the assumption's free-text statement - a threshold's variable name
    is consistently phrased ("Repeat-order rate"), while raw assumption
    sentences vary in wording per-decision (spec section 3's own worked
    example: "Users will return frequently" vs "Customers will make
    repeat purchases" share no common tokens). This is the "prefer
    exact/structured matches first" rule in practice: falling back to
    the raw statement only when no structured link exists means two
    differently-phrased-but-conceptually-related assumptions are NOT
    merged unless the underlying structured data actually connects them
    - a documented, deliberate limitation, never a silent guess.
    """
    for threshold in thresholds:
        if str(assumption.id) in threshold.related_assumption_ids:
            return threshold.variable
    return assumption.statement


def _resolve_variable_for_threshold_id(
    threshold_id: str, thresholds: list[Threshold]
) -> str | None:
    for threshold in thresholds:
        if str(threshold.id) == threshold_id:
            return threshold.variable
    return None


def _resolve_experiment_type_for_result(
    result: ExperimentResult, experiments: list[Experiment]
) -> str | None:
    for experiment in experiments:
        if str(experiment.id) == str(result.experiment_id):
            return experiment.experiment_type
    return None


def _pick_dominant_and_contradicting(
    supporting_by_key: dict[str, list[tuple[str, CandidateOccurrence]]],
    contradicting_by_key: dict[str, list[tuple[str, CandidateOccurrence]]],
) -> dict[str, tuple[str, list[CandidateOccurrence]]]:
    """For each normalized key, decides which of two opposing pattern
    types (e.g. validated vs failed) is the DOMINANT direction - the one
    with strictly more supporting occurrences - and folds the opposite
    direction's occurrences in as CONTRADICTS on the dominant pattern.

    This is exactly spec section 18's conflict-handling requirement in
    code: three observations split 2-validated/1-failed become ONE
    pattern (validated, since it's dominant) with 2 supporting and 1
    contradicting occurrence - never two competing "half" patterns and
    never a collapsed, unqualified "always validated" claim.
    """
    all_keys = set(supporting_by_key) | set(contradicting_by_key)
    result: dict[str, tuple[str, list[CandidateOccurrence]]] = {}

    for key in all_keys:
        supporting = supporting_by_key.get(key, [])
        contradicting = contradicting_by_key.get(key, [])
        # `variable` in each tuple element is the SAME across all
        # entries for a key by construction; take it from whichever
        # side is non-empty.
        variable = (supporting or contradicting)[0][0]

        support_occurrences = [occ for _, occ in supporting]
        contradiction_occurrences = [
            CandidateOccurrence(
                decision_id=occ.decision_id,
                source_type=occ.source_type,
                source_id=occ.source_id,
                observation=occ.observation,
                observed_at=occ.observed_at,
                relation=OccurrenceRelation.CONTRADICTS,
                confidence=occ.confidence,
                learning_id=occ.learning_id,
            )
            for _, occ in contradicting
        ]

        if len(support_occurrences) >= len(contradiction_occurrences):
            result[key] = (variable, support_occurrences + contradiction_occurrences)
        else:
            # The "failed"/opposite side is actually dominant - flip
            # roles: what was CONTRADICTS becomes SUPPORTS and vice
            # versa, still on the SAME key, just under the other
            # pattern_type at the call site.
            flipped_support = [
                CandidateOccurrence(
                    decision_id=occ.decision_id,
                    source_type=occ.source_type,
                    source_id=occ.source_id,
                    observation=occ.observation,
                    observed_at=occ.observed_at,
                    relation=OccurrenceRelation.SUPPORTS,
                    confidence=occ.confidence,
                    learning_id=occ.learning_id,
                )
                for _, occ in contradicting
            ]
            flipped_contradict = [
                CandidateOccurrence(
                    decision_id=occ.decision_id,
                    source_type=occ.source_type,
                    source_id=occ.source_id,
                    observation=occ.observation,
                    observed_at=occ.observed_at,
                    relation=OccurrenceRelation.CONTRADICTS,
                    confidence=occ.confidence,
                    learning_id=occ.learning_id,
                )
                for _, occ in supporting
            ]
            result[f"__flip__{key}"] = (variable, flipped_support + flipped_contradict)

    return result


def _detect_assumption_outcome_patterns(
    signals: list[DecisionSignals],
) -> tuple[list[PatternCandidate], list[PatternCandidate]]:
    """Returns `(validated_candidates, failed_candidates)` - both lists
    are built from the SAME grouping pass so contradictions are folded
    correctly (see `_pick_dominant_and_contradicting`)."""
    validated: dict[str, list[tuple[str, CandidateOccurrence]]] = defaultdict(list)
    failed: dict[str, list[tuple[str, CandidateOccurrence]]] = defaultdict(list)

    for bundle in signals:
        for learning in bundle.learnings:
            if learning.learning_type not in _VALIDATED_ASSUMPTION_TYPES | _FAILED_ASSUMPTION_TYPES:
                continue
            if not learning.related_assumption_ids:
                continue
            assumption_id = learning.related_assumption_ids[0]
            assumption = next((a for a in bundle.assumptions if str(a.id) == assumption_id), None)
            if assumption is None:
                continue
            variable = _resolve_variable_for_assumption(assumption, bundle.thresholds)
            key = normalize_variable(variable)
            if key is None:
                continue

            occurrence = CandidateOccurrence(
                decision_id=bundle.decision_id,
                source_type="memory_learning",
                source_id=str(learning.learning_id),
                observation=learning.statement,
                observed_at=learning.created_at,
                relation=OccurrenceRelation.SUPPORTS,
                confidence=learning.confidence if learning.confidence is not None else 0.5,
                learning_id=str(learning.learning_id),
            )
            if learning.learning_type in _VALIDATED_ASSUMPTION_TYPES:
                validated[key].append((variable, occurrence))
            else:
                failed[key].append((variable, occurrence))

    resolved = _pick_dominant_and_contradicting(validated, failed)

    validated_candidates: list[PatternCandidate] = []
    failed_candidates: list[PatternCandidate] = []
    for key, (variable, occurrences) in resolved.items():
        real_key = key.removeprefix("__flip__")
        is_flipped = key.startswith("__flip__")
        # Non-flipped entries came from the `validated` dict winning;
        # flipped entries came from `failed` winning.
        if not is_flipped:
            validated_candidates.append(
                PatternCandidate(
                    pattern_type=PatternType.RECURRING_VALIDATED_ASSUMPTION,
                    normalized_key=real_key,
                    variable=variable,
                    title=f"{variable} has repeatedly been validated.",
                    statement=f"In your past decisions, the assumption around '{variable}' has "
                    "repeatedly held up against real experiment results.",
                    occurrences=occurrences,
                )
            )
        else:
            failed_candidates.append(
                PatternCandidate(
                    pattern_type=PatternType.RECURRING_FAILED_ASSUMPTION,
                    normalized_key=real_key,
                    variable=variable,
                    title=f"{variable} has repeatedly underperformed.",
                    statement=f"In your past decisions, the assumption around '{variable}' has "
                    "repeatedly been weaker than expected once tested.",
                    occurrences=occurrences,
                )
            )

    return validated_candidates, failed_candidates


def _detect_threshold_outcome_patterns(
    signals: list[DecisionSignals],
) -> tuple[list[PatternCandidate], list[PatternCandidate]]:
    validated: dict[str, list[tuple[str, CandidateOccurrence]]] = defaultdict(list)
    failed: dict[str, list[tuple[str, CandidateOccurrence]]] = defaultdict(list)

    for bundle in signals:
        for learning in bundle.learnings:
            if learning.learning_type not in _VALIDATED_THRESHOLD_TYPES | _FAILED_THRESHOLD_TYPES:
                continue
            if not learning.related_threshold_ids:
                continue
            threshold_id = learning.related_threshold_ids[0]
            variable = _resolve_variable_for_threshold_id(threshold_id, bundle.thresholds)
            if variable is None:
                continue
            key = normalize_variable(variable)
            if key is None:
                continue

            occurrence = CandidateOccurrence(
                decision_id=bundle.decision_id,
                source_type="memory_learning",
                source_id=str(learning.learning_id),
                observation=learning.statement,
                observed_at=learning.created_at,
                relation=OccurrenceRelation.SUPPORTS,
                confidence=learning.confidence if learning.confidence is not None else 0.6,
                learning_id=str(learning.learning_id),
            )
            if learning.learning_type in _VALIDATED_THRESHOLD_TYPES:
                validated[key].append((variable, occurrence))
            else:
                failed[key].append((variable, occurrence))

    resolved = _pick_dominant_and_contradicting(validated, failed)

    validated_candidates: list[PatternCandidate] = []
    failed_candidates: list[PatternCandidate] = []
    for key, (variable, occurrences) in resolved.items():
        real_key = key.removeprefix("__flip__")
        is_flipped = key.startswith("__flip__")
        if not is_flipped:
            validated_candidates.append(
                PatternCandidate(
                    pattern_type=PatternType.RECURRING_THRESHOLD_VALIDATION,
                    normalized_key=real_key,
                    variable=variable,
                    title=f"{variable} has repeatedly met its threshold.",
                    statement=f"In your past decisions, the threshold for '{variable}' has "
                    "repeatedly been met by observed results.",
                    occurrences=occurrences,
                )
            )
        else:
            failed_candidates.append(
                PatternCandidate(
                    pattern_type=PatternType.RECURRING_THRESHOLD_FAILURE,
                    normalized_key=real_key,
                    variable=variable,
                    title=f"{variable} has repeatedly missed its threshold.",
                    statement=f"In your past decisions, the threshold for '{variable}' has "
                    "repeatedly underperformed relative to what was required - this is not a "
                    "claim that it will always fail, only that it has so far.",
                    occurrences=occurrences,
                )
            )

    return validated_candidates, failed_candidates


def _detect_experiment_learning_patterns(signals: list[DecisionSignals]) -> list[PatternCandidate]:
    """Recurring experiment TYPES that repeatedly produced useful
    evidence (`LearningType.EXPERIMENT_LEARNING`) - a tally, not a
    validated/failed binary, so there is no contradiction concept here:
    every occurrence simply SUPPORTS the observation that this
    experiment type has been informative before."""
    grouped: dict[str, list[tuple[str, CandidateOccurrence]]] = defaultdict(list)

    for bundle in signals:
        results_by_id = {str(r.id): r for r in bundle.experiment_results}
        for learning in bundle.learnings:
            if learning.learning_type != LearningType.EXPERIMENT_LEARNING:
                continue
            if learning.source_type.value != "experiment_result":
                continue
            result = results_by_id.get(str(learning.source_id))
            if result is None:
                continue
            experiment_type = _resolve_experiment_type_for_result(result, bundle.experiments)
            key = normalize_experiment_type(experiment_type)
            if key is None or experiment_type is None:
                continue

            occurrence = CandidateOccurrence(
                decision_id=bundle.decision_id,
                source_type="memory_learning",
                source_id=str(learning.learning_id),
                observation=learning.statement,
                observed_at=learning.created_at,
                relation=OccurrenceRelation.SUPPORTS,
                confidence=learning.confidence if learning.confidence is not None else 0.5,
                learning_id=str(learning.learning_id),
            )
            grouped[key].append((experiment_type, occurrence))

    candidates: list[PatternCandidate] = []
    for key, entries in grouped.items():
        variable = entries[0][0]
        occurrences = [occ for _, occ in entries]
        candidates.append(
            PatternCandidate(
                pattern_type=PatternType.RECURRING_EXPERIMENT_LEARNING,
                normalized_key=key,
                variable=variable,
                title=f"{variable} experiments have repeatedly produced useful evidence.",
                statement=f"In your past decisions, '{variable}'-type experiments have "
                "repeatedly reduced uncertainty - this is a pattern in what has worked for "
                "you, not a claim that this experiment type is statistically superior.",
                occurrences=occurrences,
            )
        )
    return candidates


def _detect_experiment_outcome_patterns(signals: list[DecisionSignals]) -> list[PatternCandidate]:
    """Recurring experiment TYPES grouped by their own real `outcome`
    (success/failure) - separate from `_detect_experiment_learning_patterns`,
    which looks at whether the learning was INFORMATIVE, not whether the
    experiment itself succeeded or failed."""
    success: dict[str, list[tuple[str, CandidateOccurrence]]] = defaultdict(list)
    failure: dict[str, list[tuple[str, CandidateOccurrence]]] = defaultdict(list)

    for bundle in signals:
        for result in bundle.experiment_results:
            experiment_type = _resolve_experiment_type_for_result(result, bundle.experiments)
            key = normalize_experiment_type(experiment_type)
            if key is None or experiment_type is None:
                continue
            if result.outcome.value not in {"success", "failure"}:
                continue

            occurrence = CandidateOccurrence(
                decision_id=bundle.decision_id,
                source_type="experiment_result",
                source_id=str(result.id),
                observation=result.summary,
                observed_at=result.completed_at,
                relation=OccurrenceRelation.SUPPORTS,
                confidence=0.7,
            )
            if result.outcome.value == "success":
                success[key].append((experiment_type, occurrence))
            else:
                failure[key].append((experiment_type, occurrence))

    candidates: list[PatternCandidate] = []
    for key, entries in success.items():
        variable = entries[0][0]
        candidates.append(
            PatternCandidate(
                pattern_type=PatternType.RECURRING_EXPERIMENT_SUCCESS,
                normalized_key=key,
                variable=variable,
                title=f"{variable} experiments have repeatedly succeeded.",
                statement=f"In your past decisions, '{variable}'-type experiments have "
                "repeatedly succeeded.",
                occurrences=[occ for _, occ in entries],
            )
        )
    for key, entries in failure.items():
        variable = entries[0][0]
        candidates.append(
            PatternCandidate(
                pattern_type=PatternType.RECURRING_EXPERIMENT_FAILURE,
                normalized_key=key,
                variable=variable,
                title=f"{variable} experiments have repeatedly failed.",
                statement=f"In your past decisions, '{variable}'-type experiments have "
                "repeatedly failed to confirm the hypothesis being tested.",
                occurrences=[occ for _, occ in entries],
            )
        )
    return candidates


def _detect_unexpected_result_patterns(signals: list[DecisionSignals]) -> list[PatternCandidate]:
    grouped: dict[str, list[tuple[str, CandidateOccurrence]]] = defaultdict(list)

    for bundle in signals:
        for learning in bundle.learnings:
            if learning.learning_type != LearningType.UNEXPECTED_RESULT:
                continue
            variable: str | None = None
            if learning.related_threshold_ids:
                variable = _resolve_variable_for_threshold_id(
                    learning.related_threshold_ids[0], bundle.thresholds
                )
            key = normalize_variable(variable) if variable else None
            if key is None:
                continue

            occurrence = CandidateOccurrence(
                decision_id=bundle.decision_id,
                source_type="memory_learning",
                source_id=str(learning.learning_id),
                observation=learning.statement,
                observed_at=learning.created_at,
                relation=OccurrenceRelation.SUPPORTS,
                confidence=learning.confidence if learning.confidence is not None else 0.5,
                learning_id=str(learning.learning_id),
            )
            grouped[key].append((variable, occurrence))

    candidates: list[PatternCandidate] = []
    for key, entries in grouped.items():
        variable = entries[0][0]
        candidates.append(
            PatternCandidate(
                pattern_type=PatternType.RECURRING_UNEXPECTED_RESULT,
                normalized_key=key,
                variable=variable,
                title=f"{variable} has repeatedly produced unexpected results.",
                statement=f"In your past decisions, results around '{variable}' have "
                "repeatedly surprised the original analysis.",
                occurrences=[occ for _, occ in entries],
            )
        )
    return candidates


def _detect_unresolved_uncertainty_patterns(
    signals: list[DecisionSignals],
) -> list[PatternCandidate]:
    """Assumptions that remain untested/unaddressed across multiple
    decisions - normalized by the assumption's own statement text (no
    threshold link exists yet, by definition, since it's unresolved).
    Distinguishes `RECURRING_UNRESOLVED_QUESTION` (never tested in ANY
    occurrence) from `RECURRING_UNCERTAINTY` (recurring, but has been
    tested at least once elsewhere) - spec section 4E."""
    _UNRESOLVED_ASSUMPTION_STATUSES = {"not_addressed", "unverified"}
    grouped: dict[str, list[tuple[str, CandidateOccurrence, bool]]] = defaultdict(list)

    for bundle in signals:
        resolved_assumption_ids = {
            learning.related_assumption_ids[0]
            for learning in bundle.learnings
            if learning.related_assumption_ids
            and learning.learning_type in _VALIDATED_ASSUMPTION_TYPES | _FAILED_ASSUMPTION_TYPES
        }
        for assumption in bundle.assumptions:
            if assumption.evidence_status.value not in _UNRESOLVED_ASSUMPTION_STATUSES:
                continue
            key = normalize_variable(assumption.statement)
            if key is None:
                continue
            was_tested_here = str(assumption.id) in resolved_assumption_ids

            occurrence = CandidateOccurrence(
                decision_id=bundle.decision_id,
                source_type="assumption",
                source_id=str(assumption.id),
                observation=assumption.statement,
                observed_at=assumption.created_at,
                relation=OccurrenceRelation.SUPPORTS,
                confidence=0.4,
            )
            grouped[key].append((assumption.statement, occurrence, was_tested_here))

    candidates: list[PatternCandidate] = []
    for key, entries in grouped.items():
        variable = entries[0][0]
        occurrences = [occ for _, occ, _ in entries]
        ever_tested = any(tested for _, _, tested in entries)
        pattern_type = (
            PatternType.RECURRING_UNCERTAINTY
            if ever_tested
            else PatternType.RECURRING_UNRESOLVED_QUESTION
        )
        title = (
            f"'{variable}' remains a recurring unresolved question."
            if not ever_tested
            else f"You repeatedly encounter unresolved uncertainty around '{variable}'."
        )
        candidates.append(
            PatternCandidate(
                pattern_type=pattern_type,
                normalized_key=key,
                variable=variable,
                title=title,
                statement=f"Across your past decisions, '{variable}' has repeatedly appeared "
                "as an unresolved uncertainty"
                + (
                    "."
                    if not ever_tested
                    else " - it has been tested at least once, but "
                    "keeps recurring in later decisions."
                ),
                occurrences=occurrences,
            )
        )
    return candidates


def detect_patterns(signals: list[DecisionSignals]) -> list[PatternCandidate]:
    """Runs every deterministic detection rule over one user's own
    decision signals and returns every candidate with at least
    `_MIN_DECISIONS_FOR_ANY_PATTERN` distinct supporting decisions -
    weaker candidates (a single decision's worth of evidence) are
    dropped here, before the service layer ever sees them, per spec
    section 5's explicit "1 occurrence -> no pattern" rule.
    """
    candidates: list[PatternCandidate] = []

    validated_assumptions, failed_assumptions = _detect_assumption_outcome_patterns(signals)
    candidates.extend(validated_assumptions)
    candidates.extend(failed_assumptions)

    validated_thresholds, failed_thresholds = _detect_threshold_outcome_patterns(signals)
    candidates.extend(validated_thresholds)
    candidates.extend(failed_thresholds)

    candidates.extend(_detect_experiment_learning_patterns(signals))
    candidates.extend(_detect_experiment_outcome_patterns(signals))
    candidates.extend(_detect_unexpected_result_patterns(signals))
    candidates.extend(_detect_unresolved_uncertainty_patterns(signals))

    return [
        candidate
        for candidate in candidates
        if len(set(o.decision_id for o in candidate.occurrences)) >= _MIN_DECISIONS_FOR_ANY_PATTERN
    ]
