"""Decision Evolution read-only aggregation (REGRET ENGINE 2.0, Step 22).

This is deliberately NOT a new persisted entity. It holds no
`create_*`/`put_item`/`update_item` calls at all - every method here
reads from a repository that already exists (`DecisionRepository`,
`AnalysisRepository`, `EvidenceRepository`, `MemoryRepository`,
`ValueOfInformationRepository`, `AdaptiveStateRepository`) and returns
their real, already-persisted records unchanged. `DecisionEvolutionService`
is the only thing that turns these into `DecisionEvolutionEvent` rows;
this class's only job is fetching everything one timeline needs without
each caller having to know about six different repositories.
"""

from dataclasses import dataclass, field
from uuid import UUID

from app.adaptive.repository import AdaptiveStateRepository
from app.adaptive.schemas import AdaptiveExperimentState
from app.agents.value_of_information_schemas import ValueOfInformationAnalysis
from app.memory.memory_repository import MemoryRepository
from app.memory.memory_schemas import DecisionMemory, MemoryLearning
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.decision_repository import DecisionRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.value_of_information_repository import ValueOfInformationRepository
from app.schemas.decision_resources import (
    AnalysisRun,
    Assumption,
    Blindspot,
    Evidence,
    Experiment,
    ExperimentResult,
    ReEvaluation,
    RegretScenario,
    Threshold,
)


@dataclass
class DecisionEvolutionRecords:
    """Every canonical record that can contribute an event to one
    decision's evolution timeline - a plain data bag, no logic. Fields
    are lists in roughly chronological creation order per entity type
    (each underlying repository already returns them that way); the
    service is responsible for interleaving them by real timestamp.
    """

    analysis_runs: list[AnalysisRun] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)
    blindspots: list[Blindspot] = field(default_factory=list)
    regret_scenarios: list[RegretScenario] = field(default_factory=list)
    thresholds: list[Threshold] = field(default_factory=list)
    experiments: list[Experiment] = field(default_factory=list)
    experiment_results: list[ExperimentResult] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    reevaluations: list[ReEvaluation] = field(default_factory=list)
    memory: DecisionMemory | None = None
    learnings: list[MemoryLearning] = field(default_factory=list)
    voi_analyses: list[ValueOfInformationAnalysis] = field(default_factory=list)
    adaptive_states: list[AdaptiveExperimentState] = field(default_factory=list)


class DecisionEvolutionRepository:
    """Fetches every canonical record needed to assemble one decision's
    evolution timeline. Holds no cache and no derived state of its own -
    every call re-reads the current, real data, exactly like every other
    read path in this codebase.
    """

    def __init__(
        self,
        decision_repository: DecisionRepository,
        analysis_repository: AnalysisRepository,
        evidence_repository: EvidenceRepository,
        memory_repository: MemoryRepository,
        voi_repository: ValueOfInformationRepository,
        adaptive_repository: AdaptiveStateRepository,
    ) -> None:
        self._decisions = decision_repository
        self._analyses = analysis_repository
        self._evidence = evidence_repository
        self._memory = memory_repository
        self._voi = voi_repository
        self._adaptive = adaptive_repository

    def _latest_memory(self, decision_id: UUID) -> DecisionMemory | None:
        """Exactly one `DecisionMemory` exists per decision (see its own
        schema docstring); `list_memory_for_decision` is the repository's
        only read method for it, so this takes the first (and only)
        record rather than duplicating `MemoryService._get_memory`'s
        private helper - avoids depending on the service layer here."""
        records = self._memory.list_memory_for_decision(decision_id)
        return records[0] if records else None

    def load(self, decision_id: UUID) -> DecisionEvolutionRecords:
        """One bounded fetch per existing entity type - the same set of
        calls `DecisionMemoryResponse`/`useDecisionReportData` already
        make, just gathered in one place. No new DynamoDB access pattern
        is introduced; each call is the exact same `Query` on
        `PK=DECISION#<decision_id>` that entity's own repository already
        exposes.
        """
        return DecisionEvolutionRecords(
            analysis_runs=self._analyses.list_for_decision(decision_id),
            assumptions=self._decisions.list_assumptions(decision_id),
            blindspots=self._decisions.list_blindspots(decision_id),
            regret_scenarios=self._decisions.list_regret_scenarios(decision_id),
            thresholds=self._decisions.list_thresholds(decision_id),
            experiments=self._decisions.list_experiments(decision_id),
            experiment_results=self._decisions.list_experiment_results(decision_id),
            evidence=self._evidence.list_for_decision(decision_id),
            reevaluations=self._decisions.list_reevaluations(decision_id),
            memory=self._latest_memory(decision_id),
            learnings=self._memory.list_learnings_for_decision(decision_id),
            voi_analyses=self._voi.list_for_decision(decision_id),
            adaptive_states=self._adaptive.list_adaptive_states(decision_id),
        )
