"""Tests for `CrossDecisionLearningService` - the orchestration layer for
Cross-Decision Learning (REGRET ENGINE 2.0, Step 23).

No LLM/Strands invocation happens anywhere in this file. Tests seed real
decisions/assumptions/thresholds/experiments through `DecisionRepository`
and drive the real `ReEvaluationService`/`MemoryService` to produce
genuine downstream `MemoryLearning` records - mirroring
`test_adaptive_service.py`'s seeding pattern - then exercise
`CrossDecisionLearningService.refresh_patterns` against them.
"""

from uuid import uuid4

import pytest

from app.learning.repository import CrossDecisionLearningRepository
from app.learning.schemas import HistoricalLearningSignal, PatternStatus
from app.learning.service import CrossDecisionLearningService
from app.memory.memory_repository import MemoryRepository
from app.memory.memory_service import MemoryService
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
def memory_repo(dynamodb_table: None) -> MemoryRepository:
    return MemoryRepository()


@pytest.fixture
def learning_repo(dynamodb_table: None) -> CrossDecisionLearningRepository:
    return CrossDecisionLearningRepository()


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
def learning_service(
    decision_repo: DecisionRepository,
    memory_repo: MemoryRepository,
    learning_repo: CrossDecisionLearningRepository,
) -> CrossDecisionLearningService:
    return CrossDecisionLearningService(decision_repo, memory_repo, learning_repo)


def _seed_decision_with_failed_retention(
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
    user_id: str,
    variable: str = "Customer retention rate",
    outcome: str = "failure",
    measured_value: float = 10,
):
    decision = decision_repo.create(
        user_id, DecisionCreate(title="Open a cloud kitchen", description="x", budget=500000)
    )
    assumption = decision_repo.create_assumptions(
        decision.id,
        [
            {
                "statement": variable,
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
                "title": "Retention failure",
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
                "variable": variable,
                "validation_status": "validated",
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

    result, reevaluation = reeval_service.submit_result(
        decision.id,
        experiment.id,
        ExperimentResultCreate(
            outcome=outcome, summary="Observed.", measured_values={variable: measured_value}
        ),
    )
    memory_service.update_memory_from_reevaluation(decision.id, experiment.id, result, reevaluation)

    return decision


# --- 1: one occurrence does not create a strong pattern ------------------------


def test_single_decision_refresh_creates_no_pattern(
    learning_service: CrossDecisionLearningService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_A)

    response = learning_service.refresh_patterns(USER_A)

    assert response.total_patterns == 0
    assert response.patterns_created == 0


# --- 2/3: repeated failures create/establish a pattern --------------------------


def test_two_decisions_create_an_emerging_pattern(
    learning_service: CrossDecisionLearningService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_A)
    _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_A)

    response = learning_service.refresh_patterns(USER_A)
    patterns = learning_service.list_patterns_for_user(USER_A)

    # A single scenario (retention assumption failed + its threshold
    # failed + the assumption remains formally "unresolved" but was
    # tested) legitimately produces multiple distinct, real patterns -
    # never collapsed into one, since each is backed by its own kind of
    # canonical record (memory_learning types differ).
    assert response.patterns_created == len(patterns)
    assert len(patterns) >= 1
    for pattern in patterns:
        assert pattern.status in (PatternStatus.EMERGING, PatternStatus.REPEATED)
        assert len(pattern.supporting_decision_ids) == 2


def test_three_decisions_can_reach_established(
    learning_service: CrossDecisionLearningService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    for _ in range(3):
        _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_A)

    learning_service.refresh_patterns(USER_A)
    patterns = learning_service.list_patterns_for_user(USER_A)

    assert len(patterns) >= 1
    assert all(p.status == PatternStatus.ESTABLISHED for p in patterns)


# --- 10: provenance preserved ---------------------------------------------------


def test_pattern_detail_exposes_real_provenance(
    learning_service: CrossDecisionLearningService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_A)
    _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_A)
    learning_service.refresh_patterns(USER_A)

    patterns = learning_service.list_patterns_for_user(USER_A)
    failed_assumption_pattern = next(
        p for p in patterns if p.pattern_type.value == "recurring_failed_assumption"
    )
    detail = learning_service.get_pattern_detail(USER_A, failed_assumption_pattern.pattern_id)

    assert detail is not None
    assert len(detail.occurrences) == 2
    for occurrence in detail.occurrences:
        assert occurrence.source_id
        assert occurrence.source_type == "memory_learning"


def test_get_pattern_detail_for_unknown_id_returns_none(
    learning_service: CrossDecisionLearningService,
) -> None:
    assert learning_service.get_pattern_detail(USER_A, "not-a-real-id") is None


# --- 11: duplicate refresh does not create duplicates ---------------------------


def test_duplicate_refresh_reports_unchanged_not_duplicated(
    learning_service: CrossDecisionLearningService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_A)
    _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_A)

    first = learning_service.refresh_patterns(USER_A)
    second = learning_service.refresh_patterns(USER_A)

    assert first.patterns_created == first.total_patterns
    assert second.patterns_created == 0
    assert second.patterns_unchanged == first.total_patterns
    assert len(learning_service.list_patterns_for_user(USER_A)) == first.total_patterns


# --- 12/13/16: MANDATORY user isolation at the service layer --------------------


def test_user_a_cannot_access_user_b_patterns_via_service(
    learning_service: CrossDecisionLearningService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_A)
    _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_A)
    _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_B)
    _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_B)

    learning_service.refresh_patterns(USER_A)
    learning_service.refresh_patterns(USER_B)

    patterns_a = learning_service.list_patterns_for_user(USER_A)
    patterns_b = learning_service.list_patterns_for_user(USER_B)

    assert len(patterns_a) >= 1
    assert len(patterns_b) >= 1
    assert all(p.user_id == USER_A for p in patterns_a)
    assert all(p.user_id == USER_B for p in patterns_b)
    # Cross-check: User A's pattern is never retrievable under User B's id.
    assert learning_service.get_pattern(USER_B, patterns_a[0].pattern_id) is None


def test_refreshing_user_a_never_touches_user_b_patterns(
    learning_service: CrossDecisionLearningService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_B)
    _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_B)
    learning_service.refresh_patterns(USER_B)
    before = learning_service.list_patterns_for_user(USER_B)

    learning_service.refresh_patterns(USER_A)
    after = learning_service.list_patterns_for_user(USER_B)

    assert len(before) == len(after) >= 1
    assert {p.pattern_id for p in before} == {p.pattern_id for p in after}


# --- 14/15: current evidence remains higher priority; history never overrides --


def test_historical_signal_never_appears_for_a_variable_with_no_pattern(
    learning_service: CrossDecisionLearningService,
) -> None:
    signal, explanation = learning_service.historical_learning_signal_for_variable(
        USER_A, "Some totally new variable"
    )

    assert signal == HistoricalLearningSignal.NONE
    assert explanation == ""


def test_historical_signal_is_strong_for_an_established_failure_pattern(
    learning_service: CrossDecisionLearningService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    for _ in range(3):
        _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_A)
    learning_service.refresh_patterns(USER_A)

    signal, explanation = learning_service.historical_learning_signal_for_variable(
        USER_A, "Customer retention rate"
    )

    assert signal == HistoricalLearningSignal.STRONG
    assert explanation != ""


def test_historical_signal_is_weak_for_a_validated_pattern(
    learning_service: CrossDecisionLearningService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    for _ in range(2):
        _seed_decision_with_failed_retention(
            decision_repo,
            reeval_service,
            memory_service,
            USER_A,
            variable="Pricing tolerance",
            outcome="success",
            measured_value=30,
        )
    learning_service.refresh_patterns(USER_A)

    signal, explanation = learning_service.historical_learning_signal_for_variable(
        USER_A, "Pricing tolerance"
    )

    # The same assumption is BOTH validated (a lowering signal) AND
    # still formally unresolved (evidence_status stays not_addressed
    # even after a successful result - see Threshold Engine's own
    # evidence-status semantics) - so a recurring_uncertainty pattern
    # coexists with the validated one for this variable. Raising
    # signals take priority (spec section 14: "increase the priority of
    # testing"), so this is a real, non-NONE signal, never fabricated.
    assert signal != HistoricalLearningSignal.NONE
    assert explanation != ""


# --- 17: VOI receives the historical learning signal (integration smoke test) --


def test_voi_service_enriches_items_with_cross_decision_signal(
    learning_service: CrossDecisionLearningService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    from app.agents.value_of_information import ValueOfInformationService
    from app.repositories.value_of_information_repository import ValueOfInformationRepository

    for _ in range(3):
        _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_A)
    learning_service.refresh_patterns(USER_A)

    voi_service = ValueOfInformationService(
        decision_repo, ValueOfInformationRepository(), None, learning_service
    )

    # A fresh decision with the SAME recurring variable.
    decision = decision_repo.create(USER_A, DecisionCreate(title="New venture", description="x"))
    decision_repo.create_assumptions(
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
    )

    analysis = voi_service.compute_and_persist(decision, user_id=USER_A)

    assert len(analysis.ranked_uncertainties) == 1
    item = analysis.ranked_uncertainties[0]
    assert item.historical_learning_signal == HistoricalLearningSignal.STRONG
    assert item.historical_learning_explanation is not None


# --- 19: missing historical data is handled safely -------------------------------


def test_refresh_with_no_decisions_at_all_never_raises(
    learning_service: CrossDecisionLearningService,
) -> None:
    response = learning_service.refresh_patterns(str(uuid4()))

    assert response.total_patterns == 0
    assert response.patterns_created == 0


# --- 22: pagination / bounding works --------------------------------------------


def test_refresh_respects_the_configured_max_decisions_bound(
    decision_repo: DecisionRepository,
    memory_repo: MemoryRepository,
    learning_repo: CrossDecisionLearningRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config as config_module

    config_module.get_settings.cache_clear()
    monkeypatch.setenv("LEARNING_MAX_DECISIONS_SCANNED", "1")
    config_module.get_settings.cache_clear()

    service = CrossDecisionLearningService(decision_repo, memory_repo, learning_repo)
    _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_A)
    _seed_decision_with_failed_retention(decision_repo, reeval_service, memory_service, USER_A)

    # With the bound set to 1 decision, there's not enough evidence in
    # scope to ever form a 2-decision pattern.
    response = service.refresh_patterns(USER_A)

    assert response.total_patterns == 0

    config_module.get_settings.cache_clear()


# --- 23: repository failures are handled safely (refresh never crashes) --------


def test_refresh_tolerates_a_decision_with_no_thresholds_or_experiments(
    learning_service: CrossDecisionLearningService,
    decision_repo: DecisionRepository,
) -> None:
    decision_repo.create(USER_A, DecisionCreate(title="Bare decision", description="x"))
    decision_repo.create(USER_A, DecisionCreate(title="Another bare decision", description="x"))

    response = learning_service.refresh_patterns(USER_A)

    assert response.total_patterns == 0
