"""Tests for `DecisionEvolutionService` - the read-only Decision Evolution
& Causal Timeline assembly (REGRET ENGINE 2.0, Step 22).

No LLM/Strands invocation happens anywhere in this file - event assembly
is entirely deterministic Python. Tests seed decisions/assumptions/
thresholds/regret-scenarios/experiments directly through
`DecisionRepository` (mirroring `test_adaptive_service.py`'s seeding
pattern), drive the real `ReEvaluationService`/`MemoryService` to produce
genuine downstream records, then exercise `DecisionEvolutionService`
against them - never against fabricated inputs.

The MANDATORY test required by the spec is
`test_supported_to_weakened_exposes_previous_new_state_source_and_reason`.
"""

from uuid import uuid4

import pytest

from app.adaptive.repository import AdaptiveStateRepository
from app.evolution.repository import DecisionEvolutionRepository
from app.evolution.schemas import EvolutionEventType, EvolutionImpact
from app.evolution.service import DecisionEvolutionService
from app.memory.memory_repository import MemoryRepository
from app.memory.memory_service import MemoryService
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.decision_repository import DecisionRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.value_of_information_repository import ValueOfInformationRepository
from app.schemas.decision import DecisionCreate
from app.schemas.experiment_result import ExperimentResultCreate
from app.services.re_evaluation_service import ReEvaluationService

USER_A = "user-a"


@pytest.fixture
def decision_repo(dynamodb_table: None) -> DecisionRepository:
    return DecisionRepository()


@pytest.fixture
def analysis_repo(dynamodb_table: None) -> AnalysisRepository:
    return AnalysisRepository()


@pytest.fixture
def evidence_repo(dynamodb_table: None) -> EvidenceRepository:
    return EvidenceRepository()


@pytest.fixture
def memory_repo(dynamodb_table: None) -> MemoryRepository:
    return MemoryRepository()


@pytest.fixture
def voi_repo(dynamodb_table: None) -> ValueOfInformationRepository:
    return ValueOfInformationRepository()


@pytest.fixture
def adaptive_repo(dynamodb_table: None) -> AdaptiveStateRepository:
    return AdaptiveStateRepository()


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
def evolution_repo(
    decision_repo: DecisionRepository,
    analysis_repo: AnalysisRepository,
    evidence_repo: EvidenceRepository,
    memory_repo: MemoryRepository,
    voi_repo: ValueOfInformationRepository,
    adaptive_repo: AdaptiveStateRepository,
) -> DecisionEvolutionRepository:
    return DecisionEvolutionRepository(
        decision_repo, analysis_repo, evidence_repo, memory_repo, voi_repo, adaptive_repo
    )


@pytest.fixture
def evolution_service(
    decision_repo: DecisionRepository, evolution_repo: DecisionEvolutionRepository
) -> DecisionEvolutionService:
    return DecisionEvolutionService(decision_repo, evolution_repo, max_events=200)


def _seed_decision_with_threshold(decision_repo: DecisionRepository, user_id: str = USER_A):
    """Seeds one decision with an assumption, regret scenario, validated
    threshold, and a real experiment targeting it - mirrors
    `test_adaptive_service.py::_seed_two_uncertainty_decision`'s single-
    uncertainty variant."""
    decision = decision_repo.create(
        user_id,
        DecisionCreate(
            title="Open a cloud kitchen", description="Investment decision.", budget=500000
        ),
    )

    assumption = decision_repo.create_assumptions(
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
                "variable": "Customer retention rate",
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
                "hypothesis": "Customers reorder at a sufficient rate.",
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
        "scenario": scenario,
        "threshold": threshold,
        "experiment": experiment,
    }


# --- 1: empty timeline ---------------------------------------------------------


def test_empty_decision_has_only_a_decision_created_event(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
) -> None:
    decision = decision_repo.create(USER_A, DecisionCreate(title="Bare decision", description="x"))

    evolution = evolution_service.get_evolution(decision.id)

    assert len(evolution.timeline) == 1
    assert evolution.timeline[0].event_type == EvolutionEventType.DECISION_CREATED
    assert evolution.current_assessment == "insufficient_evidence"
    assert evolution.total_cycles == 0


def test_unknown_decision_raises_not_found(evolution_service: DecisionEvolutionService) -> None:
    from app.core.errors import NotFoundError

    with pytest.raises(NotFoundError):
        evolution_service.get_evolution(uuid4())


# --- 2: decision with only creation --------------------------------------------


def test_decision_created_event_uses_the_real_decision_title(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
) -> None:
    decision = decision_repo.create(
        USER_A, DecisionCreate(title="Should I open a cloud kitchen?", description="x")
    )

    evolution = evolution_service.get_evolution(decision.id)

    assert evolution.timeline[0].summary == "Should I open a cloud kitchen?"
    assert evolution.timeline[0].source_type == "decision"
    assert evolution.timeline[0].source_id == str(decision.id)


# --- 3: decision with analysis (assumption/blindspot/threshold/regret) --------


def test_analysis_stage_records_produce_their_own_identified_events(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
) -> None:
    seeded = _seed_decision_with_threshold(decision_repo)

    evolution = evolution_service.get_evolution(seeded["decision"].id)
    types = {event.event_type for event in evolution.timeline}

    assert EvolutionEventType.ASSUMPTION_IDENTIFIED in types
    assert EvolutionEventType.REGRET_SCENARIO_IDENTIFIED in types
    assert EvolutionEventType.THRESHOLD_IDENTIFIED in types
    assert EvolutionEventType.EXPERIMENT_RECOMMENDED in types

    threshold_event = next(
        e for e in evolution.timeline if e.event_type == EvolutionEventType.THRESHOLD_IDENTIFIED
    )
    assert str(seeded["threshold"].id) in threshold_event.affected_threshold_ids


# --- 4, 5, 6: experiment lifecycle + result + re-evaluation --------------------


def test_experiment_result_and_reevaluation_produce_real_events(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
) -> None:
    seeded = _seed_decision_with_threshold(decision_repo)

    result, reeval = reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment"].id,
        ExperimentResultCreate(
            outcome="success",
            summary="30% retention observed.",
            measured_values={"Customer retention rate": 30},
        ),
    )

    evolution = evolution_service.get_evolution(seeded["decision"].id)
    types = {event.event_type for event in evolution.timeline}

    assert EvolutionEventType.EXPERIMENT_RESULT in types
    assert EvolutionEventType.EXPERIMENT_COMPLETED in types
    assert EvolutionEventType.RE_EVALUATION in types

    result_event = next(
        e for e in evolution.timeline if e.event_type == EvolutionEventType.EXPERIMENT_RESULT
    )
    assert result_event.source_id == str(result.id)
    assert result_event.summary == "30% retention observed."

    reeval_event = next(
        e for e in evolution.timeline if e.event_type == EvolutionEventType.RE_EVALUATION
    )
    assert reeval_event.source_id == str(reeval.id)


# --- 7: memory learning ---------------------------------------------------------


def test_memory_learning_produces_a_learning_recorded_event(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
    memory_service: MemoryService,
) -> None:
    seeded = _seed_decision_with_threshold(decision_repo)

    result, reeval = reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment"].id,
        ExperimentResultCreate(
            outcome="success", summary="x", measured_values={"Customer retention rate": 30}
        ),
    )
    memory_service.update_memory_from_reevaluation(
        seeded["decision"].id, seeded["experiment"].id, result, reeval
    )

    evolution = evolution_service.get_evolution(seeded["decision"].id)
    learning_events = [
        e for e in evolution.timeline if e.event_type == EvolutionEventType.LEARNING_RECORDED
    ]

    assert len(learning_events) >= 1
    assert all(e.source_type == "memory_learning" for e in learning_events)


# --- MANDATORY: supported -> weakened exposes previous/new/source/reason ------


def test_supported_to_weakened_exposes_previous_new_state_source_and_reason(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
) -> None:
    """MANDATORY test (spec section 23 / step 6): when an experiment
    causes the decision's assessment to move from supported to weakened,
    the evolution API must expose the correct previous_state, new_state,
    source, and reason."""
    seeded = _seed_decision_with_threshold(decision_repo)

    # First result: retention comes in strong -> strengthens the decision.
    reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment"].id,
        ExperimentResultCreate(
            outcome="success",
            summary="Strong retention.",
            measured_values={"Customer retention rate": 30},
        ),
    )

    # Second threshold + experiment, targeting the SAME assumption, so a
    # second real re-evaluation can move the assessment the other way.
    threshold_2 = decision_repo.create_thresholds(
        seeded["decision"].id,
        [
            {
                "variable": "Customer retention rate",
                "validation_status": "validated",
                "derivation": "calculated_from_evidence",
                "threshold_value": "24",
                "direction": "below",
                "related_assumption_ids": [str(seeded["assumption"].id)],
                "related_regret_scenario_ids": [str(seeded["scenario"].id)],
            }
        ],
    )[0]
    experiment_2 = decision_repo.create_experiments(
        seeded["decision"].id,
        [
            {
                "title": "Second retention check",
                "hypothesis": "Retention holds over a longer window.",
                "target_threshold_id": str(threshold_2.id),
                "decision_rule": "x",
                "feasibility": "high",
                "reversibility": "high",
                "estimated_cost": 500,
            }
        ],
    )[0]

    # Second result: retention drops below the threshold -> weakens the decision.
    _, reeval_2 = reeval_service.submit_result(
        seeded["decision"].id,
        experiment_2.id,
        ExperimentResultCreate(
            outcome="failure",
            summary="Retention dropped.",
            measured_values={"Customer retention rate": 10},
        ),
    )

    assert reeval_2.decision_assessment.status.value == "weakened"
    assert reeval_2.previous_assessment != reeval_2.new_assessment

    evolution = evolution_service.get_evolution(seeded["decision"].id)
    assessment_changed_events = [
        e for e in evolution.timeline if e.event_type == EvolutionEventType.ASSESSMENT_CHANGED
    ]

    assert len(assessment_changed_events) >= 1
    matching = [e for e in assessment_changed_events if e.source_id == str(reeval_2.id)]
    assert len(matching) == 1
    event = matching[0]

    assert event.previous_state == reeval_2.previous_assessment
    assert event.new_state == reeval_2.new_assessment
    assert event.source_type == "re_evaluation"
    assert event.source_id == str(reeval_2.id)
    assert event.reason is not None
    assert event.reason == reeval_2.decision_assessment.summary
    assert event.impact == EvolutionImpact.MAJOR

    # Also confirmed via the standalone event-detail lookup, not just the
    # bulk timeline - both code paths must agree.
    detail = evolution_service.get_event(seeded["decision"].id, event.event_id)
    assert detail.previous_state == reeval_2.previous_assessment
    assert detail.new_state == reeval_2.new_assessment


# --- threshold validated / failed -----------------------------------------------


def test_threshold_validated_event_has_validated_new_state(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
) -> None:
    seeded = _seed_decision_with_threshold(decision_repo)

    reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment"].id,
        ExperimentResultCreate(
            outcome="success", summary="x", measured_values={"Customer retention rate": 30}
        ),
    )

    evolution = evolution_service.get_evolution(seeded["decision"].id)
    validated_events = [
        e for e in evolution.timeline if e.event_type == EvolutionEventType.THRESHOLD_VALIDATED
    ]

    assert len(validated_events) == 1
    assert validated_events[0].new_state == "validated"
    assert str(seeded["threshold"].id) in validated_events[0].affected_threshold_ids


def test_threshold_failed_event_has_failed_new_state(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
) -> None:
    seeded = _seed_decision_with_threshold(decision_repo)

    reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment"].id,
        ExperimentResultCreate(
            outcome="failure", summary="x", measured_values={"Customer retention rate": 10}
        ),
    )

    evolution = evolution_service.get_evolution(seeded["decision"].id)
    failed_events = [
        e for e in evolution.timeline if e.event_type == EvolutionEventType.THRESHOLD_FAILED
    ]

    assert len(failed_events) == 1
    assert failed_events[0].new_state == "failed"


# --- adaptive cycle / VOI change -------------------------------------------------


def test_adaptive_cycle_produces_next_experiment_selected_event(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
) -> None:
    from app.adaptive.repository import AdaptiveStateRepository as _AdaptiveRepo
    from app.adaptive.service import AdaptiveExperimentService
    from app.agents.value_of_information import ValueOfInformationService
    from app.repositories.value_of_information_repository import (
        ValueOfInformationRepository as _VOIRepo,
    )

    seeded = _seed_decision_with_threshold(decision_repo)
    voi_service = ValueOfInformationService(decision_repo, _VOIRepo())
    voi_service.compute_and_persist(seeded["decision"])

    adaptive_service = AdaptiveExperimentService(decision_repo, _AdaptiveRepo(), voi_service)
    adaptive_service.advance_cycle(seeded["decision"], USER_A)

    evolution = evolution_service.get_evolution(seeded["decision"].id)
    selected_events = [
        e for e in evolution.timeline if e.event_type == EvolutionEventType.NEXT_EXPERIMENT_SELECTED
    ]

    assert len(selected_events) >= 1
    assert evolution.total_cycles == 1
    assert evolution.current_cycle == 1


# --- decision delta --------------------------------------------------------------


def test_decision_delta_for_assessment_changed_event_reflects_the_transition(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
) -> None:
    seeded = _seed_decision_with_threshold(decision_repo)

    reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment"].id,
        ExperimentResultCreate(
            outcome="failure", summary="x", measured_values={"Customer retention rate": 10}
        ),
    )

    evolution = evolution_service.get_evolution(seeded["decision"].id)
    event = next(
        e for e in evolution.timeline if e.event_type == EvolutionEventType.ASSESSMENT_CHANGED
    )

    delta = evolution_service.get_decision_delta(seeded["decision"].id, event.event_id)

    assert delta.changed is True
    assert delta.assessment_changed is True
    assert delta.explanation != ""


def test_decision_delta_for_unknown_event_id_raises_not_found(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
) -> None:
    from app.core.errors import NotFoundError

    decision = decision_repo.create(USER_A, DecisionCreate(title="x", description="x"))

    with pytest.raises(NotFoundError):
        evolution_service.get_decision_delta(decision.id, "not-a-real-event-id")


# --- event ordering / timestamps -------------------------------------------------


def test_timeline_is_sorted_oldest_first_by_real_timestamp(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
) -> None:
    seeded = _seed_decision_with_threshold(decision_repo)
    reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment"].id,
        ExperimentResultCreate(
            outcome="success", summary="x", measured_values={"Customer retention rate": 30}
        ),
    )

    evolution = evolution_service.get_evolution(seeded["decision"].id)
    timestamps = [event.timestamp for event in evolution.timeline]

    assert timestamps == sorted(timestamps)
    assert evolution.timeline[0].event_type == EvolutionEventType.DECISION_CREATED


# --- provenance / source ids ------------------------------------------------------


def test_every_event_has_a_real_traceable_source_id(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
) -> None:
    seeded = _seed_decision_with_threshold(decision_repo)
    reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment"].id,
        ExperimentResultCreate(
            outcome="success", summary="x", measured_values={"Customer retention rate": 30}
        ),
    )

    evolution = evolution_service.get_evolution(seeded["decision"].id)

    for event in evolution.timeline:
        assert event.source_id
        assert event.source_type


# --- historical insight labeling (never presented as current evidence) --------


def test_no_historical_insight_event_is_fabricated_without_real_history(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
) -> None:
    """This decision has no similar past decisions - the timeline must
    never invent a HISTORICAL event with no real HistoricalInsight behind
    it."""
    decision = decision_repo.create(USER_A, DecisionCreate(title="x", description="x"))

    evolution = evolution_service.get_evolution(decision.id)

    assert all(not e.is_historical for e in evolution.timeline)


# --- user isolation --------------------------------------------------------------


def test_user_isolation_evolution_only_shows_this_decisions_events(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
) -> None:
    seeded_a = _seed_decision_with_threshold(decision_repo, user_id="user-a")
    seeded_b = _seed_decision_with_threshold(decision_repo, user_id="user-b")

    evolution_a = evolution_service.get_evolution(seeded_a["decision"].id)
    evolution_b = evolution_service.get_evolution(seeded_b["decision"].id)

    assert evolution_a.decision_id != evolution_b.decision_id
    assert evolution_a.user_id == "user-a"
    assert evolution_b.user_id == "user-b"
    a_source_ids = {e.source_id for e in evolution_a.timeline}
    b_source_ids = {e.source_id for e in evolution_b.timeline}
    assert a_source_ids.isdisjoint(b_source_ids)


# --- bounded timeline (EVOLUTION_MAX_EVENTS) -------------------------------------


def test_timeline_is_bounded_by_max_events_and_keeps_the_newest(
    decision_repo: DecisionRepository,
    evolution_repo: DecisionEvolutionRepository,
) -> None:
    bounded_service = DecisionEvolutionService(decision_repo, evolution_repo, max_events=2)
    decision = decision_repo.create(USER_A, DecisionCreate(title="x", description="x"))
    decision_repo.create_assumptions(
        decision.id,
        [
            {
                "statement": "a1",
                "source": "implicit",
                "importance": "high",
                "confidence": 0.5,
                "evidence_status": "not_addressed",
            },
            {
                "statement": "a2",
                "source": "implicit",
                "importance": "high",
                "confidence": 0.5,
                "evidence_status": "not_addressed",
            },
            {
                "statement": "a3",
                "source": "implicit",
                "importance": "high",
                "confidence": 0.5,
                "evidence_status": "not_addressed",
            },
        ],
    )

    evolution = bounded_service.get_evolution(decision.id)

    assert evolution.truncated is True
    assert len(evolution.timeline) == 2
    # The newest events survive truncation, not the oldest.
    full_timeline = bounded_service.build_timeline(decision.id)
    assert evolution.timeline == full_timeline[-2:]


# --- idempotency / duplicate events ----------------------------------------------


def test_calling_get_evolution_twice_produces_identical_event_ids(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
) -> None:
    seeded = _seed_decision_with_threshold(decision_repo)
    reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment"].id,
        ExperimentResultCreate(
            outcome="success", summary="x", measured_values={"Customer retention rate": 30}
        ),
    )

    first = evolution_service.get_evolution(seeded["decision"].id)
    second = evolution_service.get_evolution(seeded["decision"].id)

    assert [e.event_id for e in first.timeline] == [e.event_id for e in second.timeline]


# --- get_current_state / get_major_changes ---------------------------------------


def test_get_current_state_matches_get_evolution(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
) -> None:
    decision = decision_repo.create(USER_A, DecisionCreate(title="x", description="x"))

    a = evolution_service.get_evolution(decision.id)
    b = evolution_service.get_current_state(decision.id)

    assert a.decision_id == b.decision_id
    assert [e.event_id for e in a.timeline] == [e.event_id for e in b.timeline]


def test_get_major_changes_only_returns_major_impact_events(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
    reeval_service: ReEvaluationService,
) -> None:
    seeded = _seed_decision_with_threshold(decision_repo)
    reeval_service.submit_result(
        seeded["decision"].id,
        seeded["experiment"].id,
        ExperimentResultCreate(
            outcome="success", summary="x", measured_values={"Customer retention rate": 30}
        ),
    )

    major_changes = evolution_service.get_major_changes(seeded["decision"].id)

    assert len(major_changes) > 0
    assert all(e.impact == EvolutionImpact.MAJOR for e in major_changes)


# --- missing/malformed records tolerance -----------------------------------------


def test_decision_with_no_experiments_or_thresholds_never_raises(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
) -> None:
    decision = decision_repo.create(USER_A, DecisionCreate(title="x", description="x"))
    decision_repo.create_assumptions(
        decision.id,
        [
            {
                "statement": "x",
                "source": "implicit",
                "importance": "low",
                "confidence": 0.5,
                "evidence_status": "not_addressed",
            }
        ],
    )

    evolution = evolution_service.get_evolution(decision.id)

    assert evolution.current_uncertainties  # the unresolved assumption shows up
    assert evolution.validated_thresholds == []
    assert evolution.failed_thresholds == []


def test_get_event_for_unknown_event_id_raises_not_found(
    evolution_service: DecisionEvolutionService,
    decision_repo: DecisionRepository,
) -> None:
    from app.core.errors import NotFoundError

    decision = decision_repo.create(USER_A, DecisionCreate(title="x", description="x"))

    with pytest.raises(NotFoundError):
        evolution_service.get_event(decision.id, "does-not-exist")
