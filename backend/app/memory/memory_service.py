"""Decision Memory business logic.

`MemoryService` is the only thing that builds or updates a `DecisionMemory`
or creates a `MemoryLearning`. It never re-runs the agent pipeline and
never calls Bedrock/Strands - every fact it records is read from
already-persisted `DecisionRepository` records (assumptions, thresholds,
regret scenarios, experiments) or from an already-computed
`ReEvaluationService` result (`ExperimentResult`, `ReEvaluation`,
`DecisionAssessment`). This mirrors the project's existing "deterministic
Python over LLM for factual comparisons" principle, applied here to memory
construction instead of threshold comparison.

Responsibilities (see module docstring in `app/memory/__init__.py`):

1. Build a preliminary memory from a decision's own analysis output.
2. Update memory after an experiment result + re-evaluation.
3. Extract validated learnings from a re-evaluation, deterministically.
4. Link learnings to the assumptions/thresholds/regret scenarios they
   actually reference (ids copied from the source record, never invented).
5. Retrieve a decision's memory + learning history.
6. Retrieve its unresolved uncertainties.
7. Provide a structured, historical context object for one decision.

Explicitly out of scope for this step (Step 18): no semantic similarity
across decisions, no ranking/recommendation from memory, no use of memory
to influence a *different*, future decision. That is Step 19's job - see
this module's own docstring warning against scope creep in
`docs/architecture.md`/README if reused there.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid5

from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.memory.memory_repository import MemoryRepository
from app.memory.memory_schemas import (
    DecisionMemory,
    DecisionMemoryResponse,
    LearningSourceType,
    LearningType,
    MemoryLearning,
    MemoryStage,
)
from app.repositories.decision_repository import DecisionRepository
from app.schemas.decision_resources import ExperimentResult as StoredExperimentResult
from app.schemas.decision_resources import ReEvaluation

logger = get_logger(__name__)

# Deterministic namespace for learning ids - see `_learning_id_for`. A
# fixed constant (not `uuid4`) so the same (experiment_result_id,
# learning_type) pair always maps to the same learning_id across process
# restarts, which is what makes duplicate-processing idempotent.
_LEARNING_ID_NAMESPACE = UUID("6f1a6b1a-8f3b-4b8a-9d8a-2f6f6a1a6b1a")


class MemoryService:
    """Builds and maintains Decision Memory from real, persisted evidence."""

    def __init__(
        self,
        memory_repository: MemoryRepository,
        decision_repository: DecisionRepository,
    ) -> None:
        self._memory = memory_repository
        self._decisions = decision_repository

    # --- 1 & 2: build / update ------------------------------------------------

    def get_or_create_preliminary_memory(self, decision_id: UUID) -> DecisionMemory:
        """Return the decision's memory, creating a PRELIMINARY one if none exists.

        A preliminary memory is deliberately thin: it references the
        decision's own critical assumptions/thresholds/regret
        scenarios/experiments (by id, never duplicating their content) and
        an `original_assessment` describing the analysis as it stands -
        but `outcome_summary`/`final_assessment` stay `None` and `stage`
        stays `preliminary` until a real experiment result exists. This is
        the explicit "KNOWN vs EXPECTED vs UNRESOLVED" distinction Step 18
        requires: nothing in a preliminary memory is presented as an
        observed outcome, because none exists yet.
        """
        existing = self._get_memory(decision_id)
        if existing is not None:
            return existing

        decision = self._decisions.get_raw(decision_id)
        if decision is None:
            raise NotFoundError(detail=f"Decision {decision_id} not found.")

        assumptions = self._decisions.list_assumptions(decision_id)
        thresholds = self._decisions.list_thresholds(decision_id)
        regret_scenarios = self._decisions.list_regret_scenarios(decision_id)
        experiments = self._decisions.list_experiments(decision_id)

        # "Critical" = the subset an agent stage itself flagged as most
        # important - never a re-scoring performed at this layer. Mirrors
        # the same importance-weight vocabulary the agents already use
        # (see e.g. `app.agents.schemas`'s importance fields), just
        # filtered rather than re-ranked.
        critical_assumption_ids = [
            str(a.id) for a in assumptions if (a.importance or "").lower() in {"critical", "high"}
        ]
        critical_threshold_ids = [str(t.id) for t in thresholds]
        critical_regret_scenario_ids = [
            str(s.id)
            for s in regret_scenarios
            if (s.regret_level or "").lower() in {"critical", "high"}
        ]

        # `Threshold.validation_status` reflects the Threshold Engine's own
        # confidence in *deriving* the value at analysis time - it says
        # nothing about whether the threshold has actually been tested
        # against real-world evidence. While `stage=preliminary` (no
        # experiment result submitted yet), every threshold remains
        # unresolved by definition, regardless of that derivation
        # confidence - "validated" analysis is still only EXPECTED, never
        # KNOWN, until a real result exists.
        unresolved: list[str] = []
        if not experiments:
            unresolved.append(
                "No experiment has been recommended or run yet for this decision."
            )
        else:
            for threshold in thresholds:
                unresolved.append(
                    f"The threshold for '{threshold.variable}' has not yet been tested "
                    "against a real experiment result."
                )

        now = datetime.now(UTC)
        memory = DecisionMemory(
            memory_id=uuid5(_LEARNING_ID_NAMESPACE, f"memory:{decision_id}"),
            decision_id=decision_id,
            user_id=decision["user_id"],
            decision_type=None,
            decision_summary=decision["title"],
            created_at=now,
            updated_at=now,
            stage=MemoryStage.PRELIMINARY,
            original_assessment=(
                f"Analysis identified {len(assumptions)} assumption(s), "
                f"{len(thresholds)} threshold(s), and {len(regret_scenarios)} regret "
                "scenario(s). No experiment result has been observed yet."
            ),
            critical_assumption_ids=critical_assumption_ids,
            critical_threshold_ids=critical_threshold_ids,
            critical_regret_scenario_ids=critical_regret_scenario_ids,
            experiment_ids=[str(e.id) for e in experiments],
            outcome_summary=None,
            validated_learnings=[],
            unresolved_uncertainties=unresolved,
            final_assessment=None,
            confidence=None,
            tags=[],
            source_analysis_run_id=None,
        )
        self._memory.create_memory(memory)
        logger.info(
            "Memory created decision_id=%s memory_id=%s stage=%s",
            decision_id,
            memory.memory_id,
            memory.stage.value,
        )
        return memory

    def update_memory_from_reevaluation(
        self,
        decision_id: UUID,
        experiment_id: UUID,
        stored_result: StoredExperimentResult,
        reevaluation: ReEvaluation,
    ) -> tuple[DecisionMemory, list[MemoryLearning]]:
        """The primary Decision Memory trigger: experiment result -> re-evaluation
        -> memory update -> learning records.

        Deterministic end to end. `stored_result`/`reevaluation` are the
        exact objects `ReEvaluationService.submit_result` already computed
        and persisted - this method never recomputes a threshold
        comparison or re-evaluates anything itself; it only *records* what
        `ReEvaluationService` already determined, plus updates the
        decision-level summary to reflect it.

        Idempotent: extracting learnings from the same
        `stored_result`/`reevaluation` pair twice produces the exact same
        `MemoryLearning` records (same deterministic ids), never
        duplicates - see `MemoryRepository.create_learning`.
        """
        memory = self.get_or_create_preliminary_memory(decision_id)

        learnings = self._extract_learnings(decision_id, stored_result, reevaluation)
        created_learnings: list[MemoryLearning] = []
        for learning in learnings:
            persisted, was_created = self._memory.create_learning(learning)
            created_learnings.append(persisted)
            if was_created:
                logger.info(
                    "Learning created decision_id=%s learning_id=%s learning_type=%s "
                    "source_type=%s source_id=%s",
                    decision_id,
                    persisted.learning_id,
                    persisted.learning_type.value,
                    persisted.source_type.value,
                    persisted.source_id,
                )

        assessment = reevaluation.decision_assessment
        experiment_ids = set(memory.experiment_ids)
        experiment_ids.add(str(experiment_id))

        validated_ids = [
            str(learning.learning_id)
            for learning in created_learnings
            if learning.learning_type
            in {
                LearningType.ASSUMPTION_VALIDATED,
                LearningType.ASSUMPTION_WEAKENED,
                LearningType.ASSUMPTION_FAILED,
                LearningType.THRESHOLD_VALIDATED,
                LearningType.THRESHOLD_FAILED,
                LearningType.DECISION_OUTCOME,
            }
        ]
        unresolved_ids = [
            str(learning.learning_id)
            for learning in created_learnings
            if learning.learning_type
            in {LearningType.THRESHOLD_INCONCLUSIVE, LearningType.UNRESOLVED_UNCERTAINTY}
        ]

        updated = memory.model_copy(
            update={
                "stage": MemoryStage.VALIDATED,
                "experiment_ids": sorted(experiment_ids),
                "outcome_summary": reevaluation.key_learning,
                "validated_learnings": sorted(set(memory.validated_learnings) | set(validated_ids)),
                "unresolved_uncertainties": _merge_unresolved(
                    memory.unresolved_uncertainties, unresolved_ids
                ),
                "final_assessment": assessment.summary,
                "confidence": assessment.confidence,
                "updated_at": datetime.now(UTC),
            }
        )
        self._memory.update_memory(updated)
        logger.info(
            "Memory updated decision_id=%s memory_id=%s stage=%s assessment=%s",
            decision_id,
            updated.memory_id,
            updated.stage.value,
            assessment.status.value,
        )
        return updated, created_learnings

    # --- 3 & 4: learning extraction -------------------------------------------

    def _extract_learnings(
        self,
        decision_id: UUID,
        stored_result: StoredExperimentResult,
        reevaluation: ReEvaluation,
    ) -> list[MemoryLearning]:
        """Deterministically convert one `ReEvaluation` into durable learnings.

        Every learning's `source_type`/`source_id` points at the real
        `ReEvaluation` record (`source_type=re_evaluation`) that produced
        it, except the one learning built directly from the experiment
        result's own submitted summary (`source_type=experiment_result`) -
        that one is the single place an LLM-free, user-authored fact
        (not a re-evaluation of it) is recorded as its own learning. No
        statement here claims a cause the source data doesn't establish -
        each one restates only what the threshold/assumption/regret
        scenario comparison, or the user's own submission, actually says.
        """
        now = datetime.now(UTC)
        learnings: list[MemoryLearning] = []
        result_id = stored_result.id
        reeval_id = reevaluation.id

        # One learning per threshold comparison actually performed.
        for comparison in reevaluation.threshold_comparisons:
            status = comparison.status.value
            if status == "met" or status == "within_range":
                learning_type = LearningType.THRESHOLD_VALIDATED
                statement = (
                    f"Observed {comparison.variable} met the recorded threshold "
                    f"({comparison.observed_value} vs {comparison.threshold_value or 'unknown'})."
                )
            elif status == "missed" or status == "outside_range":
                learning_type = LearningType.THRESHOLD_FAILED
                statement = (
                    f"Observed {comparison.variable} did not meet the recorded threshold "
                    f"({comparison.observed_value} vs {comparison.threshold_value or 'unknown'})."
                )
            elif status in {"above", "below", "inconclusive"}:
                learning_type = LearningType.THRESHOLD_INCONCLUSIVE
                statement = (
                    f"Observed {comparison.variable} ({comparison.observed_value}) could not "
                    "be clearly judged as meeting or missing the recorded threshold "
                    f"({comparison.threshold_value or 'unknown'})."
                )
            else:
                # unknown - no comparison could be made at all.
                learning_type = LearningType.UNRESOLVED_UNCERTAINTY
                statement = (
                    f"No measured value could be matched to the threshold for "
                    f"{comparison.variable}; it remains untested."
                )

            learnings.append(
                MemoryLearning(
                    learning_id=self._learning_id_for(
                        result_id, learning_type, comparison.threshold_id
                    ),
                    memory_id=self._existing_memory_id(decision_id),
                    decision_id=decision_id,
                    statement=statement,
                    learning_type=learning_type,
                    source_type=LearningSourceType.RE_EVALUATION,
                    source_id=reeval_id,
                    confidence=reevaluation.decision_assessment.confidence,
                    evidence_basis=[comparison.explanation],
                    observed_value=comparison.observed_value,
                    expected_value=comparison.threshold_value,
                    variance_description=comparison.explanation,
                    related_threshold_ids=[comparison.threshold_id],
                    created_at=now,
                )
            )

        # One learning per assumption re-evaluation actually performed.
        for assumption_reeval in reevaluation.assumption_reevaluations:
            new_status = assumption_reeval.new_status.value
            if new_status == "supported":
                learning_type = LearningType.ASSUMPTION_VALIDATED
            elif new_status == "contradicted":
                learning_type = LearningType.ASSUMPTION_FAILED
            elif new_status in {"partially_supported", "still_uncertain"}:
                learning_type = LearningType.ASSUMPTION_WEAKENED
            else:
                learning_type = LearningType.UNRESOLVED_UNCERTAINTY

            learnings.append(
                MemoryLearning(
                    learning_id=self._learning_id_for(
                        result_id, learning_type, assumption_reeval.assumption_id
                    ),
                    memory_id=self._existing_memory_id(decision_id),
                    decision_id=decision_id,
                    statement=assumption_reeval.explanation,
                    learning_type=learning_type,
                    source_type=LearningSourceType.RE_EVALUATION,
                    source_id=reeval_id,
                    confidence=reevaluation.decision_assessment.confidence,
                    related_assumption_ids=[assumption_reeval.assumption_id],
                    created_at=now,
                )
            )

        # One learning per regret scenario re-evaluation actually performed.
        for scenario_reeval in reevaluation.regret_scenario_reevaluations:
            learnings.append(
                MemoryLearning(
                    learning_id=self._learning_id_for(
                        result_id,
                        LearningType.EXPERIMENT_LEARNING,
                        scenario_reeval.regret_scenario_id,
                    ),
                    memory_id=self._existing_memory_id(decision_id),
                    decision_id=decision_id,
                    statement=scenario_reeval.explanation,
                    learning_type=LearningType.EXPERIMENT_LEARNING,
                    source_type=LearningSourceType.RE_EVALUATION,
                    source_id=reeval_id,
                    confidence=reevaluation.decision_assessment.confidence,
                    related_regret_scenario_ids=[scenario_reeval.regret_scenario_id],
                    created_at=now,
                )
            )

        # If nothing above fired at all (no threshold/assumption/scenario was
        # actually affected), the re-evaluation itself already recorded that
        # as UNCHANGED - record it as a single, unresolved-style learning so
        # the fact that an experiment ran without moving anything is not
        # silently lost.
        if not reevaluation.threshold_comparisons and not reevaluation.assumption_reevaluations:
            learnings.append(
                MemoryLearning(
                    learning_id=self._learning_id_for(
                        result_id, LearningType.DECISION_OUTCOME, str(reeval_id)
                    ),
                    memory_id=self._existing_memory_id(decision_id),
                    decision_id=decision_id,
                    statement=reevaluation.decision_assessment.summary,
                    learning_type=LearningType.DECISION_OUTCOME,
                    source_type=LearningSourceType.RE_EVALUATION,
                    source_id=reeval_id,
                    confidence=reevaluation.decision_assessment.confidence,
                    created_at=now,
                )
            )

        # Always record the raw, user-authored result itself as one more
        # learning, distinct from the re-evaluation's interpretation of
        # it - this is the "what actually happened, in the user's own
        # words" fact, sourced directly from ExperimentResult, never
        # rephrased by an LLM.
        learnings.append(
            MemoryLearning(
                learning_id=self._learning_id_for(
                    result_id, LearningType.EXPERIMENT_LEARNING, "summary"
                ),
                memory_id=self._existing_memory_id(decision_id),
                decision_id=decision_id,
                statement=stored_result.summary,
                learning_type=LearningType.EXPERIMENT_LEARNING,
                source_type=LearningSourceType.EXPERIMENT_RESULT,
                source_id=result_id,
                confidence=None,
                created_at=now,
            )
        )

        return learnings

    def _learning_id_for(
        self, experiment_result_id: UUID, learning_type: LearningType, discriminator: str
    ) -> UUID:
        """Deterministic learning id from (experiment_result_id, learning_type,
        discriminator) - see `MemoryRepository.create_learning` for why this
        is what makes duplicate processing idempotent. `discriminator`
        disambiguates multiple learnings of the same type from the same
        result (e.g. two different thresholds both MET in one result).
        """
        return uuid5(
            _LEARNING_ID_NAMESPACE,
            f"learning:{experiment_result_id}:{learning_type.value}:{discriminator}",
        )

    def _existing_memory_id(self, decision_id: UUID) -> UUID:
        """The deterministic memory id for a decision - see
        `get_or_create_preliminary_memory`. Learnings always reference the
        same memory id a decision's summary uses, without an extra read,
        since it's derived the same deterministic way here as there.
        """
        return uuid5(_LEARNING_ID_NAMESPACE, f"memory:{decision_id}")

    # --- 5, 6, 7: retrieval ----------------------------------------------------

    def get_memory(self, decision_id: UUID) -> DecisionMemory | None:
        return self._get_memory(decision_id)

    def get_memory_by_id(self, memory_id: UUID) -> DecisionMemory | None:
        return self._memory.get_memory_by_id(memory_id)

    def list_learnings(self, decision_id: UUID) -> list[MemoryLearning]:
        return self._memory.list_learnings_for_decision(decision_id)

    def get_memory_context(self, decision_id: UUID) -> DecisionMemoryResponse:
        """The full, composite historical context for one decision - memory,
        learnings, the real experiments it references, the real
        re-evaluations (assessments) it references, and the current
        unresolved uncertainties. Powers `GET /decisions/{id}/memory`.

        Returns an empty-but-valid response (memory=None, empty lists)
        rather than raising if no memory has been created yet - a
        decision with no experiment result and no prior read of this
        endpoint legitimately has nothing to report yet, which is not an
        error condition.
        """
        memory = self._get_memory(decision_id)
        if memory is None:
            return DecisionMemoryResponse(
                memory=None, learnings=[], experiments=[], assessments=[],
                unresolved_uncertainties=[],
            )

        learnings = self._memory.list_learnings_for_decision(decision_id)

        experiment_ids = set(memory.experiment_ids)
        experiments = [
            e for e in self._decisions.list_experiments(decision_id) if str(e.id) in experiment_ids
        ]
        assessments = self._decisions.list_reevaluations(decision_id)

        return DecisionMemoryResponse(
            memory=memory,
            learnings=learnings,
            experiments=experiments,
            assessments=assessments,
            unresolved_uncertainties=memory.unresolved_uncertainties,
        )

    def get_unresolved_uncertainties(self, decision_id: UUID) -> list[str]:
        """The decision's current list of what remains untested/unresolved.

        Read directly off the stored `DecisionMemory.unresolved_uncertainties`
        - never recomputed by re-inspecting every threshold/assumption
        here, since that recomputation already happens once, correctly,
        in `get_or_create_preliminary_memory`/`update_memory_from_reevaluation`.
        """
        memory = self._get_memory(decision_id)
        return memory.unresolved_uncertainties if memory is not None else []

    def _get_memory(self, decision_id: UUID) -> DecisionMemory | None:
        records = self._memory.list_memory_for_decision(decision_id)
        return records[0] if records else None


def _merge_unresolved(previous: list[str], new_unresolved_ids: list[str]) -> list[str]:
    """Combine a memory's existing unresolved-uncertainty entries with newly
    created ones, without duplicating an id already present.

    `previous` may contain either plain descriptive strings (from a
    preliminary memory, before any learning existed) or learning ids
    (from an earlier update) - both are preserved verbatim; only exact
    duplicates of a `new_unresolved_ids` entry are skipped.
    """
    combined = list(previous)
    for entry in new_unresolved_ids:
        if entry not in combined:
            combined.append(entry)
    return combined
