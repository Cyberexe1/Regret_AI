"""Deterministic quality checks (REGRET ENGINE 2.0, Step 24).

No LLM call happens anywhere in this module. Every function below takes
plain, already-persisted records for ONE decision (bundled by
`app.quality.service.QualityService._load_signals`, mirroring
`app.learning.pattern_detector.DecisionSignals`'s exact shape) and
returns a list of real `QualityCheck` rows - never a fabricated
confidence percentage, never a re-judgment of whether the decision
itself is wise (see the package docstring's "analysis quality vs
decision quality" principle).

Each `_check_*` function is named after the rule it implements and
returns zero or more `QualityCheck` rows. `service.py` collects them all,
buckets them into the nine categories, and derives per-category and
overall `QualityBand`s deterministically from their statuses/severities -
never from a separate, independently-computed score.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from app.learning.normalization import normalize_variable
from app.learning.schemas import CrossDecisionPattern, HistoricalLearningSignal, PatternStatus
from app.memory.memory_schemas import DecisionMemory, MemoryLearning
from app.quality.schemas import (
    QualityCheck,
    QualityCheckCategory,
    QualityCheckSeverity,
    QualityCheckStatus,
)
from app.schemas.decision import DecisionResponse
from app.schemas.decision_resources import (
    Assumption,
    Blindspot,
    Evidence,
    Experiment,
    ExperimentResult,
    ExperimentStatus,
    ReEvaluation,
    Threshold,
    ThresholdComparisonStatus,
)
from app.schemas.decision_resources import EvidenceFinding as StoredEvidenceFinding

_CHECK_NAMESPACE = uuid5(NAMESPACE_URL, "regret-engine:quality:check")

_MET_LIKE = {ThresholdComparisonStatus.MET, ThresholdComparisonStatus.WITHIN_RANGE}
_MISSED_LIKE = {ThresholdComparisonStatus.MISSED, ThresholdComparisonStatus.OUTSIDE_RANGE}
_CRITICAL_IMPORTANCE = {"critical", "high"}
_UNRESOLVED_EVIDENCE_STATUSES = {"unverified", "not_addressed"}

# Required pipeline stages (spec section 12) - a missing one is always
# at least a warning; optional/recommended stages never cause a failure
# merely for being absent.
_REQUIRED_STAGES = {
    "decision_analyzer",
    "assumption_hunter",
    "blindspot_hunter",
    "evidence_agent",
    "devils_advocate",
    "regret_simulator",
    "threshold_engine",
    "experiment_planner",
}
_RECOMMENDED_STAGES = {"value_of_information", "historical_context"}
_OPTIONAL_STAGES = {"research_agent", "adaptive_loop", "memory", "evolution"}


def deterministic_check_id(
    quality_id: str, category: str, name: str, related_entity_id: str | None
) -> str:
    """Same rule against the same record always produces the SAME check
    id - lets a re-run of the same quality pass be recognized as
    identical rather than a fresh, unrelated set of findings."""
    return str(uuid5(_CHECK_NAMESPACE, f"{quality_id}:{category}:{name}:{related_entity_id}"))


@dataclass
class DecisionQualitySignals:
    """Plain data bundle: every real, already-persisted record needed
    to run every quality check for ONE decision - mirrors
    `app.learning.pattern_detector.DecisionSignals`'s exact shape and
    purpose. Assembled by `app.quality.service.QualityService
    ._load_signals`; this module never talks to DynamoDB itself."""

    decision: DecisionResponse
    assumptions: list[Assumption] = field(default_factory=list)
    blindspots: list[Blindspot] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    evidence_findings: list[StoredEvidenceFinding] = field(default_factory=list)
    thresholds: list[Threshold] = field(default_factory=list)
    experiments: list[Experiment] = field(default_factory=list)
    experiment_results: list[ExperimentResult] = field(default_factory=list)
    reevaluations: list[ReEvaluation] = field(default_factory=list)
    memory: DecisionMemory | None = None
    learnings: list[MemoryLearning] = field(default_factory=list)
    cross_decision_patterns: list[CrossDecisionPattern] = field(default_factory=list)
    analysis_run_id: str | None = None
    analysis_result_keys: set[str] = field(default_factory=set)
    analysis_completed_at: datetime | None = None


def _make_check(
    quality_id: str,
    category: QualityCheckCategory,
    name: str,
    status: QualityCheckStatus,
    severity: QualityCheckSeverity,
    message: str,
    related_entity_type: str | None = None,
    related_entity_id: str | None = None,
    evidence_ids: list[str] | None = None,
    recommendation: str | None = None,
) -> QualityCheck:
    return QualityCheck(
        check_id=deterministic_check_id(quality_id, category.value, name, related_entity_id),
        category=category,
        name=name,
        status=status,
        severity=severity,
        message=message,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        evidence_ids=evidence_ids or [],
        recommendation=recommendation,
        created_at=datetime.now(UTC),
    )


# --- 4/5: evidence + assumption quality ---------------------------------------


def check_evidence_quality(quality_id: str, signals: DecisionQualitySignals) -> list[QualityCheck]:
    """Spec section 4/5: critical assumptions need real, resolvable
    evidence; findings must reference a real Evidence id; evidence
    marked insufficient is flagged, never silently treated as support."""
    checks: list[QualityCheck] = []
    real_evidence_ids = {str(e.id) for e in signals.evidence}

    for finding in signals.evidence_findings:
        if str(finding.evidence_id) not in real_evidence_ids:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.EVIDENCE,
                    "finding_references_real_evidence",
                    QualityCheckStatus.FAILED,
                    QualityCheckSeverity.HIGH,
                    f"An evidence finding claims support from evidence id "
                    f"{finding.evidence_id}, which does not exist for this decision.",
                    related_entity_type="evidence_finding",
                    related_entity_id=str(finding.id),
                    recommendation="Re-run analysis or verify the evidence record wasn't deleted.",
                )
            )
        elif (finding.support_level or "").lower() in {"insufficient", "weak"}:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.EVIDENCE,
                    "evidence_support_insufficient",
                    QualityCheckStatus.WARNING,
                    QualityCheckSeverity.MEDIUM,
                    f"Evidence exists for the claim '{finding.claim}' but is marked "
                    f"'{finding.support_level}'.",
                    related_entity_type="evidence_finding",
                    related_entity_id=str(finding.id),
                    evidence_ids=[str(finding.evidence_id)],
                )
            )
        else:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.EVIDENCE,
                    "evidence_support_present",
                    QualityCheckStatus.PASSED,
                    QualityCheckSeverity.INFO,
                    f"The claim '{finding.claim}' is backed by real, submitted evidence.",
                    related_entity_type="evidence_finding",
                    related_entity_id=str(finding.id),
                    evidence_ids=[str(finding.evidence_id)],
                )
            )

    finding_assumption_ids = {
        aid for finding in signals.evidence_findings for aid in finding.related_assumption_ids
    }
    for assumption in signals.assumptions:
        if (assumption.importance or "").lower() not in _CRITICAL_IMPORTANCE:
            continue
        if str(assumption.id) in finding_assumption_ids:
            continue
        checks.append(
            _make_check(
                quality_id,
                QualityCheckCategory.EVIDENCE,
                "critical_assumption_has_evidence",
                QualityCheckStatus.WARNING,
                QualityCheckSeverity.HIGH,
                f"'{assumption.statement}' is a critical assumption with no submitted "
                "evidence finding addressing it.",
                related_entity_type="assumption",
                related_entity_id=str(assumption.id),
                recommendation="Upload evidence addressing this assumption, or run an "
                "experiment that would produce it.",
            )
        )

    return checks


def check_assumption_quality(
    quality_id: str, signals: DecisionQualitySignals
) -> list[QualityCheck]:
    """Spec section 5: confidence must not contradict evidence_status;
    unresolved assumptions must never be silently presented as
    validated; assumptions referenced by thresholds must actually exist.
    """
    checks: list[QualityCheck] = []
    assumption_ids = {str(a.id) for a in signals.assumptions}

    for assumption in signals.assumptions:
        status = assumption.evidence_status.value
        confidence = assumption.confidence

        if status in _UNRESOLVED_EVIDENCE_STATUSES and confidence is not None and confidence >= 0.7:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.ASSUMPTION,
                    "confidence_matches_evidence_status",
                    QualityCheckStatus.FAILED,
                    QualityCheckSeverity.HIGH,
                    f"'{assumption.statement}' has confidence {confidence:.2f} but its "
                    f"evidence_status is still '{status}' - the confidence is inconsistent "
                    "with how little has actually been resolved.",
                    related_entity_type="assumption",
                    related_entity_id=str(assumption.id),
                    recommendation="Re-run analysis, or treat this confidence value with caution "
                    "until real evidence exists.",
                )
            )
        elif status == "contradicted":
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.ASSUMPTION,
                    "contradicted_assumption_flagged",
                    QualityCheckStatus.WARNING,
                    QualityCheckSeverity.MEDIUM,
                    f"'{assumption.statement}' has evidence marked as contradicting it.",
                    related_entity_type="assumption",
                    related_entity_id=str(assumption.id),
                )
            )
        else:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.ASSUMPTION,
                    "confidence_matches_evidence_status",
                    QualityCheckStatus.PASSED,
                    QualityCheckSeverity.INFO,
                    f"'{assumption.statement}' has a confidence level consistent with its "
                    "recorded evidence status.",
                    related_entity_type="assumption",
                    related_entity_id=str(assumption.id),
                )
            )

    for threshold in signals.thresholds:
        for related_id in threshold.related_assumption_ids:
            if related_id not in assumption_ids:
                checks.append(
                    _make_check(
                        quality_id,
                        QualityCheckCategory.ASSUMPTION,
                        "threshold_assumption_exists",
                        QualityCheckStatus.FAILED,
                        QualityCheckSeverity.HIGH,
                        f"Threshold '{threshold.variable}' references assumption id "
                        f"{related_id}, which does not exist for this decision.",
                        related_entity_type="threshold",
                        related_entity_id=str(threshold.id),
                    )
                )

    return checks


# --- 6: threshold quality --------------------------------------------------------


def check_threshold_quality(quality_id: str, signals: DecisionQualitySignals) -> list[QualityCheck]:
    """Spec section 6: never auto-modifies a threshold, only flags it."""
    checks: list[QualityCheck] = []
    tested_threshold_ids = {
        comparison.threshold_id
        for reeval in signals.reevaluations
        for comparison in reeval.threshold_comparisons
    }

    for threshold in signals.thresholds:
        has_numeric_value = threshold.threshold_value is not None and _is_numeric(
            threshold.threshold_value
        )
        has_bounds = threshold.lower_bound is not None or threshold.upper_bound is not None

        if has_numeric_value and not threshold.unit and threshold.threshold_type == "numeric":
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.THRESHOLD,
                    "threshold_has_unit",
                    QualityCheckStatus.WARNING,
                    QualityCheckSeverity.LOW,
                    f"Threshold '{threshold.variable}' has a numeric value "
                    f"({threshold.threshold_value}) but no unit recorded.",
                    related_entity_type="threshold",
                    related_entity_id=str(threshold.id),
                )
            )

        if threshold.threshold_value is not None and not has_numeric_value and not has_bounds:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.THRESHOLD,
                    "threshold_value_is_valid",
                    QualityCheckStatus.WARNING,
                    QualityCheckSeverity.MEDIUM,
                    f"Threshold '{threshold.variable}' has a non-numeric, non-bounded value "
                    f"('{threshold.threshold_value}') recorded as its threshold_value.",
                    related_entity_type="threshold",
                    related_entity_id=str(threshold.id),
                )
            )

        if not threshold.evidence_basis and not threshold.related_assumption_ids:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.THRESHOLD,
                    "threshold_has_grounding",
                    QualityCheckStatus.WARNING,
                    QualityCheckSeverity.MEDIUM,
                    f"Threshold '{threshold.variable}' has no evidence_basis and no related "
                    "assumption - its grounding cannot be traced.",
                    related_entity_type="threshold",
                    related_entity_id=str(threshold.id),
                )
            )
        else:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.THRESHOLD,
                    "threshold_has_grounding",
                    QualityCheckStatus.PASSED,
                    QualityCheckSeverity.INFO,
                    f"Threshold '{threshold.variable}' traces back to a real assumption or "
                    "evidence basis.",
                    related_entity_type="threshold",
                    related_entity_id=str(threshold.id),
                )
            )

        if not threshold.related_regret_scenario_ids:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.THRESHOLD,
                    "threshold_connected_to_regret_scenario",
                    QualityCheckStatus.WARNING,
                    QualityCheckSeverity.LOW,
                    f"Threshold '{threshold.variable}' is not connected to any regret scenario.",
                    related_entity_type="threshold",
                    related_entity_id=str(threshold.id),
                )
            )

        has_completed_experiment = any(
            e.status == ExperimentStatus.COMPLETED
            for e in signals.experiments
            if e.target_threshold_id == str(threshold.id)
        )
        if has_completed_experiment and str(threshold.id) not in tested_threshold_ids:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.THRESHOLD,
                    "threshold_evaluated_after_experiment",
                    QualityCheckStatus.WARNING,
                    QualityCheckSeverity.MEDIUM,
                    f"Threshold '{threshold.variable}' has a completed experiment but was "
                    "never actually compared against its result.",
                    related_entity_type="threshold",
                    related_entity_id=str(threshold.id),
                )
            )

        contradiction = _threshold_contradicts_constraint(threshold, signals.decision)
        if contradiction:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.THRESHOLD,
                    "threshold_matches_user_constraints",
                    QualityCheckStatus.WARNING,
                    QualityCheckSeverity.MEDIUM,
                    contradiction,
                    related_entity_type="threshold",
                    related_entity_id=str(threshold.id),
                )
            )

    return checks


def _is_numeric(value: str) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _threshold_contradicts_constraint(
    threshold: Threshold, decision: DecisionResponse
) -> str | None:
    """Deterministic, narrow check: a numeric threshold whose value
    exceeds the decision's own stated budget, when the threshold's
    variable is textually about cost/budget/investment - never a broad
    heuristic that could misfire on unrelated variables."""
    if decision.budget is None or threshold.threshold_value is None:
        return None
    if not _is_numeric(threshold.threshold_value):
        return None
    variable_lower = threshold.variable.lower()
    if not any(word in variable_lower for word in ("cost", "budget", "investment", "spend")):
        return None
    value = float(threshold.threshold_value)
    if value > decision.budget:
        return (
            f"Threshold '{threshold.variable}' ({value}) exceeds the decision's own stated "
            f"budget ({decision.budget})."
        )
    return None


# --- 7: experiment quality --------------------------------------------------------


def check_experiment_quality(
    quality_id: str,
    signals: DecisionQualitySignals,
    primary_uncertainty_variable: str | None = None,
) -> list[QualityCheck]:
    """Spec section 7: never invents missing experiment details - only
    flags the absence of a field the Experiment Planner should have set."""
    checks: list[QualityCheck] = []
    threshold_by_id = {str(t.id): t for t in signals.thresholds}

    for experiment in signals.experiments:
        missing_fields = []
        if not experiment.success_criteria:
            missing_fields.append("success_criteria")
        if not experiment.failure_criteria:
            missing_fields.append("failure_criteria")
        if not experiment.decision_rule:
            missing_fields.append("decision_rule")

        if missing_fields:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.EXPERIMENT,
                    "experiment_has_required_fields",
                    QualityCheckStatus.WARNING,
                    QualityCheckSeverity.MEDIUM,
                    f"Experiment '{experiment.title}' is missing: {', '.join(missing_fields)}.",
                    related_entity_type="experiment",
                    related_entity_id=str(experiment.id),
                )
            )
        else:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.EXPERIMENT,
                    "experiment_has_required_fields",
                    QualityCheckStatus.PASSED,
                    QualityCheckSeverity.INFO,
                    f"Experiment '{experiment.title}' has success/failure criteria and a "
                    "decision rule.",
                    related_entity_type="experiment",
                    related_entity_id=str(experiment.id),
                )
            )

        if (
            not experiment.target_threshold_id
            or experiment.target_threshold_id not in threshold_by_id
        ):
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.EXPERIMENT,
                    "experiment_targets_real_threshold",
                    QualityCheckStatus.FAILED,
                    QualityCheckSeverity.HIGH,
                    f"Experiment '{experiment.title}' does not target a real, persisted "
                    "threshold.",
                    related_entity_type="experiment",
                    related_entity_id=str(experiment.id),
                )
            )

        alignment_issue = _experiment_alignment_issue(experiment, primary_uncertainty_variable)
        if alignment_issue:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.EXPERIMENT,
                    "experiment_targets_primary_uncertainty",
                    QualityCheckStatus.WARNING,
                    QualityCheckSeverity.MEDIUM,
                    alignment_issue,
                    related_entity_type="experiment",
                    related_entity_id=str(experiment.id),
                    recommendation="Consider whether a different experiment would more "
                    "directly test the primary uncertainty.",
                )
            )

    return checks


def _experiment_alignment_issue(
    experiment: Experiment, primary_uncertainty_variable: str | None
) -> str | None:
    """Deterministic, structural alignment check - never a semantic
    judgment of "is this a good test." Only flags a MISMATCH when the
    primary uncertainty's variable shares no real, structured overlap
    with anything the experiment says it measures (`variable_to_test`,
    `evidence_to_collect`) - a real absence of connection, never a guess
    about experiment quality beyond that.
    """
    if not primary_uncertainty_variable:
        return None
    primary_key = normalize_variable(primary_uncertainty_variable)
    if primary_key is None:
        return None

    candidate_texts = [experiment.variable_to_test or ""] + list(experiment.evidence_to_collect)
    for text in candidate_texts:
        if normalize_variable(text) == primary_key:
            return None

    return (
        f"Experiment '{experiment.title}' does not clearly state that it measures the "
        f"primary uncertainty ('{primary_uncertainty_variable}')."
    )


# --- 8: provenance quality --------------------------------------------------------


def check_provenance_quality(
    quality_id: str, signals: DecisionQualitySignals, user_id: str
) -> list[QualityCheck]:
    """Spec section 8: traces Decision -> Assumption/RegretScenario ->
    Threshold -> Experiment -> Result -> Re-evaluation, and Learning ->
    Cross-Decision Pattern. A pattern that names a decision belonging to
    a DIFFERENT user is a CRITICAL isolation error, never merely a
    warning."""
    checks: list[QualityCheck] = []

    experiment_ids = {str(e.id) for e in signals.experiments}
    for result in signals.experiment_results:
        if str(result.experiment_id) not in experiment_ids:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.PROVENANCE,
                    "result_references_real_experiment",
                    QualityCheckStatus.FAILED,
                    QualityCheckSeverity.HIGH,
                    f"Experiment result {result.id} references experiment "
                    f"{result.experiment_id}, which is not one of this decision's experiments.",
                    related_entity_type="experiment_result",
                    related_entity_id=str(result.id),
                )
            )

    result_ids = {str(r.id) for r in signals.experiment_results}
    for reeval in signals.reevaluations:
        if str(reeval.experiment_result_id) not in result_ids:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.PROVENANCE,
                    "reevaluation_references_real_result",
                    QualityCheckStatus.FAILED,
                    QualityCheckSeverity.HIGH,
                    f"Re-evaluation {reeval.id} references experiment result "
                    f"{reeval.experiment_result_id}, which does not exist for this decision.",
                    related_entity_type="re_evaluation",
                    related_entity_id=str(reeval.id),
                )
            )

    decision_id_str = str(signals.decision.id)
    for pattern in signals.cross_decision_patterns:
        if pattern.user_id != user_id:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.PROVENANCE,
                    "pattern_respects_user_isolation",
                    QualityCheckStatus.FAILED,
                    QualityCheckSeverity.CRITICAL,
                    f"Cross-decision pattern {pattern.pattern_id} is attributed to a "
                    "different user than this decision - this is a critical isolation error.",
                    related_entity_type="cross_decision_pattern",
                    related_entity_id=pattern.pattern_id,
                )
            )
        elif decision_id_str not in pattern.supporting_decision_ids and (
            decision_id_str not in pattern.contradicting_decision_ids
        ):
            # Pattern was returned for this decision but doesn't actually
            # name it - a broken provenance link, never assumed benign.
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.PROVENANCE,
                    "pattern_names_this_decision",
                    QualityCheckStatus.WARNING,
                    QualityCheckSeverity.MEDIUM,
                    f"Cross-decision pattern {pattern.pattern_id} was surfaced for this "
                    "decision but does not list it as supporting or contradicting evidence.",
                    related_entity_type="cross_decision_pattern",
                    related_entity_id=pattern.pattern_id,
                )
            )
        else:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.PROVENANCE,
                    "pattern_names_this_decision",
                    QualityCheckStatus.PASSED,
                    QualityCheckSeverity.INFO,
                    f"Cross-decision pattern {pattern.pattern_id} correctly names this "
                    "decision as evidence.",
                    related_entity_type="cross_decision_pattern",
                    related_entity_id=pattern.pattern_id,
                )
            )

    if not checks:
        checks.append(
            _make_check(
                quality_id,
                QualityCheckCategory.PROVENANCE,
                "no_provenance_issues_detected",
                QualityCheckStatus.PASSED,
                QualityCheckSeverity.INFO,
                "Every checked relationship (result -> experiment, re-evaluation -> result, "
                "pattern -> decision/user) traces back to a real, correctly-scoped record.",
            )
        )

    return checks


# --- 9: consistency ------------------------------------------------------------------


def check_consistency(quality_id: str, signals: DecisionQualitySignals) -> list[QualityCheck]:
    """Spec section 9: detects contradictions across structured
    records - never decides which record is "correct," only flags the
    disagreement and preserves both canonical records unchanged."""
    checks: list[QualityCheck] = []
    assumptions_by_id = {str(a.id): a for a in signals.assumptions}

    for reeval in signals.reevaluations:
        for assumption_reeval in reeval.assumption_reevaluations:
            assumption = assumptions_by_id.get(assumption_reeval.assumption_id)
            if assumption is None:
                continue
            if (
                assumption_reeval.new_status.value in {"contradicted", "still_uncertain"}
                and assumption.evidence_status.value == "supported"
            ):
                checks.append(
                    _make_check(
                        quality_id,
                        QualityCheckCategory.CONSISTENCY,
                        "assumption_status_matches_reevaluation",
                        QualityCheckStatus.FAILED,
                        QualityCheckSeverity.HIGH,
                        f"Assumption '{assumption.statement}' is recorded as 'supported', but "
                        f"a re-evaluation marked it '{assumption_reeval.new_status.value}'.",
                        related_entity_type="assumption",
                        related_entity_id=assumption.id and str(assumption.id),
                        evidence_ids=[str(reeval.id)],
                    )
                )

        for comparison in reeval.threshold_comparisons:
            threshold = next(
                (t for t in signals.thresholds if str(t.id) == comparison.threshold_id), None
            )
            if threshold is None:
                continue
            if (
                comparison.status in _MISSED_LIKE
                and (threshold.validation_status or "").lower() == "validated"
            ):
                checks.append(
                    _make_check(
                        quality_id,
                        QualityCheckCategory.CONSISTENCY,
                        "threshold_status_matches_comparison",
                        QualityCheckStatus.FAILED,
                        QualityCheckSeverity.HIGH,
                        f"Threshold '{threshold.variable}' is marked 'validated', but its "
                        "most recent real comparison shows the threshold was missed.",
                        related_entity_type="threshold",
                        related_entity_id=str(threshold.id),
                        evidence_ids=[str(reeval.id)],
                    )
                )

        assessment = reeval.decision_assessment
        if assessment.status.value == "strengthened" and any(
            c.status in _MISSED_LIKE for c in reeval.threshold_comparisons
        ):
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.CONSISTENCY,
                    "assessment_matches_threshold_comparisons",
                    QualityCheckStatus.WARNING,
                    QualityCheckSeverity.MEDIUM,
                    "This re-evaluation reports the decision was 'strengthened' even though "
                    "at least one threshold comparison in the same re-evaluation was missed.",
                    related_entity_type="re_evaluation",
                    related_entity_id=str(reeval.id),
                )
            )

    if not checks:
        checks.append(
            _make_check(
                quality_id,
                QualityCheckCategory.CONSISTENCY,
                "no_consistency_issues_detected",
                QualityCheckStatus.PASSED,
                QualityCheckSeverity.INFO,
                "No contradiction was found between assumption/threshold status and the "
                "real re-evaluation records that produced them.",
            )
        )

    return checks


# --- 10: freshness --------------------------------------------------------------------


def check_freshness(quality_id: str, signals: DecisionQualitySignals) -> list[QualityCheck]:
    """Spec section 10: detects stale analysis - new evidence/results
    that arrived after the analysis run completed, with no re-evaluation
    reflecting them yet."""
    checks: list[QualityCheck] = []
    if signals.analysis_completed_at is None:
        return checks

    latest_reeval_at = max((r.created_at for r in signals.reevaluations), default=None)
    newer_results = [
        r for r in signals.experiment_results if r.completed_at > signals.analysis_completed_at
    ]
    newer_results_without_reeval = [
        r for r in newer_results if latest_reeval_at is None or r.completed_at > latest_reeval_at
    ]

    if newer_results_without_reeval:
        checks.append(
            _make_check(
                quality_id,
                QualityCheckCategory.FRESHNESS,
                "analysis_reflects_latest_results",
                QualityCheckStatus.WARNING,
                QualityCheckSeverity.MEDIUM,
                f"{len(newer_results_without_reeval)} experiment result(s) arrived after the "
                "analysis was completed, and no re-evaluation yet reflects them.",
                recommendation="Submit results through the normal flow so a re-evaluation is "
                "produced, or re-run analysis.",
            )
        )
    else:
        checks.append(
            _make_check(
                quality_id,
                QualityCheckCategory.FRESHNESS,
                "analysis_reflects_latest_results",
                QualityCheckStatus.PASSED,
                QualityCheckSeverity.INFO,
                "No experiment result has arrived without a corresponding re-evaluation.",
            )
        )

    newer_evidence = [e for e in signals.evidence if e.created_at > signals.analysis_completed_at]
    if newer_evidence:
        checks.append(
            _make_check(
                quality_id,
                QualityCheckCategory.FRESHNESS,
                "analysis_reflects_new_evidence",
                QualityCheckStatus.WARNING,
                QualityCheckSeverity.LOW,
                f"{len(newer_evidence)} evidence file(s) were uploaded after this analysis "
                "run completed.",
                recommendation="Re-run analysis to incorporate the new evidence.",
            )
        )

    return checks


# --- 11: historical learning check ------------------------------------------------


def check_historical_learning(
    quality_id: str, signals: DecisionQualitySignals
) -> list[QualityCheck]:
    """Spec section 11: cross-decision patterns must never dominate
    current evidence - detects a pattern whose direction contradicts
    what the CURRENT decision's own real, observed results already
    show, and recommends prioritizing current evidence. Never modifies
    the historical pattern."""
    checks: list[QualityCheck] = []

    current_validated_variables = {
        normalize_variable(t.variable)
        for t in signals.thresholds
        if (t.validation_status or "").lower() == "validated"
    }
    current_validated_variables.discard(None)

    for pattern in signals.cross_decision_patterns:
        if pattern.status not in {PatternStatus.ESTABLISHED, PatternStatus.REPEATED}:
            continue
        pattern_key = normalize_variable(pattern.variable) if pattern.variable else None
        if pattern_key is None:
            continue
        raises_concern = pattern.pattern_type.value in {
            "recurring_failed_assumption",
            "recurring_threshold_failure",
        }
        if raises_concern and pattern_key in current_validated_variables:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.HISTORICAL,
                    "historical_pattern_vs_current_evidence",
                    QualityCheckStatus.WARNING,
                    QualityCheckSeverity.MEDIUM,
                    f"A historical pattern ('{pattern.title}') suggests this variable has "
                    "repeatedly underperformed in the past, but current evidence for this "
                    "decision shows it validated.",
                    related_entity_type="cross_decision_pattern",
                    related_entity_id=pattern.pattern_id,
                    recommendation="Prioritize the current decision's own evidence over "
                    "historical pattern when assessing this decision.",
                )
            )

    return checks


def check_historical_reliance(
    quality_id: str,
    historical_signal: HistoricalLearningSignal,
    evidence_backed_variable_count: int,
) -> list[QualityCheck]:
    """Spec section 11 (recommendation dependency): warns when a
    recommendation would rely on a STRONG historical signal while the
    current decision has little of its own direct evidence yet."""
    if historical_signal != HistoricalLearningSignal.STRONG or evidence_backed_variable_count > 0:
        return [
            _make_check(
                quality_id,
                QualityCheckCategory.HISTORICAL,
                "recommendation_not_overreliant_on_history",
                QualityCheckStatus.PASSED,
                QualityCheckSeverity.INFO,
                "This decision's recommendations are not solely dependent on historical "
                "pattern signal.",
            )
        ]
    return [
        _make_check(
            quality_id,
            QualityCheckCategory.HISTORICAL,
            "recommendation_not_overreliant_on_history",
            QualityCheckStatus.WARNING,
            QualityCheckSeverity.MEDIUM,
            "The strongest signal behind this recommendation is a historical cross-decision "
            "pattern, with no current, decision-specific evidence yet.",
            recommendation="Seek current evidence for this decision before relying heavily on "
            "historical pattern alone.",
        )
    ]


# --- 12: completeness -----------------------------------------------------------------


def check_completeness(quality_id: str, signals: DecisionQualitySignals) -> list[QualityCheck]:
    """Spec section 12: a missing REQUIRED stage is a warning; a missing
    RECOMMENDED stage is low-severity; a missing OPTIONAL stage is never
    flagged as a problem at all."""
    checks: list[QualityCheck] = []
    present = signals.analysis_result_keys

    for stage in sorted(_REQUIRED_STAGES):
        if stage not in present:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.COMPLETENESS,
                    "required_stage_present",
                    QualityCheckStatus.WARNING,
                    QualityCheckSeverity.HIGH,
                    f"Required analysis stage '{stage}' has no recorded output for this run.",
                    related_entity_type="analysis_run",
                    related_entity_id=signals.analysis_run_id,
                )
            )
        else:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.COMPLETENESS,
                    "required_stage_present",
                    QualityCheckStatus.PASSED,
                    QualityCheckSeverity.INFO,
                    f"Required stage '{stage}' produced output for this run.",
                    related_entity_type="analysis_run",
                    related_entity_id=signals.analysis_run_id,
                )
            )

    for stage in sorted(_RECOMMENDED_STAGES):
        if stage not in present:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.COMPLETENESS,
                    "recommended_stage_present",
                    QualityCheckStatus.WARNING,
                    QualityCheckSeverity.LOW,
                    f"Recommended stage '{stage}' has no recorded output for this run.",
                    related_entity_type="analysis_run",
                    related_entity_id=signals.analysis_run_id,
                )
            )

    for stage in sorted(_OPTIONAL_STAGES):
        if stage in present:
            checks.append(
                _make_check(
                    quality_id,
                    QualityCheckCategory.COMPLETENESS,
                    "optional_stage_present",
                    QualityCheckStatus.PASSED,
                    QualityCheckSeverity.INFO,
                    f"Optional stage '{stage}' also ran for this decision.",
                    related_entity_type="analysis_run",
                    related_entity_id=signals.analysis_run_id,
                )
            )
        # Absence of an optional stage is never flagged (spec: "Do not
        # mark optional stages as failures") - not even as a NOT_APPLICABLE
        # row, to avoid diluting the checklist with expected non-events.

    return checks
