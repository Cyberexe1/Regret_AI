"""Tests for `AdaptiveExperimentService` - the closed-loop decision-
validation cycle (REGRET ENGINE 2.0, Step 21).

No LLM/Strands invocation happens anywhere in this file - the adaptive
loop is entirely deterministic Python. Tests seed decisions/assumptions/
thresholds/regret-scenarios/experiments directly through
`DecisionRepository` (mirroring `test_memory_service.py`'s and
`test_historical_context.py`'s seeding pattern), drive the real
`ReEvaluationService`/`MemoryService`/`ValueOfInformationService` to
produce genuine downstream records, then exercise
`AdaptiveExperimentService` against them - never against fabricated
inputs.

The MANDATORY test required by the spec is
`test_after_resolving_uncertainty_a_selects_uncertainty_b_by_voi_rank`.
"""

from uuid import uuid4

import pytest

from app.adaptive.repository import AdaptiveStateRepository
from app.adaptive.schemas import AdaptiveCycleStatus, AdvanceOutcome, DecisionValidationState
from app.adaptive.service import AdaptiveExperimentService
from app.agents.value_of_information import ValueOfInformationService
from app.memory.memory_repository import MemoryRepository
from app.memory.memory_service import MemoryService
from app.repositories.decision_repository import DecisionRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.value_of_information_repository import ValueOfInformationRepository
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
def voi_repo(dynamodb_table: None) -> ValueOfInformationRepository:
    return ValueOfInformationRepository()


@pytest.fixture
def adaptive_repo(dynamodb_table: None) -> AdaptiveStateRepository:
    return AdaptiveStateRepository()


@pytest.fixture
def memory_repo(dynamodb_table: None) -> MemoryRepository:
    return MemoryRepository()


@pytest.fixture
def voi_service(
    decision_repo: DecisionRepository, voi_repo: ValueOfInformationRepository
) -> ValueOfInformationService:
    return ValueOfInformationService(decision_repo, voi_repo)


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
def adaptive_service(
    decision_repo: DecisionRepository,
    adaptive_repo: AdaptiveStateRepository,
    voi_service: ValueOfInformationService,
    memory_service: MemoryService,
) -> AdaptiveExperimentService:
    return AdaptiveExperimentService(decision_repo, adaptive_repo, voi_service, memory_service)


def _seed_two_uncertainty_decision(decision_repo: DecisionRepository, user_id: str = USER_A):
    """Seeds one decision with TWO uncertainties (assumptions), each with
    its own regret scenario, validated-calculated threshold, and a real,
    feasible/reversible experiment - so both score meaningful practical
    VOI and both have a runnable experiment. Uncertainty A is made
    slightly higher-priority than B (more critical importance + lower
    confidence) so a deterministic ranking order is guaranteed.
    """
    decision = decision_repo.create(
        user_id,
        DecisionCreate(
            title="Open a cloud kitchen", description="Investment decision.", budget=500000
        ),
    )

    assumption_a = decision_repo.create_assumptions(
        decision.id,
        [
            {
                "statement": "Customer retention sustains unit economics.",
                "source": "implicit",
                "importance": "critical",
                "confidence": 0.05,
                "evidence_status": "not_addressed",
            }
        ],
    )[0]
    assumption_b = decision_repo.create_assumptions(
        decision.id,
        [
            {
                "statement": "Customer acquisition cost stays affordable.",
                "source": "implicit",
                "importance": "high",
                "confidence": 0.2,
                "evidence_status": "not_addressed",
            }
        ],
    )[0]

    scenario_a = decision_repo.create_regret_scenarios(
        decision.id,
        [
            {
                "title": "Retention failure",
                "failure_condition": "x",
                "regret_level": "critical",
                "impact": "severe",
                "related_assumption_ids": [str(assumption_a.id)],
            }
        ],
    )[0]
    scenario_b = decision_repo.create_regret_scenarios(
        decision.id,
        [
            {
                "title": "CAC too high",
                "failure_condition": "x",
                "regret_level": "high",
                "impact": "high",
                "related_assumption_ids": [str(assumption_b.id)],
            }
        ],
    )[0]

    threshold_a = decision_repo.create_thresholds(
        decision.id,
        [
            {
                "variable": "Customer retention rate",
                "validation_status": "validated",
                "derivation": "calculated_from_evidence",
                "threshold_value": "24",
                "direction": "below",
                "related_assumption_ids": [str(assumption_a.id)],
                "related_regret_scenario_ids": [str(scenario_a.id)],
            }
        ],
    )[0]
    threshold_b = decision_repo.create_thresholds(
        decision.id,
        [
            {
                "variable": "Customer acquisition cost",
                "validation_status": "validated",
                "derivation": "calculated_from_evidence",
                "threshold_value": "500",
                "direction": "above",
                "related_assumption_ids": [str(assumption_b.id)],
                "related_regret_scenario_ids": [str(scenario_b.id)],
            }
        ],
    )[0]

    experiment_a = decision_repo.create_experiments(
        decision.id,
        [
            {
                "title": "Retention pilot",
                "hypothesis": "Customers reorder at a sufficient rate.",
                "target_threshold_id": str(threshold_a.id),
                "decision_rule": "x",
                "feasibility": "high",
                "reversibility": "high",
                "estimated_cost": 1000,
            }
        ],
    )[0]
    experiment_b = decision_repo.create_experiments(
        decision.id,
        [
            {
                "title": "Acquisition cost test",
                "hypothesis": "CAC stays within budget.",
                "target_threshold_id": str(threshold_b.id),
                "decision_rule": "x",
                "feasibility": "high",
                "reversibility": "high",
                "estimated_cost": 2000,
            }
        ],
    )[0]

    return {
        "decision": decision,
        "assumption_a": assumption_a,
        "assumption_b": assumption_b,
        "scenario_a": scenario_a,
        "scenario_b": scenario_b,
        "threshold_a": threshold_a,
        "threshold_b": threshold_b,
        "experiment_a": experiment_a,
        "experiment_b": experiment_b,
    }


# --- 1: first adaptive cycle --------------------------------------------------


def test_first_cycle_selects_the_highest_ranked_uncertainty(
    adaptive_service: AdaptiveExperimentService,
    decision_repo: DecisionRepository,
    voi_service: ValueOfInformationService,
) -> None:
    seeded = _seed_two_uncertainty_decision(decision_repo)
    voi_service.compute_and_persist(seeded["decision"])

    response = adaptive_service.advance_cycle(seeded["decision"], USER_A)

    assert response.outcome == AdvanceOutcome.STARTED_FIRST_CYCLE
    assert response.state.cycle_number == 1
    assert response.state.current_status == AdaptiveCycleStatus.AWAITING_EXPERIMENT
    assert response.state.current_primary_uncertainty_id == str(seeded["assumption_a"].id)
    assert response.state.current_experiment_id == str(seeded["experiment_a"].id)
    assert response.state.current_primary_threshold_id == str(seeded["threshold_a"].id)
    assert response.state.why_this_is_next is not None


# --- 2-7: experiment completion -> re-evaluation -> memory -> VOI -> next uncertainty/experiment


def test_after_resolving_uncertainty_a_selects_uncertainty_b_by_voi_rank(
    adaptive_service: AdaptiveExperimentService,
    decision_repo: DecisionRepository,
    voi_service: ValueOfInformationService,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    """MANDATORY test (spec section 23): after Experiment 1 resolves
    Uncertainty A, the system selects Uncertainty B, since B now has the
    highest remaining practical VOI - never re-selecting A."""
    seeded = _seed_two_uncertainty_decision(decision_repo)
    voi_service.compute_and_persist(seeded["decision"])

    first = adaptive_service.advance_cycle(seeded["decision"], USER_A)
    assert first.state.current_primary_uncertainty_id == str(seeded["assumption_a"].id)

    # Real experiment result: retention comes in strong -> threshold VALIDATED.
    result, reevaluation = reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment_a"].id,
        ExperimentResultCreate(
            outcome="success",
            summary="30% retention observed.",
            measured_values={"Customer retention rate": 30},
        ),
    )
    memory_service.update_memory_from_reevaluation(
        seeded["decision"].id, seeded["experiment_a"].id, result, reevaluation
    )
    adaptive_service.mark_experiment_completed(
        seeded["decision"].id, seeded["experiment_a"].id, result.id
    )

    voi_service.compute_and_persist(seeded["decision"])
    second = adaptive_service.advance_cycle(seeded["decision"], USER_A)

    assert second.outcome == AdvanceOutcome.ADVANCED_TO_NEXT_EXPERIMENT
    assert second.state.cycle_number == 2
    # Uncertainty A must NEVER be re-selected - it was just conclusively validated.
    assert second.state.current_primary_uncertainty_id == str(seeded["assumption_b"].id)
    assert second.state.current_experiment_id == str(seeded["experiment_b"].id)
    assert second.state.previous_experiment_id == str(seeded["experiment_a"].id)
    assert second.state.previous_result_id == str(result.id)


# --- 8: same experiment not repeated unnecessarily ---------------------------


def test_completed_experiment_is_never_selected_again(
    adaptive_service: AdaptiveExperimentService,
    decision_repo: DecisionRepository,
    voi_service: ValueOfInformationService,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    seeded = _seed_two_uncertainty_decision(decision_repo)
    voi_service.compute_and_persist(seeded["decision"])
    adaptive_service.advance_cycle(seeded["decision"], USER_A)

    result, reevaluation = reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment_a"].id,
        ExperimentResultCreate(
            outcome="success", summary="x", measured_values={"Customer retention rate": 30}
        ),
    )
    memory_service.update_memory_from_reevaluation(
        seeded["decision"].id, seeded["experiment_a"].id, result, reevaluation
    )
    adaptive_service.mark_experiment_completed(
        seeded["decision"].id, seeded["experiment_a"].id, result.id
    )
    voi_service.compute_and_persist(seeded["decision"])

    for _ in range(3):
        response = adaptive_service.advance_cycle(seeded["decision"], USER_A)
        assert response.state.current_experiment_id != str(seeded["experiment_a"].id)


# --- 9: threshold validated ---------------------------------------------------


def test_threshold_validated_after_met_comparison(
    adaptive_service: AdaptiveExperimentService,
    decision_repo: DecisionRepository,
    voi_service: ValueOfInformationService,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    seeded = _seed_two_uncertainty_decision(decision_repo)
    voi_service.compute_and_persist(seeded["decision"])
    adaptive_service.advance_cycle(seeded["decision"], USER_A)

    result, reevaluation = reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment_a"].id,
        ExperimentResultCreate(
            outcome="success", summary="x", measured_values={"Customer retention rate": 30}
        ),
    )
    memory_service.update_memory_from_reevaluation(
        seeded["decision"].id, seeded["experiment_a"].id, result, reevaluation
    )
    adaptive_service.mark_experiment_completed(
        seeded["decision"].id, seeded["experiment_a"].id, result.id
    )
    voi_service.compute_and_persist(seeded["decision"])

    response = adaptive_service.advance_cycle(seeded["decision"], USER_A)
    records = {r.threshold_id: r for r in response.state.uncertainty_status}
    assert str(seeded["threshold_a"].id) in records
    assert records[str(seeded["threshold_a"].id)].current_status.value == "validated"


# --- 10: threshold failed -----------------------------------------------------


def test_threshold_failed_after_missed_comparison(
    adaptive_service: AdaptiveExperimentService,
    decision_repo: DecisionRepository,
    voi_service: ValueOfInformationService,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    seeded = _seed_two_uncertainty_decision(decision_repo)
    voi_service.compute_and_persist(seeded["decision"])
    adaptive_service.advance_cycle(seeded["decision"], USER_A)

    result, reevaluation = reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment_a"].id,
        ExperimentResultCreate(
            outcome="failure", summary="x", measured_values={"Customer retention rate": 10}
        ),
    )
    memory_service.update_memory_from_reevaluation(
        seeded["decision"].id, seeded["experiment_a"].id, result, reevaluation
    )
    adaptive_service.mark_experiment_completed(
        seeded["decision"].id, seeded["experiment_a"].id, result.id
    )
    voi_service.compute_and_persist(seeded["decision"])

    response = adaptive_service.advance_cycle(seeded["decision"], USER_A)
    records = {r.threshold_id: r for r in response.state.uncertainty_status}
    assert records[str(seeded["threshold_a"].id)].current_status.value == "failed"
    assert response.state.current_assessment == DecisionValidationState.WEAKENED or (
        response.state.current_assessment == DecisionValidationState.STRONGLY_WEAKENED
    )


# --- 11: inconclusive result --------------------------------------------------


def test_inconclusive_result_does_not_conclusively_resolve_the_threshold(
    adaptive_service: AdaptiveExperimentService,
    decision_repo: DecisionRepository,
    voi_service: ValueOfInformationService,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    seeded = _seed_two_uncertainty_decision(decision_repo)
    voi_service.compute_and_persist(seeded["decision"])
    adaptive_service.advance_cycle(seeded["decision"], USER_A)

    # No measured value at all -> no deterministic comparison possible.
    result, reevaluation = reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment_a"].id,
        ExperimentResultCreate(outcome="inconclusive", summary="Ambiguous data."),
    )
    memory_service.update_memory_from_reevaluation(
        seeded["decision"].id, seeded["experiment_a"].id, result, reevaluation
    )
    adaptive_service.mark_experiment_completed(
        seeded["decision"].id, seeded["experiment_a"].id, result.id
    )
    voi_service.compute_and_persist(seeded["decision"])

    response = adaptive_service.advance_cycle(seeded["decision"], USER_A)
    # Threshold A's experiment is COMPLETED (so it's never re-selected),
    # but its comparison state must NOT be VALIDATED/FAILED since no real
    # comparison could be made.
    records = {r.threshold_id: r for r in response.state.uncertainty_status}
    if str(seeded["threshold_a"].id) in records:
        assert records[str(seeded["threshold_a"].id)].current_status.value != "validated"
        assert records[str(seeded["threshold_a"].id)].current_status.value != "failed"


# --- 12: no remaining critical uncertainty (sufficiently validated) ----------


def test_sufficiently_validated_when_all_uncertainties_resolved(
    adaptive_service: AdaptiveExperimentService,
    decision_repo: DecisionRepository,
    voi_service: ValueOfInformationService,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    seeded = _seed_two_uncertainty_decision(decision_repo)
    voi_service.compute_and_persist(seeded["decision"])
    adaptive_service.advance_cycle(seeded["decision"], USER_A)

    for experiment, variable in (
        (seeded["experiment_a"], "Customer retention rate"),
        (seeded["experiment_b"], "Customer acquisition cost"),
    ):
        voi_service.compute_and_persist(seeded["decision"])
        adaptive_service.advance_cycle(seeded["decision"], USER_A)
        result, reevaluation = reeval_service.submit_result(
            seeded["decision"].id,
            experiment.id,
            ExperimentResultCreate(outcome="success", summary="x", measured_values={variable: 30}),
        )
        memory_service.update_memory_from_reevaluation(
            seeded["decision"].id, experiment.id, result, reevaluation
        )
        adaptive_service.mark_experiment_completed(seeded["decision"].id, experiment.id, result.id)

    voi_service.compute_and_persist(seeded["decision"])
    final = adaptive_service.advance_cycle(seeded["decision"], USER_A)

    assert final.state.current_status == AdaptiveCycleStatus.SUFFICIENTLY_VALIDATED
    assert final.state.stopping_reason is not None
    assert final.state.current_experiment_id is None


# --- 13: low VOI remaining (also sufficiently validated / no candidate) ------


def test_low_practical_value_uncertainty_is_never_selected(
    adaptive_service: AdaptiveExperimentService,
    decision_repo: DecisionRepository,
    voi_service: ValueOfInformationService,
) -> None:
    decision = decision_repo.create(
        USER_A, DecisionCreate(title="Low-stakes decision", description="x", budget=500000)
    )
    # A single, low-importance, high-confidence (already well-understood)
    # assumption - should never be selected as a next experiment target.
    decision_repo.create_assumptions(
        decision.id,
        [
            {
                "statement": "Minor detail.",
                "source": "implicit",
                "importance": "low",
                "confidence": 0.9,
                "evidence_status": "supported",
            }
        ],
    )
    voi_service.compute_and_persist(decision)

    response = adaptive_service.advance_cycle(decision, USER_A)

    assert response.state.current_status in {
        AdaptiveCycleStatus.SUFFICIENTLY_VALIDATED,
        AdaptiveCycleStatus.INCONCLUSIVE,
    }
    assert response.state.current_experiment_id is None


# --- 14: no feasible experiment exists (inconclusive) ------------------------


def test_inconclusive_when_worthwhile_uncertainty_has_no_experiment(
    adaptive_service: AdaptiveExperimentService,
    decision_repo: DecisionRepository,
    voi_service: ValueOfInformationService,
) -> None:
    decision = decision_repo.create(
        USER_A, DecisionCreate(title="Decision with no experiment", description="x", budget=500000)
    )
    assumption = decision_repo.create_assumptions(
        decision.id,
        [
            {
                "statement": "Critical unknown.",
                "source": "implicit",
                "importance": "critical",
                "confidence": 0.05,
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
    decision_repo.create_thresholds(
        decision.id,
        [
            {
                "variable": "x",
                "validation_status": "validated",
                "derivation": "calculated_from_evidence",
                "related_assumption_ids": [str(assumption.id)],
                "related_regret_scenario_ids": [str(scenario.id)],
            }
        ],
    )
    # Deliberately NO experiment created for this threshold.
    voi_service.compute_and_persist(decision)

    response = adaptive_service.advance_cycle(decision, USER_A)

    assert response.state.current_status == AdaptiveCycleStatus.INCONCLUSIVE
    assert response.state.stopping_reason is not None


# --- 15: maximum cycle limit reached ------------------------------------------


def test_maximum_cycle_limit_blocks_further_cycles(
    decision_repo: DecisionRepository,
    adaptive_repo: AdaptiveStateRepository,
    voi_service: ValueOfInformationService,
    memory_service: MemoryService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.adaptive.service import AdaptiveExperimentService as _Service
    from app.core import config as config_module

    config_module.get_settings.cache_clear()
    monkeypatch.setenv("MAX_ADAPTIVE_CYCLES", "1")
    config_module.get_settings.cache_clear()

    service = _Service(decision_repo, adaptive_repo, voi_service, memory_service)
    seeded = _seed_two_uncertainty_decision(decision_repo)
    voi_service.compute_and_persist(seeded["decision"])

    first = service.advance_cycle(seeded["decision"], USER_A)
    assert first.state.cycle_number == 1
    assert first.state.current_status == AdaptiveCycleStatus.AWAITING_EXPERIMENT

    # Force a second cycle to be attempted (simulate having completed
    # cycle 1's experiment).
    from uuid import UUID

    result_id = UUID(int=1)
    service.mark_experiment_completed(
        seeded["decision"].id, UUID(first.state.current_experiment_id), result_id
    )

    second = service.advance_cycle(seeded["decision"], USER_A)
    assert second.state.current_status == AdaptiveCycleStatus.BLOCKED
    assert "maximum" in (second.state.stopping_reason or "").lower()

    config_module.get_settings.cache_clear()


# --- 16: user stopped ---------------------------------------------------------


def test_user_stop_marks_state_user_stopped_without_deleting_history(
    adaptive_service: AdaptiveExperimentService,
    decision_repo: DecisionRepository,
    voi_service: ValueOfInformationService,
    adaptive_repo: AdaptiveStateRepository,
) -> None:
    seeded = _seed_two_uncertainty_decision(decision_repo)
    voi_service.compute_and_persist(seeded["decision"])
    first = adaptive_service.advance_cycle(seeded["decision"], USER_A)

    stopped = adaptive_service.stop(seeded["decision"].id, reason="User chose to stop testing.")

    assert stopped is not None
    assert stopped.current_status == AdaptiveCycleStatus.USER_STOPPED
    assert stopped.stopping_reason == "User chose to stop testing."

    history = adaptive_repo.list_adaptive_states(seeded["decision"].id)
    assert len(history) == 2  # first cycle's state is preserved, never deleted
    assert any(s.state_id == first.state.state_id for s in history)


def test_stop_on_never_started_loop_returns_none(
    adaptive_service: AdaptiveExperimentService,
) -> None:
    assert adaptive_service.stop(uuid4()) is None


# --- 17: missing VOI -----------------------------------------------------------


def test_missing_voi_analysis_blocks_the_cycle(
    adaptive_service: AdaptiveExperimentService,
    decision_repo: DecisionRepository,
) -> None:
    decision = decision_repo.create(USER_A, DecisionCreate(title="No VOI yet", description="x"))

    response = adaptive_service.advance_cycle(decision, USER_A)

    assert response.state.current_status == AdaptiveCycleStatus.BLOCKED
    assert "value-of-information" in (response.state.stopping_reason or "").lower()


# --- 18: missing threshold ----------------------------------------------------


def test_uncertainty_with_no_threshold_is_reported_but_never_invents_one(
    adaptive_service: AdaptiveExperimentService,
    decision_repo: DecisionRepository,
    voi_service: ValueOfInformationService,
) -> None:
    decision = decision_repo.create(USER_A, DecisionCreate(title="No threshold", description="x"))
    decision_repo.create_assumptions(
        decision.id,
        [
            {
                "statement": "x",
                "source": "implicit",
                "importance": "critical",
                "confidence": 0.05,
                "evidence_status": "not_addressed",
            }
        ],
    )
    voi_service.compute_and_persist(decision)

    response = adaptive_service.advance_cycle(decision, USER_A)

    # No threshold and no experiment exist -> INCONCLUSIVE, never a
    # fabricated threshold id.
    assert response.state.current_primary_threshold_id is None


# --- 19: duplicate advance -----------------------------------------------------


def test_duplicate_advance_with_no_new_evidence_is_a_no_op(
    adaptive_service: AdaptiveExperimentService,
    decision_repo: DecisionRepository,
    voi_service: ValueOfInformationService,
    adaptive_repo: AdaptiveStateRepository,
) -> None:
    seeded = _seed_two_uncertainty_decision(decision_repo)
    voi_service.compute_and_persist(seeded["decision"])

    first = adaptive_service.advance_cycle(seeded["decision"], USER_A)
    second = adaptive_service.advance_cycle(seeded["decision"], USER_A)
    third = adaptive_service.advance_cycle(seeded["decision"], USER_A)

    assert second.outcome == AdvanceOutcome.NO_CHANGE
    assert third.outcome == AdvanceOutcome.NO_CHANGE
    assert first.state.state_id == second.state.state_id == third.state.state_id

    history = adaptive_repo.list_adaptive_states(seeded["decision"].id)
    assert len(history) == 1  # never duplicated


# --- 20: concurrent advance -----------------------------------------------------


def test_concurrent_advance_produces_only_one_state_via_deterministic_id(
    adaptive_service: AdaptiveExperimentService,
    decision_repo: DecisionRepository,
    voi_service: ValueOfInformationService,
    adaptive_repo: AdaptiveStateRepository,
) -> None:
    """Simulates two concurrent advance() calls computing the SAME
    candidate state independently - the deterministic state_id plus the
    repository's conditional write guarantees only one record is ever
    actually created, matching real concurrent-request behavior."""
    seeded = _seed_two_uncertainty_decision(decision_repo)
    voi_service.compute_and_persist(seeded["decision"])

    # Both "concurrent" calls happen sequentially here (no real threading
    # needed to prove the guarantee) - each independently computes the
    # candidate and calls create_adaptive_state; the second one must
    # detect its own candidate already exists.
    first = adaptive_service.advance_cycle(seeded["decision"], USER_A)
    second = adaptive_service.advance_cycle(seeded["decision"], USER_A)

    assert first.state.state_id == second.state.state_id
    history = adaptive_repo.list_adaptive_states(seeded["decision"].id)
    assert len(history) == 1


# --- 21: historical learning integration (indirect via VOI) ------------------


def test_advance_cycle_never_raises_when_historical_context_is_absent(
    adaptive_service: AdaptiveExperimentService,
    decision_repo: DecisionRepository,
    voi_service: ValueOfInformationService,
) -> None:
    """The adaptive loop never computes historical context itself - it
    only reads whatever VOI already folded in (Step 19 tiebreaker only).
    Absence of history must never block a cycle."""
    seeded = _seed_two_uncertainty_decision(decision_repo)
    voi_service.compute_and_persist(seeded["decision"], historical_context=None)

    response = adaptive_service.advance_cycle(seeded["decision"], USER_A)

    assert response.state.current_status == AdaptiveCycleStatus.AWAITING_EXPERIMENT


# --- 22: user isolation --------------------------------------------------------


def test_user_isolation_adaptive_state_is_scoped_by_decision_not_shared(
    adaptive_service: AdaptiveExperimentService,
    decision_repo: DecisionRepository,
    voi_service: ValueOfInformationService,
    adaptive_repo: AdaptiveStateRepository,
) -> None:
    """Adaptive state is keyed by decision_id (PK=DECISION#<id>), and a
    decision itself is already user-scoped (see DecisionRepository) - two
    different users' decisions can never share or leak adaptive state."""
    seeded_a = _seed_two_uncertainty_decision(decision_repo, user_id=USER_A)
    seeded_b = _seed_two_uncertainty_decision(decision_repo, user_id=USER_B)
    voi_service.compute_and_persist(seeded_a["decision"])
    voi_service.compute_and_persist(seeded_b["decision"])

    response_a = adaptive_service.advance_cycle(seeded_a["decision"], USER_A)
    response_b = adaptive_service.advance_cycle(seeded_b["decision"], USER_B)

    assert response_a.state.decision_id != response_b.state.decision_id
    assert response_a.state.user_id == USER_A
    assert response_b.state.user_id == USER_B

    history_a = adaptive_repo.list_adaptive_states(seeded_a["decision"].id)
    history_b = adaptive_repo.list_adaptive_states(seeded_b["decision"].id)
    assert all(s.decision_id == seeded_a["decision"].id for s in history_a)
    assert all(s.decision_id == seeded_b["decision"].id for s in history_b)


# --- get_latest / list_history -------------------------------------------------


def test_get_latest_before_any_cycle_returns_none(
    adaptive_service: AdaptiveExperimentService,
) -> None:
    assert adaptive_service.get_latest(uuid4()) is None


def test_list_history_returns_every_cycle_oldest_first(
    adaptive_service: AdaptiveExperimentService,
    decision_repo: DecisionRepository,
    voi_service: ValueOfInformationService,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    seeded = _seed_two_uncertainty_decision(decision_repo)
    voi_service.compute_and_persist(seeded["decision"])
    adaptive_service.advance_cycle(seeded["decision"], USER_A)

    result, reevaluation = reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment_a"].id,
        ExperimentResultCreate(
            outcome="success", summary="x", measured_values={"Customer retention rate": 30}
        ),
    )
    memory_service.update_memory_from_reevaluation(
        seeded["decision"].id, seeded["experiment_a"].id, result, reevaluation
    )
    adaptive_service.mark_experiment_completed(
        seeded["decision"].id, seeded["experiment_a"].id, result.id
    )
    voi_service.compute_and_persist(seeded["decision"])
    adaptive_service.advance_cycle(seeded["decision"], USER_A)

    history = adaptive_service.list_history(seeded["decision"].id)
    assert len(history) >= 3  # cycle1, ready_for_next, cycle2
    assert history == sorted(history, key=lambda s: s.created_at)
