"""Decision Similarity scoring (REGRET ENGINE 2.0).

`DecisionSimilarityService` computes a deterministic, explainable
similarity score between the decision currently being analyzed and ONE of
the same user's own past decisions. This is intentionally NOT:

- vector/embedding-based (no vector DB, no semantic embedding model - see
  the Step 19 spec's explicit prohibition),
- LLM-judged (no model call is involved anywhere in this file),
- based only on exact string matching (see `_tokenize`/`_jaccard` below -
  matching is token-set overlap, not substring/equality checks alone).

Every score is a weighted sum of a small, fixed set of named features,
each independently computed in plain Python from real, already-persisted
fields - `Assumption`/`Threshold` records for the past decision (never
another user's), and the current decision's own raw text/constraint
fields (its own analysis may not exist yet - similarity runs BEFORE the
Decision Analyzer, see `app.agents.orchestrator`). `matched_features` and
`explanation` are built directly from those same components, so a caller
(or a user looking at the UI) can see exactly why two decisions were
considered similar - never a black-box number.

User-scoping is NOT enforced here - this module only ever compares two
`DecisionResponse`/`Assumption`/`Threshold` objects it is given. The
caller (`app.memory.historical_context.HistoricalContextService`) is
responsible for only ever passing in candidates already filtered to the
current decision's own `user_id` via `DecisionRepository.list_for_user`.
See that module's docstring for the actual ownership boundary.
"""

import re
from dataclasses import dataclass

from app.memory.similarity_schemas import SimilarityScore
from app.schemas.decision import DecisionResponse
from app.schemas.decision_resources import Assumption, Threshold

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

# A short, generic stopword list - just enough to keep near-universal
# filler words (articles, prepositions, common verbs) from dominating a
# token-overlap score. Deliberately NOT a full NLP stopword corpus; this
# stays a lightweight, dependency-free heuristic, not an NLP pipeline.
_STOPWORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "if", "then", "than", "so", "of", "to", "in",
        "on", "for", "with", "at", "by", "from", "as", "is", "are", "was", "were", "be",
        "been", "being", "this", "that", "these", "those", "it", "its", "i", "we", "you",
        "he", "she", "they", "my", "our", "your", "their", "not", "no", "do", "does", "did",
        "will", "would", "should", "could", "can", "may", "might", "must", "have", "has",
        "had", "about", "into", "over", "after", "before", "there", "here", "what", "which",
        "who", "whom", "how", "when", "where", "why",
    }
)

# Below this, a component's contribution is treated as noise rather than
# a genuine match - it never appears in `matched_features`/`explanation`,
# even though it still contributes its (small) weighted amount to `score`.
_MATCH_THRESHOLD = 0.15

# Feature weights, summing to 1.0. Named so `matched_features` entries and
# these weights always stay in lockstep - see `_FEATURE_NAMES` below.
_WEIGHT_TEXT_SIMILARITY = 0.35
_WEIGHT_ASSUMPTION_OVERLAP = 0.20
_WEIGHT_VARIABLE_OVERLAP = 0.15
_WEIGHT_BUDGET_SIMILARITY = 0.15
_WEIGHT_RISK_TOLERANCE_MATCH = 0.10
_WEIGHT_LOCATION_MATCH = 0.05


def _tokenize(text: str | None) -> set[str]:
    """Lowercase, alphanumeric-only tokenization with light stopword removal.

    Deliberately simple (no stemming, no lemmatization, no external NLP
    dependency) - this is a lightweight lexical overlap heuristic, not a
    semantic similarity model. Tokens shorter than 3 characters are
    dropped along with stopwords, to reduce noise from short connector
    words that survive the stopword list.
    """
    if not text:
        return set()
    return {
        token
        for token in _TOKEN_PATTERN.findall(text.lower())
        if token not in _STOPWORDS and len(token) >= 3
    }


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity: |intersection| / |union|, or 0.0 if either side is empty."""
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def _decision_text_tokens(decision: DecisionResponse) -> set[str]:
    """Every free-text field on a decision, combined into one token set.

    Includes `title`/`description`/`desired_outcome`/`beliefs` (the
    decision's own stated reasoning) and `timeline`/`location`/
    `risk_tolerance` (short descriptive fields) - deliberately NOT
    `budget`/`currency` (numeric/code fields handled by their own,
    separate feature below).
    """
    parts = [
        decision.title,
        decision.description,
        decision.desired_outcome,
        decision.beliefs,
        decision.timeline,
        decision.location,
        decision.risk_tolerance,
    ]
    tokens: set[str] = set()
    for part in parts:
        tokens |= _tokenize(part)
    return tokens


def _assumption_tokens(assumptions: list[Assumption]) -> set[str]:
    tokens: set[str] = set()
    for assumption in assumptions:
        tokens |= _tokenize(assumption.statement)
        tokens |= _tokenize(assumption.dependency)
        tokens |= _tokenize(assumption.failure_consequence)
    return tokens


def _variable_tokens(thresholds: list[Threshold]) -> set[str]:
    tokens: set[str] = set()
    for threshold in thresholds:
        tokens |= _tokenize(threshold.variable)
    return tokens


def _budget_similarity(current: float | None, past: float | None) -> float | None:
    """Relative closeness of two budgets in [0, 1], or `None` if either is missing.

    `None` (not 0.0) when a comparison genuinely can't be made, so the
    caller can tell "no signal" apart from "signal, but dissimilar" -
    important for `confidence` below.
    """
    if current is None or past is None:
        return None
    if current == 0 and past == 0:
        return 1.0
    larger = max(abs(current), abs(past))
    if larger == 0:
        return 1.0
    return max(0.0, 1.0 - abs(current - past) / larger)


@dataclass(frozen=True)
class _CandidateFeatures:
    """Real, already-persisted data about ONE past decision this module
    needs to score it - never the past decision's raw analysis output,
    only the ids-bearing, persisted entities every other part of this
    codebase already treats as the source of truth."""

    decision: DecisionResponse
    assumptions: list[Assumption]
    thresholds: list[Threshold]


class DecisionSimilarityService:
    """Deterministic, explainable similarity scoring across a user's own
    past decisions. Stateless - holds no repository, no cache, no
    network client; every method is a pure function of its arguments."""

    def score(
        self,
        current: DecisionResponse,
        past: DecisionResponse,
        past_assumptions: list[Assumption],
        past_thresholds: list[Threshold],
    ) -> SimilarityScore:
        """Score one past decision against the current one.

        Never raises for missing/thin data - a past decision with no
        recorded assumptions/thresholds yet simply scores those
        components as "no signal" (excluded from both the weighted sum's
        denominator and `matched_features`), never as a hard 0 that would
        unfairly penalize a decision that just hasn't been analyzed yet.
        """
        current_tokens = _decision_text_tokens(current)
        past_tokens = _decision_text_tokens(past)
        text_similarity = _jaccard(current_tokens, past_tokens)

        assumption_overlap = _jaccard(current_tokens, _assumption_tokens(past_assumptions))
        variable_overlap = _jaccard(current_tokens, _variable_tokens(past_thresholds))
        budget_similarity = _budget_similarity(current.budget, past.budget)
        risk_tolerance_match = (
            1.0
            if current.risk_tolerance
            and past.risk_tolerance
            and current.risk_tolerance.strip().lower() == past.risk_tolerance.strip().lower()
            else 0.0
        )
        location_match = (
            1.0
            if current.location
            and past.location
            and current.location.strip().lower() == past.location.strip().lower()
            else 0.0
        )

        # Components that always have a value (text/assumption/variable
        # overlap - Jaccard on an empty set is a clean 0.0, a real,
        # meaningful "no overlap" rather than "no signal") vs components
        # that can be genuinely absent (budget - `None` when either side
        # lacks one). Only present components count toward both the
        # weighted score and the confidence denominator.
        weighted_components: list[tuple[str, float, float]] = [
            ("decision_text_similarity", text_similarity, _WEIGHT_TEXT_SIMILARITY),
            ("assumption_overlap", assumption_overlap, _WEIGHT_ASSUMPTION_OVERLAP),
            ("key_variable_overlap", variable_overlap, _WEIGHT_VARIABLE_OVERLAP),
        ]
        if budget_similarity is not None:
            weighted_components.append(
                ("budget_similarity", budget_similarity, _WEIGHT_BUDGET_SIMILARITY)
            )
        if current.risk_tolerance and past.risk_tolerance:
            weighted_components.append(
                ("risk_tolerance_match", risk_tolerance_match, _WEIGHT_RISK_TOLERANCE_MATCH)
            )
        if current.location and past.location:
            weighted_components.append(("location_match", location_match, _WEIGHT_LOCATION_MATCH))

        total_weight = sum(weight for _, _, weight in weighted_components)
        score = (
            sum(value * weight for _, value, weight in weighted_components) / total_weight
            if total_weight > 0
            else 0.0
        )

        matched_features = [
            name for name, value, _ in weighted_components if value >= _MATCH_THRESHOLD
        ]

        # Confidence reflects how much of the FULL feature set (all six
        # possible components) actually had comparable data - a score
        # built only from text overlap (the two always-present
        # components' worth of weight) is a thinner basis than one that
        # also had budget/risk-tolerance/location/assumption/threshold
        # data to draw on.
        full_weight = (
            _WEIGHT_TEXT_SIMILARITY
            + _WEIGHT_ASSUMPTION_OVERLAP
            + _WEIGHT_VARIABLE_OVERLAP
            + _WEIGHT_BUDGET_SIMILARITY
            + _WEIGHT_RISK_TOLERANCE_MATCH
            + _WEIGHT_LOCATION_MATCH
        )
        confidence = min(1.0, total_weight / full_weight) if full_weight > 0 else 0.0

        explanation = self._build_explanation(matched_features, past_assumptions, past_thresholds)

        return SimilarityScore(
            decision_id=past.id,
            score=round(score, 4),
            matched_features=matched_features,
            explanation=explanation,
            confidence=round(confidence, 4),
        )

    def rank(
        self,
        current: DecisionResponse,
        candidates: list[tuple[DecisionResponse, list[Assumption], list[Threshold]]],
    ) -> list[SimilarityScore]:
        """Score every candidate and return them ranked by score, highest first.

        `candidates` are (past_decision, past_assumptions, past_thresholds)
        tuples the caller has already fetched and already filtered to the
        current decision's own user - see this module's docstring. Ties in
        score are broken by decision id for a stable, deterministic order
        (never insertion order, which could vary between calls).
        """
        scores = [
            self.score(current, past, assumptions, thresholds)
            for past, assumptions, thresholds in candidates
        ]
        return sorted(scores, key=lambda s: (-s.score, str(s.decision_id)))

    @staticmethod
    def _build_explanation(
        matched_features: list[str],
        past_assumptions: list[Assumption],
        past_thresholds: list[Threshold],
    ) -> str:
        """Plain-English sentence built directly from `matched_features` -
        never free-form LLM prose, and never a claim beyond what the
        named features actually established."""
        if not matched_features:
            return (
                "Only a weak textual resemblance was found; treat this comparison as "
                "low-confidence."
            )

        clauses: list[str] = []
        if "decision_text_similarity" in matched_features:
            clauses.append("similar wording in how the decision itself is described")
        if "assumption_overlap" in matched_features:
            clauses.append(
                f"overlapping themes with {len(past_assumptions)} assumption(s) recorded "
                "for that decision"
            )
        if "key_variable_overlap" in matched_features:
            clauses.append("shares one or more of the same key variables/thresholds")
        if "budget_similarity" in matched_features:
            clauses.append("a comparable budget")
        if "risk_tolerance_match" in matched_features:
            clauses.append("the same stated risk tolerance")
        if "location_match" in matched_features:
            clauses.append("the same stated location")

        if not clauses:
            # Every matched feature had weight but no explanation clause is
            # defined for it (should not happen given the mapping above,
            # but never silently produce an empty sentence).
            return "A measurable similarity was found across this decision's recorded features."

        return "Considered similar because of " + "; ".join(clauses) + "."
