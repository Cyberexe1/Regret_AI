"""Calibration data model and aggregation (REGRET ENGINE 2.0, Step 24).

Answers a narrower, more concrete question than the quality checks in
`rules.py`: "when this user expected a variable to cross some threshold,
how often did the observed result actually agree?" Aggregated strictly
within ONE user's own completed experiments/re-evaluations - never
across users (see the package docstring's user-isolation principle,
carried over unchanged from Step 23's Cross-Decision Learning).

NO FALSE STATISTICS (spec section 15): this module never computes or
displays a percentage-style calibration score ("REGRET is 94%
calibrated") unless the underlying arithmetic is real and disclosed.
Every claim here is expressed as a plain count ("3 of 4 comparable
experiments...") - `evidence_strength` is one of four descriptive bands,
never a fabricated precision number.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, Field

from app.learning.normalization import normalize_variable
from app.schemas.decision_resources import ReEvaluation, Threshold, ThresholdComparisonStatus

_CALIBRATION_NAMESPACE = uuid5(NAMESPACE_URL, "regret-engine:quality:calibration")

_MET_LIKE = {ThresholdComparisonStatus.MET, ThresholdComparisonStatus.WITHIN_RANGE}
_MISSED_LIKE = {ThresholdComparisonStatus.MISSED, ThresholdComparisonStatus.OUTSIDE_RANGE}


class RecurringBias(StrEnum):
    """A descriptive label for the shape of a user's own expectation-vs-
    outcome history - never a claim of statistical significance (spec
    section 14: "only label consistently_overoptimistic when the
    historical observations actually justify that description").
    """

    CONSISTENTLY_OVEROPTIMISTIC = "consistently_overoptimistic"
    CONSISTENTLY_UNDEROPTIMISTIC = "consistently_underoptimistic"
    MIXED = "mixed"
    INSUFFICIENT_HISTORY = "insufficient_history"
    NO_DETECTABLE_BIAS = "no_detectable_bias"


class CalibrationEvidenceStrength(StrEnum):
    """Descriptive band for how much history backs a calibration
    observation - never a fabricated confidence percentage (spec
    section 13)."""

    LIMITED_HISTORY = "limited_history"
    EMERGING_CALIBRATION = "emerging_calibration"
    MODERATE_CALIBRATION_EVIDENCE = "moderate_calibration_evidence"
    STRONG_CALIBRATION_EVIDENCE = "strong_calibration_evidence"


# spec section 13's exact minimum-evidence policy, expressed as named
# constants rather than magic numbers scattered through the logic below.
_MIN_OBSERVATIONS_FOR_EMERGING = 2
_MIN_OBSERVATIONS_FOR_MODERATE = 4
_MIN_OBSERVATIONS_FOR_STRONG = 6
# A bias label is only ever assigned when one direction clearly
# dominates - never from a bare majority of e.g. 2 out of 3.
_BIAS_DOMINANCE_RATIO = 0.7


class CalibrationInsight(BaseModel):
    """One variable's expected-vs-observed history for ONE user - never
    aggregated across users. `recurring_bias` is a descriptive label,
    always paired with a plain-language `explanation` built only from
    the real counts below it - never a probability, never a percentage
    presented as statistically significant.
    """

    calibration_id: str = Field(
        ...,
        description="Deterministic, derived from (user_id, normalized variable key) - "
        "recomputing calibration for the same user/variable always upserts the SAME record.",
    )
    user_id: str
    variable: str
    expected_direction: str | None = Field(
        default=None,
        description="The most common real threshold direction observed for "
        "this variable ('above'/'below'/etc.) - null if inconsistent or unavailable.",
    )
    observation_count: int = Field(..., ge=0)
    successful_count: int = Field(
        ..., ge=0, description="Observations where the threshold was met."
    )
    unsuccessful_count: int = Field(
        ..., ge=0, description="Observations where the threshold was missed."
    )
    inconclusive_count: int = Field(..., ge=0)
    recurring_bias: RecurringBias
    evidence_strength: CalibrationEvidenceStrength
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How much of this insight rests on real, comparable observations (i.e. "
        "observation_count relative to the strong-evidence bound) - NEVER a probability that "
        "any future prediction will be right.",
    )
    supporting_decision_ids: list[str] = Field(default_factory=list)
    supporting_learning_ids: list[str] = Field(default_factory=list)
    explanation: str = Field(
        ...,
        description="Plain-language, count-based summary - e.g. '3 of 4 comparable "
        "experiments produced outcomes below the original expectation.' Never a fabricated "
        "percentage.",
    )
    created_at: datetime
    updated_at: datetime


@dataclass
class CalibrationObservation:
    """One real, traceable expected-vs-observed data point - always
    derived from a real `ThresholdComparison` embedded in an
    already-persisted `ReEvaluation`. Never fabricated."""

    decision_id: str
    threshold_id: str
    variable: str
    direction: str | None
    status: ThresholdComparisonStatus
    observed_at: datetime
    learning_id: str | None = None


@dataclass
class DecisionCalibrationSignals:
    """Plain data bundle: one decision's thresholds + re-evaluations,
    exactly mirroring `app.learning.pattern_detector.DecisionSignals`'
    shape and purpose - the caller (see `app.quality.service
    .CalibrationService`) assembles this from the existing repositories;
    this module never talks to DynamoDB directly.
    """

    decision_id: str
    thresholds: list[Threshold] = field(default_factory=list)
    reevaluations: list[ReEvaluation] = field(default_factory=list)


def deterministic_calibration_id(user_id: str, normalized_key: str) -> str:
    """Same user + same normalized variable always upserts the SAME
    calibration record - mirrors `app.learning.pattern_detector
    .deterministic_pattern_id`'s exact rationale."""
    return str(uuid5(_CALIBRATION_NAMESPACE, f"{user_id}:{normalized_key}"))


def _extract_observations(
    signals: list[DecisionCalibrationSignals],
) -> list[CalibrationObservation]:
    """Deterministically extracts one `CalibrationObservation` per real
    `ThresholdComparison` found across a user's own decisions - never
    fabricated, always traceable to a real `ReEvaluation`."""
    observations: list[CalibrationObservation] = []
    for bundle in signals:
        thresholds_by_id = {str(t.id): t for t in bundle.thresholds}
        for reeval in bundle.reevaluations:
            for comparison in reeval.threshold_comparisons:
                threshold = thresholds_by_id.get(comparison.threshold_id)
                if threshold is None:
                    continue
                observations.append(
                    CalibrationObservation(
                        decision_id=bundle.decision_id,
                        threshold_id=comparison.threshold_id,
                        variable=threshold.variable,
                        direction=threshold.direction,
                        status=comparison.status,
                        observed_at=reeval.created_at,
                    )
                )
    return observations


def _band_for_count(observation_count: int) -> CalibrationEvidenceStrength:
    if observation_count >= _MIN_OBSERVATIONS_FOR_STRONG:
        return CalibrationEvidenceStrength.STRONG_CALIBRATION_EVIDENCE
    if observation_count >= _MIN_OBSERVATIONS_FOR_MODERATE:
        return CalibrationEvidenceStrength.MODERATE_CALIBRATION_EVIDENCE
    if observation_count >= _MIN_OBSERVATIONS_FOR_EMERGING:
        return CalibrationEvidenceStrength.EMERGING_CALIBRATION
    return CalibrationEvidenceStrength.LIMITED_HISTORY


def _confidence_for_count(observation_count: int) -> float:
    """A bounded, deterministic fraction of the strong-evidence
    threshold - never a probability of any future prediction being
    correct, purely "how much of this insight rests on real
    observations."""
    return round(min(observation_count / _MIN_OBSERVATIONS_FOR_STRONG, 1.0), 4)


def _recurring_bias_and_explanation(
    variable: str, successful: int, unsuccessful: int, inconclusive: int
) -> tuple[RecurringBias, str]:
    total_decisive = successful + unsuccessful
    total = successful + unsuccessful + inconclusive

    if total_decisive < _MIN_OBSERVATIONS_FOR_EMERGING:
        return (
            RecurringBias.INSUFFICIENT_HISTORY,
            f"Only {total} observation(s) exist for '{variable}' so far - not enough history "
            "to describe a pattern yet.",
        )

    # "Missed" (threshold not met) means the ORIGINAL EXPECTATION was
    # optimistic relative to what was observed - i.e. expectations
    # exceeded outcomes. "Met" means expectations were, if anything,
    # cautious relative to outcomes.
    if unsuccessful / total_decisive >= _BIAS_DOMINANCE_RATIO:
        return (
            RecurringBias.CONSISTENTLY_OVEROPTIMISTIC,
            f"{unsuccessful} of {total_decisive} comparable experiments for '{variable}' "
            "produced outcomes below the original expectation.",
        )
    if successful / total_decisive >= _BIAS_DOMINANCE_RATIO:
        return (
            RecurringBias.CONSISTENTLY_UNDEROPTIMISTIC,
            f"{successful} of {total_decisive} comparable experiments for '{variable}' "
            "produced outcomes at or above the original expectation.",
        )
    return (
        RecurringBias.MIXED,
        f"Outcomes for '{variable}' have been mixed: {successful} met their expectation and "
        f"{unsuccessful} did not, across {total_decisive} comparable experiments.",
    )


def compute_calibration_insights(
    user_id: str, signals: list[DecisionCalibrationSignals]
) -> list[CalibrationInsight]:
    """Deterministically aggregates every real `ThresholdComparison`
    across a user's OWN decisions into one `CalibrationInsight` per
    normalized variable. Never aggregates across users - `signals` must
    already be scoped to one user's own decisions by the caller (see
    `app.quality.service.CalibrationService`, which mirrors
    `CrossDecisionLearningService.refresh_patterns`'s own bounded,
    user-scoped loading exactly).
    """
    observations = _extract_observations(signals)
    if not observations:
        return []

    grouped: dict[str, list[CalibrationObservation]] = defaultdict(list)
    for observation in observations:
        key = normalize_variable(observation.variable)
        if key is None:
            continue
        grouped[key].append(observation)

    now = datetime.now(UTC)
    insights: list[CalibrationInsight] = []
    for key, group in grouped.items():
        variable = group[0].variable
        successful = sum(1 for o in group if o.status in _MET_LIKE)
        unsuccessful = sum(1 for o in group if o.status in _MISSED_LIKE)
        inconclusive = len(group) - successful - unsuccessful

        directions = [o.direction for o in group if o.direction]
        expected_direction = max(set(directions), key=directions.count) if directions else None

        recurring_bias, explanation = _recurring_bias_and_explanation(
            variable, successful, unsuccessful, inconclusive
        )

        insights.append(
            CalibrationInsight(
                calibration_id=deterministic_calibration_id(user_id, key),
                user_id=user_id,
                variable=variable,
                expected_direction=expected_direction,
                observation_count=len(group),
                successful_count=successful,
                unsuccessful_count=unsuccessful,
                inconclusive_count=inconclusive,
                recurring_bias=recurring_bias,
                evidence_strength=_band_for_count(len(group)),
                confidence=_confidence_for_count(len(group)),
                supporting_decision_ids=sorted({o.decision_id for o in group}),
                supporting_learning_ids=[],
                explanation=explanation,
                created_at=now,
                updated_at=now,
            )
        )

    return sorted(insights, key=lambda i: i.observation_count, reverse=True)
