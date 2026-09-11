"""Tests for `app.learning.pattern_detector` - the deterministic
recurring-pattern detection core (REGRET ENGINE 2.0, Step 23).

No LLM/Strands invocation happens anywhere in this file, and no
DynamoDB either - these tests build `DecisionSignals` bundles directly
from plain constructed schema objects, mirroring how
`app.learning.service.CrossDecisionLearningService._load_signals` would
assemble them, without needing a running table.
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.learning.pattern_detector import (
    DecisionSignals,
    compute_confidence,
    compute_status,
    detect_patterns,
    deterministic_occurrence_id,
    deterministic_pattern_id,
)
from app.learning.schemas import PatternConfidence, PatternStatus, PatternType
from app.memory.memory_schemas import LearningSourceType, LearningType, MemoryLearning
from app.schemas.decision_resources import (
    Assumption,
    AssumptionSource,
    EvidenceStatus,
    Experiment,
    ExperimentOutcome,
    ExperimentResult,
    Threshold,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _assumption(
    decision_id, statement="Customer retention will be high", **overrides
) -> Assumption:
    defaults = {
        "id": uuid4(),
        "decision_id": decision_id,
        "statement": statement,
        "source": AssumptionSource.IMPLICIT,
        "importance": "critical",
        "confidence": 0.2,
        "evidence_status": EvidenceStatus.NOT_ADDRESSED,
        "dependency": None,
        "failure_consequence": None,
        "reason": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    return Assumption(**defaults)


def _threshold(
    decision_id, variable="Customer retention rate", related_assumption_ids=None, **overrides
) -> Threshold:
    defaults = {
        "id": uuid4(),
        "decision_id": decision_id,
        "variable": variable,
        "threshold_type": "numeric",
        "direction": "below",
        "threshold_value": "24",
        "related_assumption_ids": related_assumption_ids or [],
        "related_regret_scenario_ids": [],
        "validation_status": "validated",
        "created_at": NOW,
    }
    defaults.update(overrides)
    return Threshold(**defaults)


def _experiment(
    decision_id, target_threshold_id=None, experiment_type="pilot", **overrides
) -> Experiment:
    defaults = {
        "id": uuid4(),
        "decision_id": decision_id,
        "title": "Retention pilot",
        "hypothesis": "Retention holds",
        "target_threshold_id": target_threshold_id,
        "experiment_type": experiment_type,
        "status": "completed",
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    return Experiment(**defaults)


def _experiment_result(
    decision_id, experiment_id, outcome=ExperimentOutcome.SUCCESS, **overrides
) -> ExperimentResult:
    defaults = {
        "id": uuid4(),
        "decision_id": decision_id,
        "experiment_id": experiment_id,
        "outcome": outcome,
        "summary": "Result observed.",
        "completed_at": NOW,
    }
    defaults.update(overrides)
    return ExperimentResult(**defaults)


def _learning(
    decision_id,
    learning_type,
    related_assumption_ids=None,
    related_threshold_ids=None,
    confidence=0.6,
    statement="Something was learned.",
    source_type=LearningSourceType.RE_EVALUATION,
    **overrides,
) -> MemoryLearning:
    defaults = {
        "learning_id": uuid4(),
        "memory_id": uuid4(),
        "decision_id": decision_id,
        "statement": statement,
        "learning_type": learning_type,
        "source_type": source_type,
        "source_id": uuid4(),
        "confidence": confidence,
        "related_assumption_ids": related_assumption_ids or [],
        "related_threshold_ids": related_threshold_ids or [],
        "related_regret_scenario_ids": [],
        "created_at": NOW,
    }
    defaults.update(overrides)
    return MemoryLearning(**defaults)


def _signals_with_assumption_outcome(
    learning_type: LearningType, variable: str, decision_id=None
) -> DecisionSignals:
    decision_id = decision_id or str(uuid4())
    assumption = _assumption(decision_id, statement=variable)
    threshold = _threshold(
        decision_id, variable=variable, related_assumption_ids=[str(assumption.id)]
    )
    learning = _learning(
        decision_id,
        learning_type,
        related_assumption_ids=[str(assumption.id)],
        statement=f"{variable}: observed.",
    )
    return DecisionSignals(
        decision_id=decision_id,
        assumptions=[assumption],
        thresholds=[threshold],
        learnings=[learning],
    )


# --- 1: one occurrence does not create a strong pattern -----------------------


def test_single_decision_produces_no_pattern() -> None:
    signals = [
        _signals_with_assumption_outcome(LearningType.ASSUMPTION_FAILED, "Customer retention")
    ]

    patterns = detect_patterns(signals)

    assert patterns == []


# --- 2: two consistent occurrences create an emerging/repeated pattern --------


def test_two_consistent_decisions_create_a_failed_assumption_pattern() -> None:
    signals = [
        _signals_with_assumption_outcome(LearningType.ASSUMPTION_FAILED, "Customer retention"),
        _signals_with_assumption_outcome(LearningType.ASSUMPTION_WEAKENED, "Customer retention"),
    ]

    patterns = detect_patterns(signals)
    failed = [p for p in patterns if p.pattern_type == PatternType.RECURRING_FAILED_ASSUMPTION]

    assert len(failed) == 1
    assert len(set(o.decision_id for o in failed[0].occurrences)) == 2


# --- 3: three consistent occurrences can establish a pattern -------------------


def test_three_consistent_decisions_reach_established_status() -> None:
    status = compute_status(supporting_count=3, contradicting_count=0, total_decisions=3)

    assert status == PatternStatus.ESTABLISHED


def test_two_decisions_reach_only_emerging_status() -> None:
    status = compute_status(supporting_count=2, contradicting_count=0, total_decisions=2)

    assert status in (PatternStatus.EMERGING, PatternStatus.REPEATED)
    assert status != PatternStatus.ESTABLISHED


# --- 4: contradictory evidence lowers confidence -------------------------------


def test_contradictory_evidence_lowers_confidence_and_status() -> None:
    high_confidence, _ = compute_confidence(
        supporting_count=3, contradicting_count=0, observed_result_count=3, total_occurrence_count=3
    )
    low_confidence, basis = compute_confidence(
        supporting_count=2, contradicting_count=2, observed_result_count=2, total_occurrence_count=4
    )

    assert high_confidence == PatternConfidence.HIGH
    assert low_confidence == PatternConfidence.LOW
    assert "contradict" in basis.lower()


def test_contradicting_status_when_contradictions_outweigh_support() -> None:
    status = compute_status(supporting_count=1, contradicting_count=2, total_decisions=3)

    assert status == PatternStatus.CONTRADICTED


# --- 5, 6: failed / validated assumptions are detected --------------------------


def test_failed_assumption_pattern_detected_with_real_fields() -> None:
    signals = [
        _signals_with_assumption_outcome(LearningType.ASSUMPTION_FAILED, "Repeat order rate"),
        _signals_with_assumption_outcome(LearningType.ASSUMPTION_WEAKENED, "Repeat order rate"),
    ]

    patterns = detect_patterns(signals)
    failed = next(p for p in patterns if p.pattern_type == PatternType.RECURRING_FAILED_ASSUMPTION)

    assert failed.variable == "Repeat order rate"
    assert "weaker than expected" in failed.statement


def test_validated_assumption_pattern_detected() -> None:
    signals = [
        _signals_with_assumption_outcome(LearningType.ASSUMPTION_VALIDATED, "Pricing tolerance"),
        _signals_with_assumption_outcome(LearningType.ASSUMPTION_VALIDATED, "Pricing tolerance"),
    ]

    patterns = detect_patterns(signals)
    validated = [
        p for p in patterns if p.pattern_type == PatternType.RECURRING_VALIDATED_ASSUMPTION
    ]

    assert len(validated) == 1
    assert validated[0].variable == "Pricing tolerance"


# --- 7: repeated threshold failures are detected --------------------------------


def test_repeated_threshold_failure_detected() -> None:
    def bundle():
        decision_id = str(uuid4())
        threshold = _threshold(decision_id, variable="Operating margin")
        learning = _learning(
            decision_id,
            LearningType.THRESHOLD_FAILED,
            related_threshold_ids=[str(threshold.id)],
            statement="Operating margin missed its threshold.",
        )
        return DecisionSignals(
            decision_id=decision_id, thresholds=[threshold], learnings=[learning]
        )

    patterns = detect_patterns([bundle(), bundle()])
    failed = [p for p in patterns if p.pattern_type == PatternType.RECURRING_THRESHOLD_FAILURE]

    assert len(failed) == 1
    assert failed[0].variable == "Operating margin"
    # The statement explicitly hedges against claiming universal failure
    # (spec section 4B: "do not claim the threshold is universally
    # wrong") - it must contain the hedge, not merely an unqualified claim.
    assert "not a claim" in failed[0].statement or "only that it has so far" in failed[0].statement


# --- 8: repeated uncertainties are detected -------------------------------------


def test_recurring_unresolved_question_detected_when_never_tested() -> None:
    def bundle():
        decision_id = str(uuid4())
        assumption = _assumption(decision_id, statement="Acquisition cost stays low")
        return DecisionSignals(decision_id=decision_id, assumptions=[assumption])

    patterns = detect_patterns([bundle(), bundle()])
    unresolved = [
        p for p in patterns if p.pattern_type == PatternType.RECURRING_UNRESOLVED_QUESTION
    ]

    assert len(unresolved) == 1
    assert unresolved[0].variable == "Acquisition cost stays low"


def test_recurring_uncertainty_when_tested_at_least_once() -> None:
    decision_id_1 = str(uuid4())
    decision_id_2 = str(uuid4())
    statement = "Acquisition cost stays low"

    assumption_1 = _assumption(decision_id_1, statement=statement)
    learning_1 = _learning(
        decision_id_1, LearningType.ASSUMPTION_FAILED, related_assumption_ids=[str(assumption_1.id)]
    )
    bundle_1 = DecisionSignals(
        decision_id=decision_id_1, assumptions=[assumption_1], learnings=[learning_1]
    )

    assumption_2 = _assumption(decision_id_2, statement=statement)
    bundle_2 = DecisionSignals(decision_id=decision_id_2, assumptions=[assumption_2])

    patterns = detect_patterns([bundle_1, bundle_2])
    uncertainty_patterns = [
        p for p in patterns if p.pattern_type == PatternType.RECURRING_UNCERTAINTY
    ]

    assert len(uncertainty_patterns) == 1


# --- 9: repeated experiment learning is detected --------------------------------


def test_repeated_experiment_learning_detected() -> None:
    def bundle():
        decision_id = str(uuid4())
        threshold = _threshold(decision_id)
        experiment = _experiment(
            decision_id, target_threshold_id=str(threshold.id), experiment_type="landing_page"
        )
        result = _experiment_result(decision_id, experiment.id)
        learning = _learning(
            decision_id,
            LearningType.EXPERIMENT_LEARNING,
            source_type=LearningSourceType.EXPERIMENT_RESULT,
            source_id=result.id,
            statement="Landing page test reduced uncertainty.",
        )
        return DecisionSignals(
            decision_id=decision_id,
            thresholds=[threshold],
            experiments=[experiment],
            experiment_results=[result],
            learnings=[learning],
        )

    patterns = detect_patterns([bundle(), bundle(), bundle()])
    learning_patterns = [
        p for p in patterns if p.pattern_type == PatternType.RECURRING_EXPERIMENT_LEARNING
    ]

    assert len(learning_patterns) == 1
    assert len(set(o.decision_id for o in learning_patterns[0].occurrences)) == 3


# --- 10: provenance is preserved -------------------------------------------------


def test_every_occurrence_traces_to_a_real_source_id() -> None:
    signals = [
        _signals_with_assumption_outcome(LearningType.ASSUMPTION_FAILED, "Repeat order rate"),
        _signals_with_assumption_outcome(LearningType.ASSUMPTION_FAILED, "Repeat order rate"),
    ]

    patterns = detect_patterns(signals)
    failed = next(p for p in patterns if p.pattern_type == PatternType.RECURRING_FAILED_ASSUMPTION)

    for occurrence in failed.occurrences:
        assert occurrence.source_type == "memory_learning"
        assert occurrence.source_id
        assert occurrence.decision_id


# --- deterministic ids -----------------------------------------------------------


def test_pattern_id_is_deterministic_for_the_same_user_type_and_key() -> None:
    id_a = deterministic_pattern_id("user-1", PatternType.RECURRING_FAILED_ASSUMPTION, "retention")
    id_b = deterministic_pattern_id("user-1", PatternType.RECURRING_FAILED_ASSUMPTION, "retention")
    id_c = deterministic_pattern_id("user-2", PatternType.RECURRING_FAILED_ASSUMPTION, "retention")

    assert id_a == id_b
    assert id_a != id_c


def test_occurrence_id_is_deterministic_for_the_same_source_record() -> None:
    id_a = deterministic_occurrence_id("pattern-1", "decision-1", "memory_learning", "learning-1")
    id_b = deterministic_occurrence_id("pattern-1", "decision-1", "memory_learning", "learning-1")
    id_c = deterministic_occurrence_id("pattern-1", "decision-2", "memory_learning", "learning-1")

    assert id_a == id_b
    assert id_a != id_c


# --- 20/18: contradictory observations represented correctly -------------------


def test_mixed_validated_and_failed_produces_one_dominant_pattern_with_contradictions() -> None:
    signals = [
        _signals_with_assumption_outcome(LearningType.ASSUMPTION_VALIDATED, "Retention"),
        _signals_with_assumption_outcome(LearningType.ASSUMPTION_VALIDATED, "Retention"),
        _signals_with_assumption_outcome(LearningType.ASSUMPTION_FAILED, "Retention"),
    ]

    patterns = detect_patterns(signals)
    validated = [
        p for p in patterns if p.pattern_type == PatternType.RECURRING_VALIDATED_ASSUMPTION
    ]
    failed = [p for p in patterns if p.pattern_type == PatternType.RECURRING_FAILED_ASSUMPTION]

    # Validated is dominant (2 vs 1) - only ONE pattern should exist for
    # this variable, never two competing ones, and it must record the
    # contradiction rather than silently absorbing it.
    assert len(validated) == 1
    assert failed == []
    assert len(validated[0].contradicting_decision_ids) == 1
    assert len(validated[0].supporting_decision_ids) == 2


# --- 21: incomplete memories do not crash detection ------------------------------


def test_incomplete_signals_never_raise() -> None:
    empty_bundle = DecisionSignals(decision_id=str(uuid4()))
    bundle_with_orphan_learning = DecisionSignals(
        decision_id=str(uuid4()),
        learnings=[
            _learning(
                str(uuid4()),
                LearningType.ASSUMPTION_FAILED,
                related_assumption_ids=["nonexistent-id"],
            )
        ],
    )

    # Should never raise, regardless of how thin the data is.
    patterns = detect_patterns([empty_bundle, bundle_with_orphan_learning])

    assert isinstance(patterns, list)


def test_learning_with_no_related_ids_is_safely_ignored() -> None:
    decision_id = str(uuid4())
    learning = _learning(decision_id, LearningType.ASSUMPTION_FAILED, related_assumption_ids=[])
    bundle = DecisionSignals(decision_id=decision_id, learnings=[learning])

    patterns = detect_patterns([bundle, bundle])

    assert patterns == []
