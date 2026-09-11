"""Tests for `app.quality.rules` - the deterministic quality-check core
(REGRET ENGINE 2.0, Step 24).

No LLM/Strands invocation happens anywhere in this file, and no
DynamoDB either - these build `DecisionQualitySignals` bundles directly
from plain constructed schema objects, mirroring
`test_learning_pattern_detector.py`'s exact approach.
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.learning.schemas import CrossDecisionPattern, PatternConfidence, PatternStatus, PatternType
from app.quality import rules
from app.quality.rules import DecisionQualitySignals
from app.quality.schemas import QualityCheckStatus
from app.schemas.decision import DecisionResponse, DecisionStatus
from app.schemas.decision_resources import (
    Assumption,
    AssumptionReevaluation,
    AssumptionReevaluationStatus,
    AssumptionSource,
    DecisionAssessment,
    DecisionAssessmentStatus,
    EvidenceStatus,
    Experiment,
    ExperimentResult,
    ExperimentStatus,
    ReEvaluation,
    Threshold,
    ThresholdComparison,
    ThresholdComparisonStatus,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
QUALITY_ID = "quality-1"


def _decision(**overrides) -> DecisionResponse:
    defaults = {
        "id": uuid4(),
        "title": "Open a cloud kitchen",
        "description": "x",
        "status": DecisionStatus.NEEDS_VALIDATION,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    return DecisionResponse(**defaults)


def _assumption(**overrides) -> Assumption:
    defaults = {
        "id": uuid4(),
        "decision_id": uuid4(),
        "statement": "Customers will reorder frequently.",
        "source": AssumptionSource.IMPLICIT,
        "importance": "critical",
        "confidence": 0.2,
        "evidence_status": EvidenceStatus.NOT_ADDRESSED,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    return Assumption(**defaults)


def _threshold(**overrides) -> Threshold:
    defaults = {
        "id": uuid4(),
        "decision_id": uuid4(),
        "variable": "Repeat-order rate",
        "threshold_type": "numeric",
        "threshold_value": "24",
        "unit": "%",
        "related_assumption_ids": [],
        "related_regret_scenario_ids": [],
        "validation_status": "provisional",
        "created_at": NOW,
    }
    defaults.update(overrides)
    return Threshold(**defaults)


def _experiment(**overrides) -> Experiment:
    defaults = {
        "id": uuid4(),
        "decision_id": uuid4(),
        "title": "Retention pilot",
        "hypothesis": "x",
        "target_threshold_id": None,
        "success_criteria": ["x"],
        "failure_criteria": ["x"],
        "decision_rule": "x",
        "status": ExperimentStatus.RECOMMENDED,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    return Experiment(**defaults)


def test_evidence_check_fails_when_finding_references_missing_evidence() -> None:
    from app.schemas.decision_resources import EvidenceFinding

    finding = EvidenceFinding(
        id=uuid4(),
        decision_id=uuid4(),
        evidence_id=uuid4(),
        claim="x",
        support_level="strong",
        credibility="high",
        created_at=NOW,
    )
    signals = DecisionQualitySignals(decision=_decision(), evidence=[], evidence_findings=[finding])

    checks = rules.check_evidence_quality(QUALITY_ID, signals)
    failed = [c for c in checks if c.name == "finding_references_real_evidence"]

    assert len(failed) == 1
    assert failed[0].status == QualityCheckStatus.FAILED


def test_evidence_check_warns_when_critical_assumption_has_no_evidence() -> None:
    assumption = _assumption(importance="critical")
    signals = DecisionQualitySignals(decision=_decision(), assumptions=[assumption])

    checks = rules.check_evidence_quality(QUALITY_ID, signals)
    warning = next(c for c in checks if c.name == "critical_assumption_has_evidence")

    assert warning.status == QualityCheckStatus.WARNING
    assert warning.related_entity_id == str(assumption.id)


def test_evidence_check_passes_when_critical_assumption_has_real_evidence() -> None:
    from app.schemas.decision_resources import Evidence, EvidenceFinding, SourceType

    assumption = _assumption(importance="critical")
    evidence = Evidence(
        id=uuid4(),
        decision_id=assumption.decision_id,
        title="x",
        source_type=SourceType.DOCUMENT,
        created_at=NOW,
    )
    finding = EvidenceFinding(
        id=uuid4(),
        decision_id=assumption.decision_id,
        evidence_id=evidence.id,
        claim="x",
        support_level="strong",
        related_assumption_ids=[str(assumption.id)],
        created_at=NOW,
    )
    signals = DecisionQualitySignals(
        decision=_decision(),
        assumptions=[assumption],
        evidence=[evidence],
        evidence_findings=[finding],
    )

    checks = rules.check_evidence_quality(QUALITY_ID, signals)
    names = {c.name for c in checks if c.status == QualityCheckStatus.WARNING}

    assert "critical_assumption_has_evidence" not in names


def test_assumption_check_flags_high_confidence_with_unresolved_evidence() -> None:
    assumption = _assumption(confidence=0.9, evidence_status=EvidenceStatus.NOT_ADDRESSED)
    signals = DecisionQualitySignals(decision=_decision(), assumptions=[assumption])

    checks = rules.check_assumption_quality(QUALITY_ID, signals)
    failure = next(c for c in checks if c.name == "confidence_matches_evidence_status")

    assert failure.status == QualityCheckStatus.FAILED
    assert failure.severity.value == "high"


def test_assumption_check_flags_threshold_referencing_missing_assumption() -> None:
    threshold = _threshold(related_assumption_ids=["does-not-exist"])
    signals = DecisionQualitySignals(decision=_decision(), thresholds=[threshold])

    checks = rules.check_assumption_quality(QUALITY_ID, signals)
    failure = next(c for c in checks if c.name == "threshold_assumption_exists")

    assert failure.status == QualityCheckStatus.FAILED


def test_threshold_check_warns_on_missing_unit() -> None:
    threshold = _threshold(unit=None, threshold_value="24", threshold_type="numeric")
    signals = DecisionQualitySignals(decision=_decision(), thresholds=[threshold])

    checks = rules.check_threshold_quality(QUALITY_ID, signals)
    warning = next(c for c in checks if c.name == "threshold_has_unit")

    assert warning.status == QualityCheckStatus.WARNING


def test_threshold_check_warns_when_not_connected_to_regret_scenario() -> None:
    threshold = _threshold(related_regret_scenario_ids=[])
    signals = DecisionQualitySignals(decision=_decision(), thresholds=[threshold])

    checks = rules.check_threshold_quality(QUALITY_ID, signals)
    warning = next(c for c in checks if c.name == "threshold_connected_to_regret_scenario")

    assert warning.status == QualityCheckStatus.WARNING


def test_threshold_check_warns_when_completed_experiment_never_compared() -> None:
    threshold = _threshold()
    experiment = _experiment(
        target_threshold_id=str(threshold.id), status=ExperimentStatus.COMPLETED
    )
    signals = DecisionQualitySignals(
        decision=_decision(), thresholds=[threshold], experiments=[experiment]
    )

    checks = rules.check_threshold_quality(QUALITY_ID, signals)
    warning = next(c for c in checks if c.name == "threshold_evaluated_after_experiment")

    assert warning.status == QualityCheckStatus.WARNING


def test_threshold_check_flags_budget_contradiction() -> None:
    decision = _decision(budget=500000)
    threshold = _threshold(variable="Total investment cost", threshold_value="900000", unit="INR")
    signals = DecisionQualitySignals(decision=decision, thresholds=[threshold])

    checks = rules.check_threshold_quality(QUALITY_ID, signals)
    warning = next(c for c in checks if c.name == "threshold_matches_user_constraints")

    assert warning.status == QualityCheckStatus.WARNING
    assert "exceeds" in warning.message


def test_experiment_check_warns_on_missing_required_fields() -> None:
    experiment = _experiment(success_criteria=[], failure_criteria=[], decision_rule=None)
    signals = DecisionQualitySignals(decision=_decision(), experiments=[experiment])

    checks = rules.check_experiment_quality(QUALITY_ID, signals)
    warning = next(c for c in checks if c.name == "experiment_has_required_fields")

    assert warning.status == QualityCheckStatus.WARNING


def test_experiment_check_fails_when_target_threshold_missing() -> None:
    experiment = _experiment(target_threshold_id=None)
    signals = DecisionQualitySignals(decision=_decision(), experiments=[experiment])

    checks = rules.check_experiment_quality(QUALITY_ID, signals)
    failure = next(c for c in checks if c.name == "experiment_targets_real_threshold")

    assert failure.status == QualityCheckStatus.FAILED


def test_experiment_check_warns_on_mismatched_primary_uncertainty() -> None:
    experiment = _experiment(
        variable_to_test="Pricing tolerance", evidence_to_collect=["pricing survey"]
    )
    signals = DecisionQualitySignals(decision=_decision(), experiments=[experiment])

    checks = rules.check_experiment_quality(
        QUALITY_ID, signals, primary_uncertainty_variable="Customer retention rate"
    )
    warning = next(c for c in checks if c.name == "experiment_targets_primary_uncertainty")

    assert warning.status == QualityCheckStatus.WARNING


def test_experiment_check_does_not_warn_when_experiment_matches_uncertainty() -> None:
    experiment = _experiment(variable_to_test="Customer retention rate")
    signals = DecisionQualitySignals(decision=_decision(), experiments=[experiment])

    checks = rules.check_experiment_quality(
        QUALITY_ID, signals, primary_uncertainty_variable="Customer retention rate"
    )
    names = {c.name for c in checks}

    assert "experiment_targets_primary_uncertainty" not in names


def test_provenance_check_flags_result_referencing_unknown_experiment() -> None:
    result = ExperimentResult(
        id=uuid4(),
        decision_id=uuid4(),
        experiment_id=uuid4(),
        outcome="success",
        summary="x",
        completed_at=NOW,
    )
    signals = DecisionQualitySignals(decision=_decision(), experiment_results=[result])

    checks = rules.check_provenance_quality(QUALITY_ID, signals, user_id="user-a")
    failure = next(c for c in checks if c.name == "result_references_real_experiment")

    assert failure.status == QualityCheckStatus.FAILED


def test_provenance_check_flags_cross_user_pattern_as_critical() -> None:
    pattern = CrossDecisionPattern(
        pattern_id="p1",
        user_id="user-b",
        pattern_type=PatternType.RECURRING_FAILED_ASSUMPTION,
        title="x",
        statement="x",
        normalized_key="x",
        occurrence_count=2,
        supporting_decision_ids=["dec-1"],
        evidence_count=2,
        confidence=PatternConfidence.MEDIUM,
        confidence_basis="x",
        first_seen_at=NOW,
        last_seen_at=NOW,
        status=PatternStatus.EMERGING,
        created_at=NOW,
        updated_at=NOW,
    )
    signals = DecisionQualitySignals(decision=_decision(), cross_decision_patterns=[pattern])

    checks = rules.check_provenance_quality(QUALITY_ID, signals, user_id="user-a")
    critical = next(c for c in checks if c.name == "pattern_respects_user_isolation")

    assert critical.status == QualityCheckStatus.FAILED
    assert critical.severity.value == "critical"


def test_provenance_check_passes_with_clean_records() -> None:
    signals = DecisionQualitySignals(decision=_decision())

    checks = rules.check_provenance_quality(QUALITY_ID, signals, user_id="user-a")

    assert any(c.status == QualityCheckStatus.PASSED for c in checks)
    assert not any(c.status == QualityCheckStatus.FAILED for c in checks)


def test_consistency_check_flags_assumption_supported_but_reevaluation_contradicted() -> None:
    assumption = _assumption(evidence_status=EvidenceStatus.SUPPORTED)
    reeval = ReEvaluation(
        id=uuid4(),
        decision_id=uuid4(),
        experiment_id=uuid4(),
        experiment_result_id=uuid4(),
        previous_assessment="x",
        new_assessment="y",
        assumption_reevaluations=[
            AssumptionReevaluation(
                assumption_id=str(assumption.id),
                new_status=AssumptionReevaluationStatus.CONTRADICTED,
                explanation="x",
            )
        ],
        decision_assessment=DecisionAssessment(
            status=DecisionAssessmentStatus.WEAKENED,
            confidence=0.6,
            summary="x",
            recommended_next_step="x",
        ),
        key_learning="x",
        recommended_next_step="x",
        created_at=NOW,
    )
    signals = DecisionQualitySignals(
        decision=_decision(), assumptions=[assumption], reevaluations=[reeval]
    )

    checks = rules.check_consistency(QUALITY_ID, signals)
    failure = next(c for c in checks if c.name == "assumption_status_matches_reevaluation")

    assert failure.status == QualityCheckStatus.FAILED
    assert failure.severity.value == "high"


def test_consistency_check_flags_validated_threshold_with_missed_comparison() -> None:
    threshold = _threshold(validation_status="validated")
    reeval = ReEvaluation(
        id=uuid4(),
        decision_id=uuid4(),
        experiment_id=uuid4(),
        experiment_result_id=uuid4(),
        previous_assessment="x",
        new_assessment="y",
        threshold_comparisons=[
            ThresholdComparison(
                threshold_id=str(threshold.id),
                variable=threshold.variable,
                status=ThresholdComparisonStatus.MISSED,
                explanation="x",
            )
        ],
        decision_assessment=DecisionAssessment(
            status=DecisionAssessmentStatus.WEAKENED,
            confidence=0.6,
            summary="x",
            recommended_next_step="x",
        ),
        key_learning="x",
        recommended_next_step="x",
        created_at=NOW,
    )
    signals = DecisionQualitySignals(
        decision=_decision(), thresholds=[threshold], reevaluations=[reeval]
    )

    checks = rules.check_consistency(QUALITY_ID, signals)
    failure = next(c for c in checks if c.name == "threshold_status_matches_comparison")

    assert failure.status == QualityCheckStatus.FAILED


def test_consistency_check_passes_with_no_contradictions() -> None:
    signals = DecisionQualitySignals(decision=_decision())

    checks = rules.check_consistency(QUALITY_ID, signals)

    assert any(c.name == "no_consistency_issues_detected" for c in checks)


def test_freshness_check_warns_on_stale_analysis() -> None:
    experiment = _experiment()
    result = ExperimentResult(
        id=uuid4(),
        decision_id=uuid4(),
        experiment_id=experiment.id,
        outcome="success",
        summary="x",
        completed_at=datetime(2026, 1, 10, tzinfo=UTC),
    )
    signals = DecisionQualitySignals(
        decision=_decision(),
        experiments=[experiment],
        experiment_results=[result],
        analysis_completed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    checks = rules.check_freshness(QUALITY_ID, signals)
    warning = next(c for c in checks if c.name == "analysis_reflects_latest_results")

    assert warning.status == QualityCheckStatus.WARNING


def test_freshness_check_passes_when_no_new_results() -> None:
    signals = DecisionQualitySignals(decision=_decision(), analysis_completed_at=NOW)

    checks = rules.check_freshness(QUALITY_ID, signals)
    passed = next(c for c in checks if c.name == "analysis_reflects_latest_results")

    assert passed.status == QualityCheckStatus.PASSED


def test_completeness_check_warns_on_missing_required_stage() -> None:
    signals = DecisionQualitySignals(
        decision=_decision(), analysis_result_keys={"decision_analyzer"}
    )

    checks = rules.check_completeness(QUALITY_ID, signals)
    missing = [
        c
        for c in checks
        if c.name == "required_stage_present" and c.status == QualityCheckStatus.WARNING
    ]

    assert len(missing) > 0


def test_completeness_check_never_flags_missing_optional_stage() -> None:
    signals = DecisionQualitySignals(decision=_decision(), analysis_result_keys=set())

    checks = rules.check_completeness(QUALITY_ID, signals)
    optional_failures = [
        c
        for c in checks
        if c.name in {"optional_stage_present"}
        and c.status in {QualityCheckStatus.FAILED, QualityCheckStatus.WARNING}
    ]

    assert optional_failures == []


def test_historical_check_flags_pattern_vs_current_evidence_conflict() -> None:
    threshold = _threshold(variable="Customer retention rate", validation_status="validated")
    pattern = CrossDecisionPattern(
        pattern_id="p1",
        user_id="user-a",
        pattern_type=PatternType.RECURRING_THRESHOLD_FAILURE,
        title="Retention has repeatedly failed.",
        statement="x",
        normalized_key="customer retention",
        variable="Customer retention rate",
        occurrence_count=3,
        supporting_decision_ids=["d1", "d2", "d3"],
        evidence_count=3,
        confidence=PatternConfidence.HIGH,
        confidence_basis="x",
        first_seen_at=NOW,
        last_seen_at=NOW,
        status=PatternStatus.ESTABLISHED,
        created_at=NOW,
        updated_at=NOW,
    )
    signals = DecisionQualitySignals(
        decision=_decision(), thresholds=[threshold], cross_decision_patterns=[pattern]
    )

    checks = rules.check_historical_learning(QUALITY_ID, signals)

    assert any(c.name == "historical_pattern_vs_current_evidence" for c in checks)
