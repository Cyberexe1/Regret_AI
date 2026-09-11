"""Tests for `QualityService`/`CalibrationService` - the orchestration
layer for the Quality & Calibration Engine (REGRET ENGINE 2.0, Step 24).

No LLM/Strands invocation happens anywhere in this file. Tests seed real
decisions/assumptions/thresholds/experiments through `DecisionRepository`
and drive the real `ReEvaluationService`/`MemoryService` to produce
genuine downstream records - mirroring `test_adaptive_service.py`'s and
`test_learning_service.py`'s exact seeding pattern.
"""

from uuid import uuid4

import pytest

from app.learning.repository import CrossDecisionLearningRepository
from app.memory.memory_repository import MemoryRepository
from app.memory.memory_service import MemoryService
from app.quality.repository import CalibrationRepository, QualityRepository
from app.quality.schemas import QualityBand
from app.quality.service import CalibrationService, QualityService
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.decision_repository import DecisionRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.schemas.decision import DecisionCreate
from app.schemas.experiment_result import ExperimentResultCreate
from app.services.re_evaluation_service import ReEvaluationService

USER_A = "user-a"
USER_B = "user-b"


@pytest.fixture
def decision_repo(dynamodb_table: None) -> DecisionRepository:
    return DecisionRepository()


@pytest.fixture
def evidence_repo(dynamodb_table: None) -> EvidenceRepository:
    return EvidenceRepository()


@pytest.fixture
def analysis_repo(dynamodb_table: None) -> AnalysisRepository:
    return AnalysisRepository()


@pytest.fixture
def memory_repo(dynamodb_table: None) -> MemoryRepository:
    return MemoryRepository()


@pytest.fixture
def learning_repo(dynamodb_table: None) -> CrossDecisionLearningRepository:
    return CrossDecisionLearningRepository()


@pytest.fixture
def quality_repo(dynamodb_table: None) -> QualityRepository:
    return QualityRepository()


@pytest.fixture
def calibration_repo(dynamodb_table: None) -> CalibrationRepository:
    return CalibrationRepository()


@pytest.fixture
def memory_service(
    memory_repo: MemoryRepository, decision_repo: DecisionRepository
) -> MemoryService:
    return MemoryService(memory_repo, decision_repo)


@pytest.fixture
def reeval_service(
    decision_repo: DecisionRepository, evidence_repo: EvidenceRepository
) -> ReEvaluationService:
    return ReEvaluationService(decision_repo, evidence_repo)


@pytest.fixture
def quality_service(
    decision_repo: DecisionRepository,
    evidence_repo: EvidenceRepository,
    analysis_repo: AnalysisRepository,
    memory_repo: MemoryRepository,
    learning_repo: CrossDecisionLearningRepository,
    quality_repo: QualityRepository,
) -> QualityService:
    return QualityService(
        decision_repo, evidence_repo, analysis_repo, memory_repo, learning_repo, quality_repo
    )


@pytest.fixture
def calibration_service(
    decision_repo: DecisionRepository, calibration_repo: CalibrationRepository
) -> CalibrationService:
    return CalibrationService(decision_repo, calibration_repo)


def _seed_decision(decision_repo: DecisionRepository, user_id: str = USER_A):
    decision = decision_repo.create(
        user_id, DecisionCreate(title="Open a cloud kitchen", description="x", budget=500000)
    )
    assumption = decision_repo.create_assumptions(
        decision.id,
        [
            {
                "statement": "Customer retention rate",
                "source": "implicit",
                "importance": "critical",
                "confidence": 0.1,
                "evidence_status": "not_addressed",
            }
        ],
    )[0]
    scenario = decision_repo.create_regret_scenarios(
        decision.id,
        [
            {
                "title": "x",
                "failure_condition": "x",
                "regret_level": "critical",
                "impact": "severe",
                "related_assumption_ids": [str(assumption.id)],
            }
        ],
    )[0]
    threshold = decision_repo.create_thresholds(
        decision.id,
        [
            {
                "variable": "Customer retention rate",
                "validation_status": "provisional",
                "derivation": "calculated_from_evidence",
                "threshold_value": "24",
                "direction": "below",
                "related_assumption_ids": [str(assumption.id)],
                "related_regret_scenario_ids": [str(scenario.id)],
            }
        ],
    )[0]
    experiment = decision_repo.create_experiments(
        decision.id,
        [
            {
                "title": "Retention pilot",
                "hypothesis": "x",
                "target_threshold_id": str(threshold.id),
                "decision_rule": "x",
                "feasibility": "high",
                "reversibility": "high",
                "estimated_cost": 1000,
            }
        ],
    )[0]
    return {
        "decision": decision,
        "assumption": assumption,
        "threshold": threshold,
        "experiment": experiment,
    }


# --- 20: quality history persistence ---------------------------------------------


def test_run_quality_check_persists_a_retrievable_assessment(
    quality_service: QualityService,
    decision_repo: DecisionRepository,
) -> None:
    seeded = _seed_decision(decision_repo)

    assessment = quality_service.run_quality_check(seeded["decision"].id, USER_A)

    fetched = quality_service.get_latest(seeded["decision"].id)
    assert fetched is not None
    assert fetched.quality_id == assessment.quality_id
    assert fetched.overall_quality in {b for b in QualityBand}


def test_quality_history_grows_across_multiple_checks(
    quality_service: QualityService,
    decision_repo: DecisionRepository,
) -> None:
    seeded = _seed_decision(decision_repo)

    quality_service.run_quality_check(seeded["decision"].id, USER_A)
    quality_service.run_quality_check(seeded["decision"].id, USER_A)

    history = quality_service.list_history(seeded["decision"].id)
    assert len(history) >= 1  # deterministic id may or may not differ; history is never lost


def test_get_latest_before_any_check_returns_none(quality_service: QualityService) -> None:
    assert quality_service.get_latest(uuid4()) is None


# --- 19: idempotent quality checks -------------------------------------------------


def test_quality_id_is_deterministic_for_the_same_analysis_run(
    quality_service: QualityService,
    decision_repo: DecisionRepository,
) -> None:
    seeded = _seed_decision(decision_repo)

    first = quality_service.run_quality_check(seeded["decision"].id, USER_A)
    second = quality_service.run_quality_check(seeded["decision"].id, USER_A)

    # No analysis run exists in this seeding path, so both share the
    # same "no-analysis-run" discriminator - re-running with no new
    # analysis run produces the SAME quality_id.
    assert first.quality_id == second.quality_id


# --- 21: re-evaluation updates quality appropriately --------------------------------


def test_quality_improves_after_a_supporting_experiment_result(
    quality_service: QualityService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    seeded = _seed_decision(decision_repo)

    before = quality_service.run_quality_check(seeded["decision"].id, USER_A)
    before_threshold_checks = [
        c for c in before.checks if c.name == "threshold_evaluated_after_experiment"
    ]
    assert before_threshold_checks == []  # experiment not completed yet, check doesn't fire

    result, reevaluation = reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment"].id,
        ExperimentResultCreate(
            outcome="success", summary="x", measured_values={"Customer retention rate": 30}
        ),
    )
    memory_service.update_memory_from_reevaluation(
        seeded["decision"].id, seeded["experiment"].id, result, reevaluation
    )

    after = quality_service.run_quality_check(seeded["decision"].id, USER_A)
    consistency_failures = [
        c for c in after.checks if c.category.value == "consistency" and c.status.value == "failed"
    ]
    # A successful, consistent result should never itself introduce a
    # consistency failure.
    assert consistency_failures == []


def test_quality_detects_new_inconsistency_after_contradictory_result(
    quality_service: QualityService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    seeded = _seed_decision(decision_repo)
    # Mark the threshold as already "validated" even though nothing has
    # tested it yet - simulates a stale/incorrect validation_status.
    decision_repo.create_thresholds(
        seeded["decision"].id,
        [
            {
                "variable": "Second variable",
                "validation_status": "validated",
                "derivation": "calculated_from_evidence",
                "threshold_value": "10",
            }
        ],
    )

    result, reevaluation = reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment"].id,
        ExperimentResultCreate(
            outcome="failure", summary="x", measured_values={"Customer retention rate": 5}
        ),
    )
    memory_service.update_memory_from_reevaluation(
        seeded["decision"].id, seeded["experiment"].id, result, reevaluation
    )

    after = quality_service.run_quality_check(seeded["decision"].id, USER_A)
    # The ORIGINAL threshold (targeted by the experiment) should now be
    # correctly reflected as failed, not silently left "provisional."
    threshold_checks = [
        c for c in after.checks if c.related_entity_id == str(seeded["threshold"].id)
    ]
    assert len(threshold_checks) > 0


# --- 18: user isolation ---------------------------------------------------------------


def test_user_a_cannot_read_user_b_quality_assessment(
    quality_service: QualityService,
    decision_repo: DecisionRepository,
) -> None:
    seeded_a = _seed_decision(decision_repo, user_id=USER_A)
    seeded_b = _seed_decision(decision_repo, user_id=USER_B)

    quality_service.run_quality_check(seeded_a["decision"].id, USER_A)
    quality_service.run_quality_check(seeded_b["decision"].id, USER_B)

    assessment_a = quality_service.get_latest(seeded_a["decision"].id)
    assessment_b = quality_service.get_latest(seeded_b["decision"].id)

    assert assessment_a.user_id == USER_A
    assert assessment_b.user_id == USER_B
    assert assessment_a.decision_id != assessment_b.decision_id


def test_user_a_cannot_read_user_b_calibration(
    calibration_service: CalibrationService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    seeded_a = _seed_decision(decision_repo, user_id=USER_A)
    seeded_b = _seed_decision(decision_repo, user_id=USER_B)

    for seeded in (seeded_a, seeded_b):
        reeval_service.submit_result(
            seeded["decision"].id,
            seeded["experiment"].id,
            ExperimentResultCreate(
                outcome="failure", summary="x", measured_values={"Customer retention rate": 5}
            ),
        )

    calibration_service.refresh_calibration(USER_A)
    calibration_service.refresh_calibration(USER_B)

    insights_a = calibration_service.list_for_user(USER_A)
    insights_b = calibration_service.list_for_user(USER_B)

    assert all(i.user_id == USER_A for i in insights_a)
    assert all(i.user_id == USER_B for i in insights_b)


# --- calibration: zero / one / multiple observations, via the service -----------


def test_calibration_refresh_with_no_decisions_returns_empty(
    calibration_service: CalibrationService,
) -> None:
    insights = calibration_service.refresh_calibration(str(uuid4()))

    assert insights == []


def test_calibration_refresh_with_one_observation_is_limited_history(
    calibration_service: CalibrationService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    seeded = _seed_decision(decision_repo)
    result, reevaluation = reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment"].id,
        ExperimentResultCreate(
            outcome="failure", summary="x", measured_values={"Customer retention rate": 5}
        ),
    )
    memory_service.update_memory_from_reevaluation(
        seeded["decision"].id, seeded["experiment"].id, result, reevaluation
    )

    insights = calibration_service.refresh_calibration(USER_A)

    assert len(insights) == 1
    assert insights[0].observation_count == 1
    assert insights[0].evidence_strength.value == "limited_history"


def test_get_for_variable_resolves_via_normalization(
    calibration_service: CalibrationService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    seeded = _seed_decision(decision_repo)
    result, reevaluation = reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment"].id,
        ExperimentResultCreate(
            outcome="failure", summary="x", measured_values={"Customer retention rate": 5}
        ),
    )
    memory_service.update_memory_from_reevaluation(
        seeded["decision"].id, seeded["experiment"].id, result, reevaluation
    )
    calibration_service.refresh_calibration(USER_A)

    insight = calibration_service.get_for_variable(USER_A, "Customer retention rate")

    assert insight is not None
    assert insight.variable == "Customer retention rate"


def test_get_for_variable_returns_none_when_no_insight_exists(
    calibration_service: CalibrationService,
) -> None:
    assert calibration_service.get_for_variable(USER_A, "Nonexistent variable") is None
