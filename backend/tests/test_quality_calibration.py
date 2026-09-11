"""Tests for `app.quality.calibration` - deterministic expected-vs-
observed calibration aggregation (REGRET ENGINE 2.0, Step 24).

No LLM/DynamoDB involved - pure data-in, data-out over plain constructed
schema objects, mirroring `test_learning_pattern_detector.py`.
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.quality.calibration import (
    CalibrationEvidenceStrength,
    DecisionCalibrationSignals,
    RecurringBias,
    compute_calibration_insights,
    deterministic_calibration_id,
)
from app.schemas.decision_resources import (
    DecisionAssessment,
    DecisionAssessmentStatus,
    ReEvaluation,
    Threshold,
    ThresholdComparison,
    ThresholdComparisonStatus,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _threshold(variable="Repeat-order rate", direction="below", **overrides) -> Threshold:
    defaults = {
        "id": uuid4(),
        "decision_id": uuid4(),
        "variable": variable,
        "direction": direction,
        "threshold_value": "24",
        "created_at": NOW,
    }
    defaults.update(overrides)
    return Threshold(**defaults)


def _reeval(threshold: Threshold, status: ThresholdComparisonStatus, **overrides) -> ReEvaluation:
    defaults = {
        "id": uuid4(),
        "decision_id": threshold.decision_id,
        "experiment_id": uuid4(),
        "experiment_result_id": uuid4(),
        "previous_assessment": "x",
        "new_assessment": "y",
        "threshold_comparisons": [
            ThresholdComparison(
                threshold_id=str(threshold.id),
                variable=threshold.variable,
                status=status,
                explanation="x",
            )
        ],
        "decision_assessment": DecisionAssessment(
            status=DecisionAssessmentStatus.WEAKENED,
            confidence=0.5,
            summary="x",
            recommended_next_step="x",
        ),
        "key_learning": "x",
        "recommended_next_step": "x",
        "created_at": NOW,
    }
    defaults.update(overrides)
    return ReEvaluation(**defaults)


def test_zero_history_produces_no_insights() -> None:
    insights = compute_calibration_insights("user-a", [])

    assert insights == []


def test_one_observation_is_insufficient_history() -> None:
    threshold = _threshold()
    reeval = _reeval(threshold, ThresholdComparisonStatus.MISSED)
    signals = [
        DecisionCalibrationSignals(
            decision_id=str(threshold.decision_id), thresholds=[threshold], reevaluations=[reeval]
        )
    ]

    insights = compute_calibration_insights("user-a", signals)

    assert len(insights) == 1
    assert insights[0].observation_count == 1
    assert insights[0].recurring_bias.value == "insufficient_history"
    assert insights[0].evidence_strength == CalibrationEvidenceStrength.LIMITED_HISTORY


def test_multiple_consistent_missed_observations_are_overoptimistic() -> None:
    threshold = _threshold()
    decision_id = str(threshold.decision_id)
    reevals = [_reeval(threshold, ThresholdComparisonStatus.MISSED) for _ in range(3)]
    signals = [
        DecisionCalibrationSignals(
            decision_id=decision_id, thresholds=[threshold], reevaluations=reevals
        )
    ]

    insights = compute_calibration_insights("user-a", signals)

    assert len(insights) == 1
    insight = insights[0]
    assert insight.observation_count == 3
    assert insight.unsuccessful_count == 3
    assert insight.recurring_bias == RecurringBias.CONSISTENTLY_OVEROPTIMISTIC
    assert "3 of 3" in insight.explanation


def test_multiple_consistent_met_observations_are_underoptimistic() -> None:
    threshold = _threshold(variable="Landing page conversion")
    decision_id = str(threshold.decision_id)
    reevals = [_reeval(threshold, ThresholdComparisonStatus.MET) for _ in range(4)]
    signals = [
        DecisionCalibrationSignals(
            decision_id=decision_id, thresholds=[threshold], reevaluations=reevals
        )
    ]

    insights = compute_calibration_insights("user-a", signals)

    assert insights[0].recurring_bias == RecurringBias.CONSISTENTLY_UNDEROPTIMISTIC
    assert (
        insights[0].evidence_strength == CalibrationEvidenceStrength.MODERATE_CALIBRATION_EVIDENCE
    )


def test_contradictory_observations_produce_mixed_bias() -> None:
    threshold = _threshold()
    decision_id = str(threshold.decision_id)
    reevals = [
        _reeval(threshold, ThresholdComparisonStatus.MET),
        _reeval(threshold, ThresholdComparisonStatus.MISSED),
        _reeval(threshold, ThresholdComparisonStatus.MET),
    ]
    signals = [
        DecisionCalibrationSignals(
            decision_id=decision_id, thresholds=[threshold], reevaluations=reevals
        )
    ]

    insights = compute_calibration_insights("user-a", signals)

    assert insights[0].recurring_bias == RecurringBias.MIXED
    assert insights[0].successful_count == 2
    assert insights[0].unsuccessful_count == 1


def test_no_false_precision_explanation_uses_plain_counts_never_percentages() -> None:
    threshold = _threshold()
    decision_id = str(threshold.decision_id)
    reevals = [_reeval(threshold, ThresholdComparisonStatus.MISSED) for _ in range(3)]
    signals = [
        DecisionCalibrationSignals(
            decision_id=decision_id, thresholds=[threshold], reevaluations=reevals
        )
    ]

    insights = compute_calibration_insights("user-a", signals)

    assert "%" not in insights[0].explanation
    assert "3 of 3" in insights[0].explanation


def test_confidence_is_bounded_and_never_a_success_probability() -> None:
    threshold = _threshold()
    decision_id = str(threshold.decision_id)
    reevals = [_reeval(threshold, ThresholdComparisonStatus.MISSED) for _ in range(10)]
    signals = [
        DecisionCalibrationSignals(
            decision_id=decision_id, thresholds=[threshold], reevaluations=reevals
        )
    ]

    insights = compute_calibration_insights("user-a", signals)

    assert 0.0 <= insights[0].confidence <= 1.0
    assert insights[0].confidence == 1.0  # capped at the strong-evidence bound


def test_inconclusive_comparisons_are_tracked_separately() -> None:
    threshold = _threshold()
    decision_id = str(threshold.decision_id)
    reevals = [
        _reeval(threshold, ThresholdComparisonStatus.INCONCLUSIVE),
        _reeval(threshold, ThresholdComparisonStatus.UNKNOWN),
    ]
    signals = [
        DecisionCalibrationSignals(
            decision_id=decision_id, thresholds=[threshold], reevaluations=reevals
        )
    ]

    insights = compute_calibration_insights("user-a", signals)

    assert insights[0].inconclusive_count == 2
    assert insights[0].successful_count == 0
    assert insights[0].unsuccessful_count == 0


def test_different_variables_produce_separate_insights() -> None:
    threshold_a = _threshold(variable="Repeat-order rate")
    threshold_b = _threshold(variable="Acquisition cost")
    decision_id = str(threshold_a.decision_id)
    reevals = [
        _reeval(threshold_a, ThresholdComparisonStatus.MISSED),
        _reeval(threshold_a, ThresholdComparisonStatus.MISSED),
        _reeval(threshold_b, ThresholdComparisonStatus.MET),
        _reeval(threshold_b, ThresholdComparisonStatus.MET),
    ]
    signals = [
        DecisionCalibrationSignals(
            decision_id=decision_id, thresholds=[threshold_a, threshold_b], reevaluations=reevals
        )
    ]

    insights = compute_calibration_insights("user-a", signals)

    assert len(insights) == 2
    variables = {i.variable for i in insights}
    assert variables == {"Repeat-order rate", "Acquisition cost"}


def test_deterministic_calibration_id_is_stable_per_user_and_variable() -> None:
    id_a = deterministic_calibration_id("user-1", "retention")
    id_b = deterministic_calibration_id("user-1", "retention")
    id_c = deterministic_calibration_id("user-2", "retention")

    assert id_a == id_b
    assert id_a != id_c


def test_supporting_decision_ids_are_real_and_traceable() -> None:
    threshold = _threshold()
    decision_id = str(threshold.decision_id)
    reevals = [_reeval(threshold, ThresholdComparisonStatus.MISSED) for _ in range(2)]
    signals = [
        DecisionCalibrationSignals(
            decision_id=decision_id, thresholds=[threshold], reevaluations=reevals
        )
    ]

    insights = compute_calibration_insights("user-a", signals)

    assert insights[0].supporting_decision_ids == [decision_id]
