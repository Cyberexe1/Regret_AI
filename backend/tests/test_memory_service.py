"""Tests for `MemoryService` and `MemoryRepository`.

No LLM/Strands invocation happens anywhere in this file - memory
construction is entirely deterministic Python, exactly like
`ReEvaluationService` (see `test_re_evaluation_service.py`, whose seeding
helper this mirrors). Tests seed a decision's assumptions/thresholds/
regret scenarios/experiments directly through `DecisionRepository`, then
drive the real `ReEvaluationService.submit_result` to produce a genuine
`ExperimentResult`/`ReEvaluation` pair before exercising `MemoryService`
against it - memory is never tested against fabricated re-evaluation data.
"""

from uuid import uuid4

import pytest

from app.core.errors import NotFoundError
from app.memory.memory_repository import MemoryRepository
from app.memory.memory_schemas import LearningType, MemoryStage
from app.memory.memory_service import MemoryService
from app.repositories.decision_repository import DecisionRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.schemas.decision import DecisionCreate
from app.schemas.experiment_result import ExperimentResultCreate
from app.services.re_evaluation_service import ReEvaluationService

USER_ID = "test-user"


@pytest.fixture
def decision_repo(dynamodb_table: None) -> DecisionRepository:
    return DecisionRepository()


@pytest.fixture
def evidence_repo(dynamodb_table: None) -> EvidenceRepository:
    return EvidenceRepository()


@pytest.fixture
def memory_repo(dynamodb_table: None) -> MemoryRepository:
    return MemoryRepository()


@pytest.fixture
def reeval_service(
    decision_repo: DecisionRepository, evidence_repo: EvidenceRepository
) -> ReEvaluationService:
    return ReEvaluationService(decision_repo, evidence_repo)


@pytest.fixture
def memory_service(
    memory_repo: MemoryRepository, decision_repo: DecisionRepository
) -> MemoryService:
    return MemoryService(memory_repo, decision_repo)


def _seeded_decision(decision_repo: DecisionRepository):
    """Mirrors `test_re_evaluation_service.py`'s seeding helper: one
    assumption, one regret scenario, one threshold (validated,
    below-direction, 24%), one experiment targeting that threshold."""
    decision = decision_repo.create(
        USER_ID,
        DecisionCreate(
            title="Open a cloud kitchen",
            description="Considering a Rs 5 lakh investment in a cloud kitchen.",
        ),
    )

    assumptions = decision_repo.create_assumptions(
        decision.id,
        [
            {
                "statement": "Repeat customers will sustain unit economics.",
                "source": "implicit",
                "importance": "critical",
                "confidence": 0.4,
                "evidence_status": "not_addressed",
                "dependency": "Business profitability",
                "failure_consequence": "Revenue falls short of required margin.",
            }
        ],
    )
    assumption = assumptions[0]

    regret_scenarios = decision_repo.create_regret_scenarios(
        decision.id,
        [
            {
                "title": "Adoption failure",
                "failure_condition": "Repeat-order rate remains below sustainable levels.",
                "probability_band": "unknown",
                "impact": "severe",
                "regret_level": "high",
                "trigger_variable": "Repeat-order rate",
                "trigger_direction": "below",
                "consequence": "Full capital commitment before demand is validated.",
                "related_assumption_ids": [str(assumption.id)],
                "related_challenge_ids": [],
                "evidence_basis": "x",
            }
        ],
    )
    scenario = regret_scenarios[0]

    thresholds = decision_repo.create_thresholds(
        decision.id,
        [
            {
                "variable": "Repeat-order rate",
                "threshold_type": "numeric",
                "direction": "below",
                "threshold_value": "24",
                "unit": "%",
                "confidence": 0.7,
                "derivation": "calculated_from_evidence",
                "consequence": "Unit economics no longer hold.",
                "related_regret_scenario_ids": [str(scenario.id)],
                "related_assumption_ids": [str(assumption.id)],
                "evidence_basis": "x",
                "validation_status": "validated",
            }
        ],
    )
    threshold = thresholds[0]

    experiments = decision_repo.create_experiments(
        decision.id,
        [
            {
                "title": "14-day limited delivery pilot",
                "hypothesis": "Customers will reorder at a sufficient rate.",
                "target_threshold_id": str(threshold.id),
                "variable_to_test": "Repeat-order rate",
                "experiment_type": "pilot",
                "decision_rule": "If met, reassess. If missed, do not commit yet.",
                "related_assumption_ids": [str(assumption.id)],
                "related_regret_scenario_ids": [str(scenario.id)],
            }
        ],
    )
    experiment = experiments[0]

    return decision, assumption, scenario, threshold, experiment


# --- 1: preliminary memory (no experiment result yet) -----------------------


def test_preliminary_memory_created_before_any_experiment_result(
    memory_service: MemoryService, decision_repo: DecisionRepository
) -> None:
    decision, assumption, scenario, threshold, experiment = _seeded_decision(decision_repo)

    memory = memory_service.get_or_create_preliminary_memory(decision.id)

    assert memory.stage == MemoryStage.PRELIMINARY
    assert memory.decision_id == decision.id
    assert memory.user_id == USER_ID
    assert str(threshold.id) in memory.critical_threshold_ids
    assert str(assumption.id) in memory.critical_assumption_ids
    assert str(scenario.id) in memory.critical_regret_scenario_ids
    assert str(experiment.id) in memory.experiment_ids
    # No observed outcome exists yet - KNOWN vs EXPECTED vs UNRESOLVED.
    assert memory.outcome_summary is None
    assert memory.final_assessment is None
    assert memory.unresolved_uncertainties  # threshold not yet validated by a real result


def test_get_or_create_preliminary_memory_is_idempotent(
    memory_service: MemoryService, decision_repo: DecisionRepository
) -> None:
    decision, *_ = _seeded_decision(decision_repo)

    first = memory_service.get_or_create_preliminary_memory(decision.id)
    second = memory_service.get_or_create_preliminary_memory(decision.id)

    assert first.memory_id == second.memory_id
    assert first == second


def test_preliminary_memory_for_missing_decision_raises_not_found(
    memory_service: MemoryService,
) -> None:
    with pytest.raises(NotFoundError):
        memory_service.get_or_create_preliminary_memory(uuid4())


# --- 2 & 3: experiment result -> re-evaluation -> memory update -------------


def test_update_memory_from_reevaluation_records_threshold_failed(
    memory_service: MemoryService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
) -> None:
    decision, assumption, scenario, threshold, experiment = _seeded_decision(decision_repo)

    result, reevaluation = reeval_service.submit_result(
        decision.id,
        experiment.id,
        ExperimentResultCreate(
            outcome="failure",
            summary="18 of 100 customers reordered within the pilot window.",
            measured_values={"Repeat-order rate": 18},
        ),
    )

    memory, learnings = memory_service.update_memory_from_reevaluation(
        decision.id, experiment.id, result, reevaluation
    )

    assert memory.stage == MemoryStage.VALIDATED
    assert memory.outcome_summary == reevaluation.key_learning
    assert memory.final_assessment == reevaluation.decision_assessment.summary
    assert memory.confidence == reevaluation.decision_assessment.confidence
    assert str(experiment.id) in memory.experiment_ids

    threshold_learnings = [
        learning
        for learning in learnings
        if learning.learning_type == LearningType.THRESHOLD_FAILED
    ]
    assert len(threshold_learnings) == 1
    learning = threshold_learnings[0]
    assert learning.observed_value == "18"
    assert learning.expected_value == "24"
    assert str(threshold.id) in learning.related_threshold_ids
    # Provenance: points back to the real ReEvaluation record, not invented.
    assert learning.source_id == reevaluation.id
    assert learning.source_type.value == "re_evaluation"


def test_update_memory_from_reevaluation_records_threshold_validated(
    memory_service: MemoryService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
) -> None:
    decision, *_, experiment = _seeded_decision(decision_repo)

    result, reevaluation = reeval_service.submit_result(
        decision.id,
        experiment.id,
        ExperimentResultCreate(
            outcome="success",
            summary="30 of 100 customers reordered.",
            measured_values={"Repeat-order rate": 30},
        ),
    )

    memory, learnings = memory_service.update_memory_from_reevaluation(
        decision.id, experiment.id, result, reevaluation
    )

    assert any(learning.learning_type == LearningType.THRESHOLD_VALIDATED for learning in learnings)
    assert memory.confidence is not None


def test_update_memory_from_reevaluation_records_inconclusive(
    memory_service: MemoryService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
) -> None:
    decision, *_, experiment = _seeded_decision(decision_repo)

    # No measured value provided at all -> no comparison could be made ->
    # the threshold comparison itself reports UNKNOWN, which maps to an
    # unresolved-uncertainty learning, never a fabricated pass/fail.
    result, reevaluation = reeval_service.submit_result(
        decision.id,
        experiment.id,
        ExperimentResultCreate(outcome="inconclusive", summary="Pilot data was ambiguous."),
    )

    memory, learnings = memory_service.update_memory_from_reevaluation(
        decision.id, experiment.id, result, reevaluation
    )

    # No numeric comparison exists, so nothing claims a definitive
    # threshold_validated/threshold_failed outcome here.
    assert not any(
        learning.learning_type == LearningType.THRESHOLD_VALIDATED for learning in learnings
    )
    assert not any(
        learning.learning_type == LearningType.THRESHOLD_FAILED for learning in learnings
    )


# --- Idempotency: duplicate processing must not duplicate learnings ---------


def test_processing_the_same_result_twice_does_not_duplicate_learnings(
    memory_service: MemoryService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
) -> None:
    decision, *_, experiment = _seeded_decision(decision_repo)

    result, reevaluation = reeval_service.submit_result(
        decision.id,
        experiment.id,
        ExperimentResultCreate(
            outcome="failure",
            summary="18 of 100 customers reordered.",
            measured_values={"Repeat-order rate": 18},
        ),
    )

    memory_service.update_memory_from_reevaluation(decision.id, experiment.id, result, reevaluation)
    memory_service.update_memory_from_reevaluation(decision.id, experiment.id, result, reevaluation)

    learnings = memory_service.list_learnings(decision.id)
    threshold_failed = [
        learning
        for learning in learnings
        if learning.learning_type == LearningType.THRESHOLD_FAILED
    ]
    assert len(threshold_failed) == 1  # not duplicated on the second call


# --- Retrieval ----------------------------------------------------------------


def test_get_memory_context_before_any_result(
    memory_service: MemoryService, decision_repo: DecisionRepository
) -> None:
    decision, *_ = _seeded_decision(decision_repo)

    context = memory_service.get_memory_context(decision.id)

    assert context.memory is None
    assert context.learnings == []
    assert context.experiments == []
    assert context.assessments == []


def test_get_memory_context_after_result(
    memory_service: MemoryService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
) -> None:
    decision, *_, experiment = _seeded_decision(decision_repo)

    result, reevaluation = reeval_service.submit_result(
        decision.id,
        experiment.id,
        ExperimentResultCreate(
            outcome="failure", summary="x", measured_values={"Repeat-order rate": 18}
        ),
    )
    memory_service.update_memory_from_reevaluation(decision.id, experiment.id, result, reevaluation)

    context = memory_service.get_memory_context(decision.id)

    assert context.memory is not None
    assert context.memory.stage == MemoryStage.VALIDATED
    assert len(context.learnings) > 0
    assert len(context.experiments) == 1
    assert context.experiments[0].id == experiment.id
    assert len(context.assessments) == 1
    assert context.assessments[0].id == reevaluation.id


def test_get_unresolved_uncertainties_before_any_result(
    memory_service: MemoryService, decision_repo: DecisionRepository
) -> None:
    decision, *_ = _seeded_decision(decision_repo)
    memory_service.get_or_create_preliminary_memory(decision.id)

    uncertainties = memory_service.get_unresolved_uncertainties(decision.id)

    assert len(uncertainties) > 0


def test_get_memory_by_id(
    memory_service: MemoryService, decision_repo: DecisionRepository
) -> None:
    decision, *_ = _seeded_decision(decision_repo)
    memory = memory_service.get_or_create_preliminary_memory(decision.id)

    found = memory_service.get_memory_by_id(memory.memory_id)

    assert found is not None
    assert found.memory_id == memory.memory_id


def test_get_memory_by_id_missing_returns_none(memory_service: MemoryService) -> None:
    assert memory_service.get_memory_by_id(uuid4()) is None
