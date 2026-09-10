"""Tests for deterministic threshold comparison.

No LLM/Strands invocation happens anywhere in this file - every comparison
is pure Python arithmetic.
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.schemas.decision_resources import Threshold, ThresholdComparisonStatus
from app.services.threshold_comparison import compare


def _threshold(**overrides) -> Threshold:
    defaults = dict(
        id=uuid4(),
        decision_id=uuid4(),
        variable="Repeat-order rate",
        threshold_type="numeric",
        direction="below",
        threshold_value="24",
        unit="%",
        confidence=0.7,
        derivation="calculated_from_evidence",
        consequence="Unit economics no longer hold.",
        evidence_basis="x",
        validation_status="validated",
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return Threshold(**defaults)


# --- 18 < 24 (below direction: missed) ---------------------------------------


def test_observed_below_threshold_with_below_direction_is_missed() -> None:
    threshold = _threshold(direction="below", threshold_value="24")

    result = compare(threshold, 18)

    assert result.status is ThresholdComparisonStatus.MISSED
    assert result.observed_value == "18"


def test_observed_at_or_above_threshold_with_below_direction_is_met() -> None:
    threshold = _threshold(direction="below", threshold_value="24")

    result = compare(threshold, 30)

    assert result.status is ThresholdComparisonStatus.MET


# --- 18 > 12 (above direction) -----------------------------------------------


def test_observed_above_threshold_with_above_direction_is_missed() -> None:
    """direction=above means the threshold is a maximum acceptable value -
    exceeding it is a miss."""
    threshold = _threshold(direction="above", threshold_value="12")

    result = compare(threshold, 18)

    assert result.status is ThresholdComparisonStatus.MISSED


def test_observed_at_or_below_threshold_with_above_direction_is_met() -> None:
    threshold = _threshold(direction="above", threshold_value="12")

    result = compare(threshold, 10)

    assert result.status is ThresholdComparisonStatus.MET


# --- 30 within 20-40 / 45 outside 20-40 ---------------------------------------


def test_value_within_range_is_within_range() -> None:
    threshold = _threshold(threshold_type="range", lower_bound=20.0, upper_bound=40.0)

    result = compare(threshold, 30)

    assert result.status is ThresholdComparisonStatus.WITHIN_RANGE


def test_value_outside_range_is_outside_range() -> None:
    threshold = _threshold(threshold_type="range", lower_bound=20.0, upper_bound=40.0)

    result = compare(threshold, 45)

    assert result.status is ThresholdComparisonStatus.OUTSIDE_RANGE


def test_range_with_outside_range_direction_flips_met_missed() -> None:
    threshold = _threshold(
        threshold_type="range", direction="outside_range", lower_bound=20.0, upper_bound=40.0
    )

    within = compare(threshold, 30)
    outside = compare(threshold, 45)

    assert within.status is ThresholdComparisonStatus.MISSED
    assert outside.status is ThresholdComparisonStatus.MET


# --- missing value / incompatible units / malformed values / unknown --------


def test_missing_observed_value_is_unknown() -> None:
    threshold = _threshold()

    result = compare(threshold, None)

    assert result.status is ThresholdComparisonStatus.UNKNOWN


def test_malformed_observed_value_is_unknown() -> None:
    threshold = _threshold()

    result = compare(threshold, "not a number")

    assert result.status is ThresholdComparisonStatus.UNKNOWN


def test_threshold_with_no_value_is_unknown() -> None:
    threshold = _threshold(threshold_value=None, validation_status="unknown")

    result = compare(threshold, 18)

    assert result.status is ThresholdComparisonStatus.UNKNOWN


def test_malformed_threshold_value_is_unknown() -> None:
    threshold = _threshold(threshold_value="at least two enterprise customers")

    result = compare(threshold, 18)

    assert result.status is ThresholdComparisonStatus.UNKNOWN


def test_incompatible_units_are_unknown() -> None:
    threshold = _threshold(direction="below", threshold_value="24", unit="%")

    result = compare(threshold, "18 days")

    assert result.status is ThresholdComparisonStatus.UNKNOWN


def test_range_threshold_missing_bounds_is_unknown() -> None:
    threshold = _threshold(threshold_type="range", lower_bound=None, upper_bound=None)

    result = compare(threshold, 30)

    assert result.status is ThresholdComparisonStatus.UNKNOWN


def test_percent_formatted_observed_value_parses_correctly() -> None:
    threshold = _threshold(direction="below", threshold_value="24")

    result = compare(threshold, "18%")

    assert result.status is ThresholdComparisonStatus.MISSED
    assert result.observed_value == "18%"


def test_currency_and_comma_formatted_observed_value_parses_correctly() -> None:
    threshold = _threshold(direction="above", threshold_value="500000", unit="INR")

    result = compare(threshold, "₹1,00,000")

    assert result.status is ThresholdComparisonStatus.MET


def test_ambiguous_direction_reports_raw_relationship_not_a_verdict() -> None:
    threshold = _threshold(direction="unknown", threshold_value="24")

    result = compare(threshold, 18)

    assert result.status is ThresholdComparisonStatus.BELOW


def test_equals_direction() -> None:
    threshold = _threshold(direction="equals", threshold_value="24")

    met = compare(threshold, 24)
    missed = compare(threshold, 25)

    assert met.status is ThresholdComparisonStatus.MET
    assert missed.status is ThresholdComparisonStatus.MISSED


def test_boolean_observed_value_is_rejected_as_non_numeric() -> None:
    """True/False must never be silently coerced into 1/0."""
    threshold = _threshold()

    result = compare(threshold, True)

    assert result.status is ThresholdComparisonStatus.UNKNOWN
