"""Tests for `ReEvaluationService`.

No LLM/Strands invocation happens anywhere in this file - the entire
re-evaluation flow is deterministic Python. Tests seed a decision's
assumptions/thresholds/regret scenarios/experiments directly through
`DecisionRepository` (bypassing the agent pipeline) so the service can be
exercised in isolation.
"""

from uuid import uuid4

import pytest

from app.core.errors import NotFoundError, ValidationError
from app.repositories.decision_repository import DecisionRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.schemas.decision import DecisionCreate
from app.schemas.decision_resources import DecisionAssessmentStatus, ExperimentStatus
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
def service(
    decision_repo: DecisionRepository, evidence_repo: EvidenceRepository
) -> ReEvaluationService:
    return ReEvaluationService(decision_repo, evidence_repo)


def _seeded_decision(decision_repo: DecisionRepository):
    """Create a decision with one assumption, one regret scenario, one
    threshold (targeting the assumption + scenario), and one experiment
    (targeting the threshold) - the minimum wiring needed to exercise the
    full re-evaluation chain."""
    decision = decision_repo.create(
        USER_ID,
        DecisionCreate(
            title="Open a cloud kitchen",
            description="Considering a ₹5 lakh investment in a cloud kitchen.",
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
                "expected_information_gain": "high",
                "confidence": 0.7,
                "feasibility": "high",
                "reversibility": "high",
                "related_assumption_ids": [str(assumption.id)],
                "related_regret_scenario_ids": [str(scenario.id)],
            }
        ],
    )
    experiment = experiments[0]

    return decision, assumption, scenario, threshold, experiment


# --- 1: consumes Devil's Advocate output / assumptions / blindspots ---------
# (re-evaluation flow tests below cover the actual deterministic behavior)


def test_submit_result_missing_experiment_raises_not_found(service: ReEvaluationService) -> None:
    with pytest.raises(NotFoundError):
        service.submit_result(
            uuid4(),
            uuid4(),
            ExperimentResultCreate(outcome="success", summary="x"),
        )


def test_submit_result_for_cancelled_experiment_raises_validation_error(
    service: ReEvaluationService, decision_repo: DecisionRepository
) -> None:
    decision, _, _, _, experiment = _seeded_decision(decision_repo)
    decision_repo.update_experiment_status(decision.id, experiment.id, ExperimentStatus.CANCELLED)

    with pytest.raises(ValidationError):
        service.submit_result(
            decision.id,
            experiment.id,
            ExperimentResultCreate(outcome="success", summary="x"),
        )


def test_submit_result_with_fabricated_evidence_id_raises_validation_error(
    service: ReEvaluationService, decision_repo: DecisionRepository
) -> None:
    decision, *_, experiment = _seeded_decision(decision_repo)

    with pytest.raises(ValidationError):
        service.submit_result(
            decision.id,
            experiment.id,
            ExperimentResultCreate(
                outcome="success", summary="x", evidence_ids=[str(uuid4())]
            ),
        )


# --- Experiment lifecycle: completed after result submission ----------------


def test_experiment_becomes_completed_after_result_submission(
    service: ReEvaluationService, decision_repo: DecisionRepository
) -> None:
    decision, *_, experiment = _seeded_decision(decision_repo)

    service.submit_result(
        decision.id, experiment.id, ExperimentResultCreate(outcome="failure", summary="x")
    )

    updated = decision_repo.get_experiment_by_id(experiment.id)
    assert updated is not None
    assert updated.status == "completed"


# --- Result persistence -------------------------------------------------------


def test_result_is_persisted_and_retrievable(
    service: ReEvaluationService, decision_repo: DecisionRepository
) -> None:
    decision, *_, experiment = _seeded_decision(decision_repo)

    result, _ = service.submit_result(
        decision.id,
        experiment.id,
        ExperimentResultCreate(
            outcome="failure",
            summary="18 of 100 customers reordered.",
            observations=["18 of 100 customers reordered."],
            measured_values={"Repeat-order rate": 18},
        ),
    )

    stored = decision_repo.list_experiment_results(decision.id, experiment.id)
    assert len(stored) == 1
    assert stored[0].id == result.id
    assert stored[0].outcome == "failure"
    assert stored[0].measured_values == {"Repeat-order rate": 18}


# --- Threshold re-evaluation: missed ------------------------------------------


def test_threshold_missed_weakens_decision_and_contradicts_validated_assumption(
    service: ReEvaluationService, decision_repo: DecisionRepository
) -> None:
    """18% observed vs a validated 'below 24%' threshold -> MISSED ->
    decision WEAKENED, assumption CONTRADICTED (validated threshold)."""
    decision, assumption, scenario, threshold, experiment = _seeded_decision(decision_repo)

    _, reevaluation = service.submit_result(
        decision.id,
        experiment.id,
        ExperimentResultCreate(
            outcome="failure",
            summary="18 of 100 customers reordered.",
            measured_values={"Repeat-order rate": 18},
        ),
    )

    assert reevaluation.decision_assessment.status is DecisionAssessmentStatus.WEAKENED
    assert len(reevaluation.threshold_comparisons) == 1
    assert reevaluation.threshold_comparisons[0].status == "missed"
    assert reevaluation.threshold_comparisons[0].threshold_id == str(threshold.id)

    assert len(reevaluation.assumption_reevaluations) == 1
    assert reevaluation.assumption_reevaluations[0].assumption_id == str(assumption.id)
    assert reevaluation.assumption_reevaluations[0].new_status == "contradicted"

    assert len(reevaluation.regret_scenario_reevaluations) == 1
    assert reevaluation.regret_scenario_reevaluations[0].regret_scenario_id == str(scenario.id)
    assert reevaluation.regret_scenario_reevaluations[0].new_status == "evidence_strengthened"


# --- Threshold re-evaluation: met ---------------------------------------------


def test_threshold_met_strengthens_decision_and_supports_assumption(
    service: ReEvaluationService, decision_repo: DecisionRepository
) -> None:
    """30% observed vs a validated 'below 24%' threshold -> MET ->
    decision STRENGTHENED, assumption SUPPORTED."""
    decision, assumption, scenario, _, experiment = _seeded_decision(decision_repo)

    _, reevaluation = service.submit_result(
        decision.id,
        experiment.id,
        ExperimentResultCreate(
            outcome="success",
            summary="30 of 100 customers reordered.",
            measured_values={"Repeat-order rate": 30},
        ),
    )

    assert reevaluation.decision_assessment.status is DecisionAssessmentStatus.STRENGTHENED
    assert reevaluation.threshold_comparisons[0].status == "met"
    assert reevaluation.assumption_reevaluations[0].new_status == "supported"
    assert reevaluation.regret_scenario_reevaluations[0].new_status == "evidence_weakened"


# --- Threshold re-evaluation against a provisional (not validated) threshold -


def test_missed_provisional_threshold_yields_still_uncertain_not_contradicted(
    decision_repo: DecisionRepository, evidence_repo: EvidenceRepository
) -> None:
    """A MISSED comparison against a merely provisional threshold must not
    be escalated to CONTRADICTED - the bar itself was never validated."""
    _seeded_decision(decision_repo)  # sanity: seeding helper still works standalone
    service = ReEvaluationService(decision_repo, evidence_repo)

    # Simulate a provisional threshold by seeding a fresh decision where the
    # threshold's validation_status is "provisional" instead of "validated"
    # (there is no direct update method for a threshold's validation_status -
    # thresholds are only ever created fresh by the Threshold Engine).
    decision2 = decision_repo.create(
        USER_ID,
        DecisionCreate(title="x", description="x"),
    )
    assumptions2 = decision_repo.create_assumptions(
        decision2.id,
        [
            {
                "statement": "x",
                "source": "implicit",
                "importance": "critical",
                "confidence": 0.4,
                "evidence_status": "not_addressed",
                "dependency": "x",
                "failure_consequence": "x",
            }
        ],
    )
    thresholds2 = decision_repo.create_thresholds(
        decision2.id,
        [
            {
                "variable": "Repeat-order rate",
                "threshold_type": "numeric",
                "direction": "below",
                "threshold_value": "24",
                "confidence": 0.5,
                "derivation": "derived_from_existing_analysis",
                "consequence": "x",
                "related_assumption_ids": [str(assumptions2[0].id)],
                "evidence_basis": "x",
                "validation_status": "provisional",
            }
        ],
    )
    experiments2 = decision_repo.create_experiments(
        decision2.id,
        [
            {
                "title": "x",
                "hypothesis": "x",
                "target_threshold_id": str(thresholds2[0].id),
                "variable_to_test": "Repeat-order rate",
                "decision_rule": "x",
                "expected_information_gain": "medium",
                "confidence": 0.5,
                "feasibility": "high",
                "reversibility": "high",
                "related_assumption_ids": [str(assumptions2[0].id)],
            }
        ],
    )

    _, reevaluation = service.submit_result(
        decision2.id,
        experiments2[0].id,
        ExperimentResultCreate(
            outcome="failure", summary="x", measured_values={"Repeat-order rate": 18}
        ),
    )

    assert reevaluation.assumption_reevaluations[0].new_status == "still_uncertain"


# --- Inconclusive experiments: small sample / narrow miss --------------------


def test_ambiguous_direction_produces_inconclusive_assessment_not_a_verdict(
    service: ReEvaluationService, decision_repo: DecisionRepository
) -> None:
    """A threshold with an ambiguous direction can't yield a met/missed
    judgment - the assessment must be inconclusive, not a fabricated verdict."""
    decision = decision_repo.create(
        USER_ID, DecisionCreate(title="x", description="x")
    )
    thresholds = decision_repo.create_thresholds(
        decision.id,
        [
            {
                "variable": "Conversion rate",
                "threshold_type": "numeric",
                "direction": "fails",  # not below/above/equals - ambiguous
                "threshold_value": "5",
                "confidence": 0.5,
                "derivation": "qualitative",
                "consequence": "x",
                "evidence_basis": "x",
                "validation_status": "unknown",
            }
        ],
    )
    experiments = decision_repo.create_experiments(
        decision.id,
        [
            {
                "title": "x",
                "hypothesis": "x",
                "target_threshold_id": str(thresholds[0].id),
                "variable_to_test": "Conversion rate",
                "decision_rule": "x",
                "expected_information_gain": "low",
                "confidence": 0.5,
                "feasibility": "medium",
                "reversibility": "high",
            }
        ],
    )

    _, reevaluation = service.submit_result(
        decision.id,
        experiments[0].id,
        ExperimentResultCreate(
            outcome="inconclusive", summary="x", measured_values={"Conversion rate": 4}
        ),
    )

    assert reevaluation.decision_assessment.status is DecisionAssessmentStatus.INCONCLUSIVE


# --- Partial results: some criteria met, no measured value for others -------


def test_no_matching_measured_value_falls_back_to_declared_outcome(
    service: ReEvaluationService, decision_repo: DecisionRepository
) -> None:
    decision, assumption, scenario, threshold, experiment = _seeded_decision(decision_repo)

    _, reevaluation = service.submit_result(
        decision.id,
        experiment.id,
        ExperimentResultCreate(
            outcome="partial",
            summary="Some success criteria met, repeat rate not directly measured.",
            measured_values={"Conversion rate": 5, "Acquisition cost": 200},
        ),
    )

    # Neither measured key matches the threshold's variable and there is
    # more than one candidate, so no comparison could be made.
    expected_status = DecisionAssessmentStatus.REQUIRES_MORE_EVIDENCE
    assert reevaluation.decision_assessment.status is expected_status
    assert reevaluation.threshold_comparisons[0].status == "unknown"


# --- History preservation: original analysis untouched -----------------------


def test_original_threshold_and_assumption_records_are_never_mutated(
    service: ReEvaluationService, decision_repo: DecisionRepository
) -> None:
    decision, assumption, scenario, threshold, experiment = _seeded_decision(decision_repo)

    service.submit_result(
        decision.id,
        experiment.id,
        ExperimentResultCreate(
            outcome="failure", summary="x", measured_values={"Repeat-order rate": 18}
        ),
    )

    thresholds_after = decision_repo.list_thresholds(decision.id)
    assumptions_after = decision_repo.list_assumptions(decision.id)
    assert len(thresholds_after) == 1
    assert thresholds_after[0].threshold_value == "24"  # unchanged, never overwritten
    assert len(assumptions_after) == 1
    assert assumptions_after[0].statement == assumption.statement  # unchanged


def test_multiple_reevaluations_can_exist_and_are_all_preserved(
    service: ReEvaluationService, decision_repo: DecisionRepository
) -> None:
    decision, *_, experiment = _seeded_decision(decision_repo)

    service.submit_result(
        decision.id,
        experiment.id,
        ExperimentResultCreate(
            outcome="failure", summary="First pilot.", measured_values={"Repeat-order rate": 18}
        ),
    )

    # A second experiment on the same decision, re-testing after changes.
    thresholds = decision_repo.list_thresholds(decision.id)
    experiments2 = decision_repo.create_experiments(
        decision.id,
        [
            {
                "title": "Second pilot",
                "hypothesis": "x",
                "target_threshold_id": str(thresholds[0].id),
                "variable_to_test": "Repeat-order rate",
                "decision_rule": "x",
                "expected_information_gain": "high",
                "confidence": 0.7,
                "feasibility": "high",
                "reversibility": "high",
            }
        ],
    )
    service.submit_result(
        decision.id,
        experiments2[0].id,
        ExperimentResultCreate(
            outcome="success", summary="Second pilot.", measured_values={"Repeat-order rate": 30}
        ),
    )

    reevaluations = decision_repo.list_reevaluations(decision.id)
    assert len(reevaluations) == 2
    statuses = {r.decision_assessment.status for r in reevaluations}
    assert DecisionAssessmentStatus.WEAKENED in statuses
    assert DecisionAssessmentStatus.STRENGTHENED in statuses


def test_reevaluation_key_learning_and_next_step_never_state_an_absolute_verdict(
    service: ReEvaluationService, decision_repo: DecisionRepository
) -> None:
    """Product safety principle: a failed experiment must never be phrased
    as an unconditional 'never invest' - see module docstring."""
    decision, *_, experiment = _seeded_decision(decision_repo)

    _, reevaluation = service.submit_result(
        decision.id,
        experiment.id,
        ExperimentResultCreate(
            outcome="failure", summary="x", measured_values={"Repeat-order rate": 18}
        ),
    )

    lowered_next_step = reevaluation.recommended_next_step.lower()
    assert "never invest" not in lowered_next_step
    assert "do not" in lowered_next_step or "not yet" in lowered_next_step
