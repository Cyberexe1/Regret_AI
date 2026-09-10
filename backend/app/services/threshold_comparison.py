"""Deterministic comparison of an observed experiment value against a
recorded threshold.

This module exists so re-evaluation never asks an LLM to perform simple
arithmetic (per the project's existing "deterministic Python over LLM
arithmetic" principle - see `app.agents.threshold_calculations`, which
this module mirrors for the same reason). Every function here:

- takes only the plain numeric/string values actually recorded on a
  `Threshold` and an observed measured value
- returns a `ThresholdComparisonStatus` that is `unknown`/`inconclusive`
  rather than a guess whenever the comparison genuinely cannot be made
  (missing value, malformed number, incompatible unit, threshold with no
  comparable value)
- never raises on bad input - callers get a safe, explicit "cannot
  compare" result instead of a crash

This module NEVER mutates the original `Threshold` record - the caller
(`app.services.re_evaluation_service`) persists the result as a new,
separate `ThresholdComparison` entry that references the threshold by id.
"""

import re
from dataclasses import dataclass

from app.schemas.decision_resources import Threshold, ThresholdComparisonStatus

# Recognized unit tokens, deliberately conservative - comparing across
# unrecognized/incompatible units returns UNKNOWN rather than guessing a
# conversion. "%"/"percent" are treated as equivalent to no unit at all
# (a bare ratio-like number), since thresholds like "24%" and observed
# values like "18" (meaning 18%) should still compare cleanly.
_PERCENT_UNITS = {"%", "percent", "pct"}


@dataclass(frozen=True)
class ThresholdComparisonResult:
    """The outcome of comparing one observed value against one threshold."""

    status: ThresholdComparisonStatus
    observed_value: str | None
    threshold_value: str | None
    explanation: str


def _parse_number(raw: object) -> float | None:
    """Extract a numeric value from a string/int/float/bool observed value.

    Strips common formatting (%, currency symbols, commas, surrounding
    whitespace) but never guesses at a number that isn't actually there -
    returns `None` (never raises) for anything that doesn't parse cleanly.
    Booleans are explicitly rejected: `True`/`False` are not numeric
    observations even though Python would otherwise coerce them.
    """
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int | float):
        return float(raw)
    if not isinstance(raw, str):
        return None

    cleaned = raw.strip()
    if not cleaned:
        return None
    # Strip a single trailing '%' and any leading currency/unit symbols,
    # then any remaining thousands separators.
    cleaned = cleaned.rstrip("%").strip()
    cleaned = re.sub(r"^[^\d\-.+]+", "", cleaned)
    cleaned = cleaned.replace(",", "")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def compare(threshold: Threshold, observed_value: object) -> ThresholdComparisonResult:
    """Deterministically compare `observed_value` against `threshold`.

    Handles the threshold types actually produced by the Threshold Engine:
    NUMERIC/UNKNOWN-with-a-value (single-value comparison against
    `threshold.threshold_value`, using `threshold.direction`), RANGE
    (against `lower_bound`/`upper_bound`), and BINARY/QUALITATIVE/
    TIME_BASED/anything without a usable numeric value (returns UNKNOWN -
    these require human or LLM judgment, never a fabricated numeric
    comparison).
    """
    observed_number = _parse_number(observed_value)
    observed_str = None if observed_value is None else str(observed_value)

    if observed_number is None:
        return ThresholdComparisonResult(
            status=ThresholdComparisonStatus.UNKNOWN,
            observed_value=observed_str,
            threshold_value=threshold.threshold_value,
            explanation=(
                "The observed value could not be parsed as a number, so no deterministic "
                "comparison could be made against this threshold."
            ),
        )

    if threshold.threshold_type == "range" or (
        threshold.lower_bound is not None and threshold.upper_bound is not None
    ):
        return _compare_range(threshold, observed_number, observed_str)

    if threshold.threshold_value is None:
        return ThresholdComparisonResult(
            status=ThresholdComparisonStatus.UNKNOWN,
            observed_value=observed_str,
            threshold_value=None,
            explanation=(
                "This threshold has no recorded numeric value to compare against "
                f"(validation_status={threshold.validation_status or 'unknown'}), so the "
                "observed value cannot be deterministically evaluated."
            ),
        )

    threshold_number = _parse_number(threshold.threshold_value)
    if threshold_number is None:
        return ThresholdComparisonResult(
            status=ThresholdComparisonStatus.UNKNOWN,
            observed_value=observed_str,
            threshold_value=threshold.threshold_value,
            explanation=(
                f"The threshold's recorded value ({threshold.threshold_value!r}) is not a "
                "plain number, so it cannot be deterministically compared."
            ),
        )

    # Unit sanity check: if the observed value carries an explicit,
    # non-empty ALPHABETIC unit token (e.g. "18 days") and the threshold's
    # own unit is set to something else non-percent (e.g. "%"), treat the
    # comparison as unknown rather than silently comparing incompatible
    # units. Currency/other symbolic tokens (₹, $, €, £) are never treated
    # as a conflict - they commonly co-occur with a currency-code unit
    # like "INR" on the threshold side and aren't themselves comparable
    # unit words. A bare number with no unit token (e.g. "18") is always
    # allowed through, since experiment submissions commonly omit units
    # that match the threshold's own unit implicitly.
    if threshold.unit and isinstance(observed_value, str):
        unit_token = re.sub(r"[\d\s.,+\-]", "", observed_value).strip()
        threshold_unit_normalized = threshold.unit.strip().lower()
        if (
            unit_token
            and unit_token.isalpha()
            and unit_token.lower() not in _PERCENT_UNITS
            and unit_token.lower() != threshold_unit_normalized
            and threshold_unit_normalized not in _PERCENT_UNITS
        ):
            return ThresholdComparisonResult(
                status=ThresholdComparisonStatus.UNKNOWN,
                observed_value=observed_str,
                threshold_value=threshold.threshold_value,
                explanation=(
                    f"The observed value's unit ({unit_token!r}) does not match the "
                    f"threshold's unit ({threshold.unit!r}), so the values cannot be "
                    "safely compared."
                ),
            )

    return _compare_single(threshold, threshold_number, observed_number, observed_str)


def _compare_single(
    threshold: Threshold, threshold_number: float, observed_number: float, observed_str: str | None
) -> ThresholdComparisonResult:
    direction = (threshold.direction or "unknown").lower()

    if direction == "below":
        met = observed_number >= threshold_number
        status = ThresholdComparisonStatus.MET if met else ThresholdComparisonStatus.MISSED
        relation = "at or above" if met else "below"
        explanation = (
            f"Observed value {observed_number:g} is {relation} the required minimum of "
            f"{threshold_number:g} (threshold requires staying at/above this level)."
        )
    elif direction == "above":
        met = observed_number <= threshold_number
        status = ThresholdComparisonStatus.MET if met else ThresholdComparisonStatus.MISSED
        relation = "at or below" if met else "above"
        explanation = (
            f"Observed value {observed_number:g} is {relation} the acceptable maximum of "
            f"{threshold_number:g} (threshold requires staying at/below this level)."
        )
    elif direction in {"equals", "not_equals"}:
        equal = observed_number == threshold_number
        if direction == "equals":
            status = ThresholdComparisonStatus.MET if equal else ThresholdComparisonStatus.MISSED
        else:
            status = ThresholdComparisonStatus.MISSED if equal else ThresholdComparisonStatus.MET
        explanation = (
            f"Observed value {observed_number:g} {'equals' if equal else 'does not equal'} "
            f"the threshold value {threshold_number:g}."
        )
    else:
        # unknown/fails/other directions: report the raw relationship
        # without claiming a met/missed judgment we can't actually justify.
        status = (
            ThresholdComparisonStatus.ABOVE
            if observed_number > threshold_number
            else ThresholdComparisonStatus.BELOW
            if observed_number < threshold_number
            else ThresholdComparisonStatus.INCONCLUSIVE
        )
        explanation = (
            f"Observed value {observed_number:g} compared to threshold value "
            f"{threshold_number:g}, but the threshold's direction ({direction}) does not "
            "support a clear met/missed judgment - reporting the raw relationship only."
        )

    return ThresholdComparisonResult(
        status=status,
        observed_value=observed_str,
        threshold_value=threshold.threshold_value,
        explanation=explanation,
    )


def _compare_range(
    threshold: Threshold, observed_number: float, observed_str: str | None
) -> ThresholdComparisonResult:
    lower = threshold.lower_bound
    upper = threshold.upper_bound
    if lower is None or upper is None:
        return ThresholdComparisonResult(
            status=ThresholdComparisonStatus.UNKNOWN,
            observed_value=observed_str,
            threshold_value=threshold.threshold_value,
            explanation="This range threshold is missing a lower or upper bound.",
        )

    direction = (threshold.direction or "").lower()
    within = lower <= observed_number <= upper
    if direction == "outside_range":
        status = (
            ThresholdComparisonStatus.MISSED if within else ThresholdComparisonStatus.MET
        )
    else:
        status = (
            ThresholdComparisonStatus.WITHIN_RANGE
            if within
            else ThresholdComparisonStatus.OUTSIDE_RANGE
        )

    explanation = (
        f"Observed value {observed_number:g} is "
        f"{'within' if within else 'outside'} the recorded safe range "
        f"[{lower:g}, {upper:g}]."
    )
    return ThresholdComparisonResult(
        status=status,
        observed_value=observed_str,
        threshold_value=f"[{lower:g}, {upper:g}]",
        explanation=explanation,
    )
