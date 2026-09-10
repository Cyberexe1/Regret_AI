"""Deterministic threshold calculations.

The Threshold Engine's LLM reasoning identifies WHICH variable might matter
and WHAT formula could apply; actual arithmetic on numbers the model claims
to have seen is deliberately kept out of the model's hands and done here in
plain Python instead. This is the separation the spec calls for: "do not
ask the LLM to perform complicated arithmetic when deterministic Python can
do it reliably."

Every function here is a pure, named formula that:

- takes only plain numeric inputs
- returns `None` (never raises, never fabricates a fallback number) on
  division by zero, a missing/None input, or a non-finite result
- is referenced by name in `Threshold.calculation_formula`, so a stored
  threshold's provenance is always traceable back to one of these exact
  functions - never to free-form model arithmetic

`CALCULATIONS` maps each recognized formula name to its function and the
named parameters it requires, so `app.agents.threshold_engine` can
recompute (and thereby verify) any calculation the model claims to have
performed, using only the inputs the model says it used - the model's own
arithmetic is never trusted, only its choice of which formula and inputs
apply.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

_Formula = Callable[..., float | None]


def _safe(value: float | int | None) -> float | None:
    """Reject missing or non-finite inputs before any arithmetic runs."""
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def break_even_customers(fixed_cost: float, contribution_per_customer: float) -> float | None:
    """Minimum customers/period needed to cover fixed costs.

    formula: break_even_customers = fixed_cost / contribution_per_customer
    """
    fixed_cost = _safe(fixed_cost)
    contribution_per_customer = _safe(contribution_per_customer)
    if fixed_cost is None or contribution_per_customer is None:
        return None
    if contribution_per_customer == 0:
        return None
    result = fixed_cost / contribution_per_customer
    return result if result >= 0 else None


def break_even_revenue(fixed_cost: float, contribution_margin_ratio: float) -> float | None:
    """Minimum revenue/period needed to cover fixed costs.

    formula: break_even_revenue = fixed_cost / contribution_margin_ratio
    """
    fixed_cost = _safe(fixed_cost)
    contribution_margin_ratio = _safe(contribution_margin_ratio)
    if fixed_cost is None or contribution_margin_ratio is None:
        return None
    if contribution_margin_ratio == 0:
        return None
    result = fixed_cost / contribution_margin_ratio
    return result if result >= 0 else None


def minimum_required_retention(
    required_customers: float, initial_customers: float
) -> float | None:
    """Minimum retention rate needed to keep `required_customers` from an
    initial cohort of `initial_customers`.

    formula: minimum_required_retention = required_customers / initial_customers
    """
    required_customers = _safe(required_customers)
    initial_customers = _safe(initial_customers)
    if required_customers is None or initial_customers is None:
        return None
    if initial_customers == 0:
        return None
    result = required_customers / initial_customers
    return result if result >= 0 else None


def maximum_acceptable_cac(
    lifetime_value: float, minimum_acceptable_margin_ratio: float
) -> float | None:
    """Highest customer-acquisition cost that still leaves the required margin.

    formula: maximum_acceptable_cac = lifetime_value * (1 - minimum_acceptable_margin_ratio)
    """
    lifetime_value = _safe(lifetime_value)
    minimum_acceptable_margin_ratio = _safe(minimum_acceptable_margin_ratio)
    if lifetime_value is None or minimum_acceptable_margin_ratio is None:
        return None
    result = lifetime_value * (1 - minimum_acceptable_margin_ratio)
    return result if result >= 0 else None


def maximum_acceptable_cost(revenue: float, minimum_acceptable_margin_ratio: float) -> float | None:
    """Highest total cost that still leaves the required margin on a given revenue.

    formula: maximum_acceptable_cost = revenue * (1 - minimum_acceptable_margin_ratio)
    """
    revenue = _safe(revenue)
    minimum_acceptable_margin_ratio = _safe(minimum_acceptable_margin_ratio)
    if revenue is None or minimum_acceptable_margin_ratio is None:
        return None
    result = revenue * (1 - minimum_acceptable_margin_ratio)
    return result if result >= 0 else None


def minimum_required_conversion(required_customers: float, total_visitors: float) -> float | None:
    """Minimum conversion rate needed to reach `required_customers` from `total_visitors`.

    formula: minimum_required_conversion = required_customers / total_visitors
    """
    required_customers = _safe(required_customers)
    total_visitors = _safe(total_visitors)
    if required_customers is None or total_visitors is None:
        return None
    if total_visitors == 0:
        return None
    result = required_customers / total_visitors
    return result if result >= 0 else None


def minimum_runway_months(available_capital: float, monthly_burn: float) -> float | None:
    """Number of months available capital lasts at the current burn rate.

    formula: minimum_runway_months = available_capital / monthly_burn
    """
    available_capital = _safe(available_capital)
    monthly_burn = _safe(monthly_burn)
    if available_capital is None or monthly_burn is None:
        return None
    if monthly_burn == 0:
        return None
    result = available_capital / monthly_burn
    return result if result >= 0 else None


@dataclass(frozen=True)
class CalculationSpec:
    """A recognized formula name paired with its function and required inputs."""

    function: _Formula
    required_inputs: tuple[str, ...]


CALCULATIONS: dict[str, CalculationSpec] = {
    "break_even_customers": CalculationSpec(
        break_even_customers, ("fixed_cost", "contribution_per_customer")
    ),
    "break_even_revenue": CalculationSpec(
        break_even_revenue, ("fixed_cost", "contribution_margin_ratio")
    ),
    "minimum_required_retention": CalculationSpec(
        minimum_required_retention, ("required_customers", "initial_customers")
    ),
    "maximum_acceptable_cac": CalculationSpec(
        maximum_acceptable_cac, ("lifetime_value", "minimum_acceptable_margin_ratio")
    ),
    "maximum_acceptable_cost": CalculationSpec(
        maximum_acceptable_cost, ("revenue", "minimum_acceptable_margin_ratio")
    ),
    "minimum_required_conversion": CalculationSpec(
        minimum_required_conversion, ("required_customers", "total_visitors")
    ),
    "minimum_runway_months": CalculationSpec(
        minimum_runway_months, ("available_capital", "monthly_burn")
    ),
}


def evaluate(formula_name: str, inputs: dict[str, float]) -> float | None:
    """Deterministically recompute a named formula from its required inputs.

    Returns `None` (never raises) if the formula name isn't recognized, a
    required input is missing, or the calculation is mathematically invalid
    (division by zero, a non-finite/negative result, malformed numeric
    values) - the caller (`app.agents.threshold_engine`) treats `None` as
    "this cannot be verified," never fills in a fallback number, and falls
    back to a qualitative/unknown threshold instead.
    """
    spec = CALCULATIONS.get(formula_name)
    if spec is None:
        return None
    try:
        kwargs = {name: inputs[name] for name in spec.required_inputs}
    except (KeyError, TypeError):
        return None
    try:
        return spec.function(**kwargs)
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return None
