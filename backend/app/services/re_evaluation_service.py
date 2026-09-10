"""Re-evaluation: comparing an experiment's observed result against the
original analysis, deterministically.

This is the validation loop's brain:

    Experiment Result
           |
    Load target Threshold (already persisted - the original analysis
           |                IS the Assumption/Threshold/RegretScenario
           |                records DecisionRepository already stores;
           |                there is no separate "original analysis"
           |                lookup needed beyond those records)
           v
    Compare observed value against the threshold  (deterministic Python,
           |                                        app.services.threshold_comparison)
           v
    Re-evaluate related assumptions   (deterministic status mapping)
           v
    Re-evaluate the related regret scenario  (deterministic status mapping)
           v
    Decision assessment  (deterministic status mapping)
           v
    Persist ReEvaluation (new entity - nothing is overwritten)

No LLM call happens anywhere in this module, per the project's explicit
"prefer deterministic service logic over an LLM for threshold comparison,
numeric comparison, status transitions, experiment lifecycle" instruction.
The only interpretation performed is a small set of documented,
deterministic status-mapping rules below - never free-form reasoning.

This service does NOT mutate the original `Threshold`/`Assumption`/
`RegretScenario` records it evaluates. Every re-evaluation is a new,
separate `ReEvaluation` entity that references them by id, so a decision's
full history (`Analysis -> Experiment -> Result -> Re-evaluation -> ...`)
stays reconstructable - see `DecisionRepository.create_reevaluation`.
"""

from datetime import UTC, datetime
from uuid import UUID

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.repositories.decision_repository import DecisionRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.schemas.decision_resources import (
    AssumptionReevaluationStatus,
    DecisionAssessmentStatus,
    Experiment,
    ExperimentOutcome,
    ExperimentStatus,
    ReEvaluation,
    RegretScenarioReevaluationStatus,
    Threshold,
    ThresholdComparisonStatus,
)
from app.schemas.decision_resources import ExperimentResult as StoredExperimentResult
from app.schemas.experiment_result import ExperimentResultCreate
from app.services.threshold_comparison import ThresholdComparisonResult, compare

logger = get_logger(__name__)

# Confidence values reflect how deterministic/complete the comparison
# actually was - NEVER a probability that the decision will succeed or
# fail. See `DecisionAssessment.confidence`'s docstring.
_CONFIDENCE_VALIDATED_NUMERIC_COMPARISON = 0.85
_CONFIDENCE_PROVISIONAL_NUMERIC_COMPARISON = 0.6
_CONFIDENCE_UNKNOWN_VALIDATION_NUMERIC_COMPARISON = 0.4
_CONFIDENCE_AMBIGUOUS_DIRECTION = 0.35
_CONFIDENCE_DECLARED_OUTCOME_FALLBACK = 0.2


class ReEvaluationService:
    """Orchestrates the deterministic re-evaluation flow for one experiment result."""

    def __init__(
        self, decision_repository: DecisionRepository, evidence_repository: EvidenceRepository
    ) -> None:
        self._decisions = decision_repository
        self._evidence = evidence_repository

    def submit_result(
        self, decision_id: UUID, experiment_id: UUID, payload: ExperimentResultCreate
    ) -> tuple[StoredExperimentResult, ReEvaluation]:
        """Submit an experiment's observed result and immediately re-evaluate.

        Raises `NotFoundError` if the experiment doesn't exist or belongs
        to a different decision. Raises `ValidationError` if the
        experiment has been cancelled (a cancelled experiment cannot
        produce a result), or if `evidence_ids` references anything that
        isn't real, already-uploaded evidence for this decision - evidence
        ids are never accepted on trust. Raises `ConflictError` if the
        experiment was already completed - either by an earlier call, or
        by a concurrent one that won the race (see the conditional write
        in `update_experiment_status` below) - so an experiment can never
        produce two results/re-evaluations.
        """
        experiment = self._decisions.get_experiment_by_id(experiment_id)
        if experiment is None or experiment.decision_id != decision_id:
            raise NotFoundError(detail=f"Experiment {experiment_id} not found.")
        if experiment.status == ExperimentStatus.CANCELLED:
            raise ValidationError(
                detail="This experiment was cancelled and cannot be marked completed."
            )
        if experiment.status == ExperimentStatus.COMPLETED:
            # Fast-path rejection before doing any work (parsing evidence
            # ids, writing a result) - the conditional write below is the
            # authoritative guard against a concurrent race, this is just
            # an early, cheap check for the common sequential case.
            raise ConflictError(
                detail="This experiment already has a submitted result and cannot be "
                "completed again."
            )

        if payload.evidence_ids:
            real_evidence_ids = {
                str(item.id) for item in self._evidence.list_for_decision(decision_id)
            }
            unknown_ids = [eid for eid in payload.evidence_ids if eid not in real_evidence_ids]
            if unknown_ids:
                raise ValidationError(
                    detail="evidence_ids must reference evidence already uploaded to this decision."
                )

        # Atomically claim "completed" status FIRST, before writing the
        # result - this is the authoritative concurrency guard. Two
        # concurrent submissions for the same experiment both pass the
        # fast-path check above (neither observed COMPLETED yet), but only
        # one of these conditional writes can win; the loser raises
        # `ConflictError` here and never gets to create a duplicate
        # result/re-evaluation.
        try:
            self._decisions.update_experiment_status(
                decision_id,
                experiment_id,
                ExperimentStatus.COMPLETED,
                require_not_completed=True,
            )
        except ConflictError as exc:
            raise ConflictError(
                detail="This experiment already has a submitted result and cannot be "
                "completed again."
            ) from exc

        completed_at = payload.completed_at or datetime.now(UTC)
        stored_result = self._decisions.create_experiment_result(
            decision_id,
            experiment_id,
            {
                "outcome": payload.outcome.value,
                "summary": payload.summary,
                "observations": payload.observations,
                "measured_values": payload.measured_values,
                "evidence_ids": payload.evidence_ids,
                "notes": payload.notes,
                "completed_at": completed_at.isoformat(),
            },
        )

        reevaluation = self._reevaluate(decision_id, experiment, stored_result)
        logger.info(
            "Experiment result submitted decision_id=%s experiment_id=%s outcome=%s "
            "assessment=%s",
            decision_id,
            experiment_id,
            payload.outcome.value,
            reevaluation.decision_assessment.status.value,
        )
        return stored_result, reevaluation

    def _reevaluate(
        self, decision_id: UUID, experiment: Experiment, result: StoredExperimentResult
    ) -> ReEvaluation:
        thresholds = self._decisions.list_thresholds(decision_id)
        target_threshold = next(
            (t for t in thresholds if str(t.id) == experiment.target_threshold_id), None
        )

        comparison: ThresholdComparisonResult | None = None
        if target_threshold is not None:
            observed_value = _extract_observed_value(target_threshold, result.measured_values)
            if observed_value is not None:
                comparison = compare(target_threshold, observed_value)

        assumptions = self._decisions.list_assumptions(decision_id)
        regret_scenarios = self._decisions.list_regret_scenarios(decision_id)

        assumption_reevaluations = []
        changed_assumptions: list[str] = []
        related_assumption_ids = target_threshold.related_assumption_ids if target_threshold else []
        for assumption in assumptions:
            if str(assumption.id) not in related_assumption_ids:
                continue
            new_status = _map_assumption_status(comparison, target_threshold)
            assumption_reevaluations.append(
                {
                    "assumption_id": str(assumption.id),
                    "previous_status": assumption.evidence_status.value
                    if assumption.evidence_status
                    else None,
                    "new_status": new_status.value,
                    "explanation": _assumption_explanation(assumption, comparison, new_status),
                }
            )
            changed_assumptions.append(str(assumption.id))

        regret_reevaluations = []
        changed_regret_scenarios: list[str] = []
        related_scenario_ids = (
            target_threshold.related_regret_scenario_ids if target_threshold else []
        )
        for scenario in regret_scenarios:
            if str(scenario.id) not in related_scenario_ids:
                continue
            new_status = _map_regret_scenario_status(comparison)
            regret_reevaluations.append(
                {
                    "regret_scenario_id": str(scenario.id),
                    "previous_status": scenario.regret_level,
                    "new_status": new_status.value,
                    "explanation": _regret_scenario_explanation(scenario, comparison, new_status),
                }
            )
            changed_regret_scenarios.append(str(scenario.id))

        threshold_comparisons = []
        changed_thresholds: list[str] = []
        if target_threshold is not None:
            threshold_comparisons.append(
                {
                    "threshold_id": str(target_threshold.id),
                    "variable": target_threshold.variable,
                    "observed_value": comparison.observed_value if comparison else None,
                    "threshold_value": target_threshold.threshold_value,
                    "status": (
                        comparison.status.value
                        if comparison
                        else ThresholdComparisonStatus.UNKNOWN.value
                    ),
                    "explanation": comparison.explanation
                    if comparison
                    else "No measured value in the experiment result matched this threshold's "
                    "variable, so no deterministic comparison could be made.",
                }
            )
            changed_thresholds.append(str(target_threshold.id))

        assessment = _build_decision_assessment(
            comparison,
            target_threshold,
            result.outcome,
            assumption_reevaluations,
            regret_reevaluations,
            changed_thresholds,
            changed_assumptions,
            changed_regret_scenarios,
        )

        previous_assessment = _describe_previous_state(target_threshold)
        new_assessment = assessment["summary"]
        key_learning = _key_learning(target_threshold, comparison, assessment)

        reevaluation_payload = {
            "experiment_id": str(experiment.id),
            "experiment_result_id": str(result.id),
            "previous_assessment": previous_assessment,
            "new_assessment": new_assessment,
            "threshold_comparisons": threshold_comparisons,
            "assumption_reevaluations": assumption_reevaluations,
            "regret_scenario_reevaluations": regret_reevaluations,
            "decision_assessment": assessment,
            "changed_thresholds": changed_thresholds,
            "changed_assumptions": changed_assumptions,
            "changed_regret_scenarios": changed_regret_scenarios,
            "key_learning": key_learning,
            "recommended_next_step": assessment["recommended_next_step"],
        }
        return self._decisions.create_reevaluation(decision_id, reevaluation_payload)


def _extract_observed_value(
    threshold: Threshold, measured_values: dict[str, object]
) -> object | None:
    """Find the measured value corresponding to a threshold's variable.

    Tries a case-insensitive match against the threshold's own `variable`
    name first (the expected common case); falls back to the sole entry if
    exactly one measured value was submitted (a single-metric experiment
    result naming its value something slightly different from the
    threshold's variable text); otherwise returns `None` - never guesses
    among multiple ambiguous candidates.
    """
    if not measured_values:
        return None

    variable_normalized = threshold.variable.strip().lower()
    for key, value in measured_values.items():
        if key.strip().lower() == variable_normalized:
            return value

    if len(measured_values) == 1:
        return next(iter(measured_values.values()))

    return None


def _map_assumption_status(
    comparison: ThresholdComparisonResult | None, threshold: Threshold | None
) -> AssumptionReevaluationStatus:
    """Deterministically map a threshold comparison onto an assumption's status.

    A MET/WITHIN_RANGE comparison against a fully `validated` threshold is
    treated as real support; the same comparison against a merely
    `provisional`/`unknown` threshold is downgraded to
    PARTIALLY_SUPPORTED/STILL_UNCERTAIN respectively, since the bar being
    cleared/missed was not itself strongly established - this is what
    keeps the service from calling an assumption definitively
    "contradicted" on the strength of a threshold nobody has actually
    validated. See spec: "Do not automatically call an assumption 'false'
    unless the experiment genuinely establishes that."
    """
    if comparison is None:
        return AssumptionReevaluationStatus.INSUFFICIENT_EVIDENCE

    validation_status = (threshold.validation_status if threshold else None) or "unknown"
    is_validated = validation_status == "validated"

    if comparison.status in (ThresholdComparisonStatus.MET, ThresholdComparisonStatus.WITHIN_RANGE):
        return (
            AssumptionReevaluationStatus.SUPPORTED
            if is_validated
            else AssumptionReevaluationStatus.PARTIALLY_SUPPORTED
        )
    if comparison.status in (
        ThresholdComparisonStatus.MISSED,
        ThresholdComparisonStatus.OUTSIDE_RANGE,
    ):
        return (
            AssumptionReevaluationStatus.CONTRADICTED
            if is_validated
            else AssumptionReevaluationStatus.STILL_UNCERTAIN
        )
    if comparison.status in (
        ThresholdComparisonStatus.ABOVE,
        ThresholdComparisonStatus.BELOW,
        ThresholdComparisonStatus.INCONCLUSIVE,
    ):
        return AssumptionReevaluationStatus.STILL_UNCERTAIN
    return AssumptionReevaluationStatus.INSUFFICIENT_EVIDENCE


def _map_regret_scenario_status(
    comparison: ThresholdComparisonResult | None,
) -> RegretScenarioReevaluationStatus:
    """Deterministically map a threshold comparison onto a regret scenario's status.

    A threshold being MET/WITHIN_RANGE means the failure condition did NOT
    materialize, so the regret scenario's evidence is weakened; MISSED/
    OUTSIDE_RANGE means the failure condition's trigger direction was
    actually observed, so the regret scenario's evidence is strengthened.
    """
    if comparison is None:
        return RegretScenarioReevaluationStatus.STILL_UNCERTAIN
    if comparison.status in (ThresholdComparisonStatus.MET, ThresholdComparisonStatus.WITHIN_RANGE):
        return RegretScenarioReevaluationStatus.EVIDENCE_WEAKENED
    if comparison.status in (
        ThresholdComparisonStatus.MISSED,
        ThresholdComparisonStatus.OUTSIDE_RANGE,
    ):
        return RegretScenarioReevaluationStatus.EVIDENCE_STRENGTHENED
    return RegretScenarioReevaluationStatus.STILL_UNCERTAIN


def _assumption_explanation(
    assumption, comparison, new_status: AssumptionReevaluationStatus
) -> str:
    if comparison is None:
        return (
            f"No comparable measured value was available to re-evaluate "
            f"'{assumption.statement}' against the target threshold."
        )
    return (
        f"Threshold comparison ({comparison.status.value}) re-evaluates "
        f"'{assumption.statement}' as {new_status.value}."
    )


def _regret_scenario_explanation(
    scenario, comparison, new_status: RegretScenarioReevaluationStatus
) -> str:
    if comparison is None:
        return (
            f"No comparable measured value was available to re-evaluate the regret scenario "
            f"'{scenario.title}'."
        )
    return (
        f"Threshold comparison ({comparison.status.value}) re-evaluates the regret scenario "
        f"'{scenario.title}' as {new_status.value}."
    )


def _build_decision_assessment(
    comparison: ThresholdComparisonResult | None,
    threshold: Threshold | None,
    declared_outcome: ExperimentOutcome,
    assumption_reevaluations: list[dict[str, object]],
    regret_reevaluations: list[dict[str, object]],
    changed_thresholds: list[str],
    changed_assumptions: list[str],
    changed_regret_scenarios: list[str],
) -> dict[str, object]:
    """Deterministically decide whether this experiment strengthened or
    weakened the original decision's defensibility.

    Priority: a real numeric threshold comparison (MET/MISSED/WITHIN_RANGE/
    OUTSIDE_RANGE) is the primary signal - it directly reflects reality
    against the decision's own recorded tipping point. Only when no such
    comparison could be made does the user's own declared `outcome`
    become the (lower-confidence) fallback signal. This never produces a
    buy/sell/invest verdict - only strengthened/weakened/unchanged/
    inconclusive/requires_more_evidence, per the module's product
    principle.
    """
    validation_status = (threshold.validation_status if threshold else None) or "unknown"

    if comparison is not None and comparison.status in (
        ThresholdComparisonStatus.MET,
        ThresholdComparisonStatus.WITHIN_RANGE,
    ):
        status = DecisionAssessmentStatus.STRENGTHENED
        confidence = (
            _CONFIDENCE_VALIDATED_NUMERIC_COMPARISON
            if validation_status == "validated"
            else _CONFIDENCE_PROVISIONAL_NUMERIC_COMPARISON
            if validation_status == "provisional"
            else _CONFIDENCE_UNKNOWN_VALIDATION_NUMERIC_COMPARISON
        )
        summary = (
            f"The observed value for {threshold.variable if threshold else 'the target variable'} "
            "met the recorded threshold, strengthening the decision's defensibility."
        )
        recommended_next_step = (
            "Increase confidence in the related assumptions and reassess the full commitment "
            "with this new evidence in hand."
        )
    elif comparison is not None and comparison.status in (
        ThresholdComparisonStatus.MISSED,
        ThresholdComparisonStatus.OUTSIDE_RANGE,
    ):
        status = DecisionAssessmentStatus.WEAKENED
        confidence = (
            _CONFIDENCE_VALIDATED_NUMERIC_COMPARISON
            if validation_status == "validated"
            else _CONFIDENCE_PROVISIONAL_NUMERIC_COMPARISON
            if validation_status == "provisional"
            else _CONFIDENCE_UNKNOWN_VALIDATION_NUMERIC_COMPARISON
        )
        summary = (
            f"The observed value for {threshold.variable if threshold else 'the target variable'} "
            "did not meet the recorded threshold, weakening the decision's defensibility."
        )
        recommended_next_step = (
            "Do not make the full commitment yet; investigate whether the underlying model can "
            "be revised, or run a further targeted experiment before proceeding."
        )
    elif comparison is not None and comparison.status in (
        ThresholdComparisonStatus.ABOVE,
        ThresholdComparisonStatus.BELOW,
        ThresholdComparisonStatus.INCONCLUSIVE,
    ):
        status = DecisionAssessmentStatus.INCONCLUSIVE
        confidence = _CONFIDENCE_AMBIGUOUS_DIRECTION
        summary = (
            "The observed value could be compared to the threshold, but the result does not "
            "clearly indicate whether the decision is more or less defensible."
        )
        recommended_next_step = (
            "Extend or redesign the experiment to produce a clearer signal against the "
            "recorded threshold."
        )
    else:
        # No numeric comparison could be made at all - fall back to the
        # user's own declared outcome, at reduced confidence.
        if declared_outcome == ExperimentOutcome.SUCCESS:
            status = DecisionAssessmentStatus.STRENGTHENED
            summary = (
                "No measured value could be matched to a recorded threshold, but the user "
                "reported the experiment as a success."
            )
            recommended_next_step = (
                "Confirm the observed result with a measurable value tied to the target "
                "threshold before treating this as strong evidence."
            )
        elif declared_outcome == ExperimentOutcome.FAILURE:
            status = DecisionAssessmentStatus.WEAKENED
            summary = (
                "No measured value could be matched to a recorded threshold, but the user "
                "reported the experiment as a failure."
            )
            recommended_next_step = (
                "Do not make the full commitment yet; capture a measurable value tied to the "
                "target threshold in a follow-up experiment."
            )
        else:
            status = DecisionAssessmentStatus.REQUIRES_MORE_EVIDENCE
            summary = (
                "The experiment result was inconclusive or partial, and no measured value "
                "could be matched to a recorded threshold."
            )
            recommended_next_step = (
                "Extend or redesign the experiment so it produces a measurable value tied "
                "directly to the target threshold."
            )
        confidence = _CONFIDENCE_DECLARED_OUTCOME_FALLBACK

    if not changed_thresholds and not changed_assumptions and not changed_regret_scenarios:
        status = DecisionAssessmentStatus.UNCHANGED
        summary = (
            "This experiment result did not affect any recorded threshold, assumption, or "
            "regret scenario for this decision."
        )
        recommended_next_step = "No further action required from this result alone."

    evidence_basis = []
    if comparison is not None:
        evidence_basis.append(comparison.explanation)
    evidence_basis.extend(str(item["explanation"]) for item in assumption_reevaluations)
    evidence_basis.extend(str(item["explanation"]) for item in regret_reevaluations)

    return {
        "status": status.value,
        "confidence": confidence,
        "summary": summary,
        "changed_assumptions": changed_assumptions,
        "affected_thresholds": changed_thresholds,
        "affected_regret_scenarios": changed_regret_scenarios,
        "recommended_next_step": recommended_next_step,
        "evidence_basis": evidence_basis,
    }


def _describe_previous_state(threshold: Threshold | None) -> str:
    if threshold is None:
        return "No target threshold was recorded for this experiment prior to this result."
    return (
        f"Threshold for {threshold.variable} was previously "
        f"{threshold.validation_status or 'unknown'} "
        f"(value: {threshold.threshold_value or 'unknown'})."
    )


def _key_learning(
    threshold: Threshold | None,
    comparison: ThresholdComparisonResult | None,
    assessment: dict[str, object],
) -> str:
    if threshold is None or comparison is None:
        return str(assessment["summary"])
    return (
        f"{threshold.variable} was observed at {comparison.observed_value}, versus a "
        f"recorded threshold of {comparison.threshold_value or 'unknown'} "
        f"({comparison.status.value})."
    )
