"""Shared analysis context passed between agents in the pipeline.

This is a plain, in-memory data holder built fresh by the orchestrator for
one analysis run - it is never persisted directly (structured results are
persisted individually through repositories) and never serialized back to
a client. It exists so agents later in the same run can read what earlier
agents produced without every agent re-deriving it from scratch.

Two kinds of "what an earlier agent produced" show up here, for different
purposes:

- `agent_results` holds each agent's raw structured output (a
  `DecisionAnalysis`, `AssumptionAnalysis`, `BlindspotAnalysis`,
  `EvidenceAnalysis`, `DevilAdvocateAnalysis`, `RegretSimulation`,
  `ThresholdAnalysis`, or `ExperimentPlan`), surfaced via the
  `decision_analysis` / `assumption_analysis` / `blindspot_analysis` /
  `evidence_analysis` / `devil_advocate_analysis` / `regret_simulation` /
  `threshold_analysis` / `experiment_plan` properties below. This is what
  gets persisted into `AnalysisRun.result`.
- `assumptions` / `blindspots` / `evidence_findings` / `challenges` /
  `regret_scenarios` / `thresholds` / `experiments` hold the *persisted*
  entities (with real, stable ids assigned by the repository layer) once
  the orchestrator has written them to DynamoDB. Downstream agents that
  need to reference an upstream finding by id (e.g. the Blindspot Hunter
  citing `related_assumption_ids`, or the Experiment Planner citing
  `target_threshold_id`) read from these lists, never from the raw agent
  output, since only the persisted records have ids.
"""

from dataclasses import dataclass, field
from typing import Any

from app.agents.schemas import (
    AssumptionAnalysis,
    BlindspotAnalysis,
    DecisionAnalysis,
    DevilAdvocateAnalysis,
    EvidenceAnalysis,
    ExperimentPlan,
    RegretSimulation,
    ResearchAnalysis,
    ThresholdAnalysis,
)
from app.agents.value_of_information_schemas import ValueOfInformationAnalysis
from app.memory.similarity_schemas import HistoricalContext
from app.schemas.decision import DecisionResponse
from app.schemas.decision_resources import (
    Assumption,
    Blindspot,
    Challenge,
    Evidence,
    Experiment,
    ExternalEvidence,
    Threshold,
)
from app.schemas.decision_resources import EvidenceFinding as StoredEvidenceFinding
from app.schemas.decision_resources import RegretScenario as StoredRegretScenario


@dataclass
class AnalysisContext:
    """Everything one orchestrator run gathers and produces for a decision."""

    decision: DecisionResponse
    evidence: list[Evidence] = field(default_factory=list)

    # REGRET ENGINE 2.0: additive historical context (Decision Similarity +
    # Historical Insight Engine), gathered BEFORE Stage 1 runs - see
    # `AnalysisOrchestrator._run_analysis_pipeline`. `None` only in the
    # narrow window before that gathering step runs; once populated, it is
    # always a valid `HistoricalContext` (possibly `found=False`), never
    # re-computed mid-run. Passed into the Decision Analyzer's prompt as
    # clearly-labeled, lower-priority context - it never overrides current
    # evidence, deterministic calculations, or user constraints; see
    # `app.memory.historical_context`'s module docstring for the full
    # evidence-hierarchy rationale.
    historical_context: HistoricalContext | None = None

    # REGRET ENGINE 2.0, Step 20: which uncertainty is most worth
    # resolving before commitment - deterministic, computed after
    # thresholds are persisted (Stage 7a) and before the Experiment
    # Planner runs (Stage 8), which reads `primary_uncertainty_id`/
    # `primary_threshold_id` as a preference hint. `None` before that
    # stage runs, or if it failed - never blocks/fails the run either
    # way; see `AnalysisOrchestrator._compute_value_of_information`.
    value_of_information: ValueOfInformationAnalysis | None = None

    # Persisted entities, populated by the orchestrator once each stage's
    # findings have been written to DynamoDB - see module docstring.
    assumptions: list[Assumption] = field(default_factory=list)
    blindspots: list[Blindspot] = field(default_factory=list)
    external_evidence: list[ExternalEvidence] = field(
        default_factory=list,
        # Populated by the (optional) Research Agent stage, kept entirely
        # separate from `evidence` (user-uploaded) and `evidence_findings`
        # (the Evidence Agent's analysis of user-uploaded evidence) - see
        # `app.agents.research_agent`'s module docstring for why external
        # research is never merged into either of those.
    )
    evidence_findings: list[StoredEvidenceFinding] = field(default_factory=list)
    challenges: list[Challenge] = field(default_factory=list)
    regret_scenarios: list[StoredRegretScenario] = field(default_factory=list)
    thresholds: list[Threshold] = field(default_factory=list)
    experiments: list[Experiment] = field(default_factory=list)

    # Structured output from each agent that has run this pass, keyed by a
    # short agent id (e.g. "decision_analyzer"). Downstream agents read from
    # here rather than re-deriving another agent's findings.
    agent_results: dict[str, Any] = field(default_factory=dict)

    @property
    def decision_analysis(self) -> DecisionAnalysis | None:
        """Convenience accessor for the Decision Analyzer's result, if present."""
        result = self.agent_results.get("decision_analyzer")
        return result if isinstance(result, DecisionAnalysis) else None

    @property
    def assumption_analysis(self) -> AssumptionAnalysis | None:
        """Convenience accessor for the Assumption Hunter's result, if present."""
        result = self.agent_results.get("assumption_hunter")
        return result if isinstance(result, AssumptionAnalysis) else None

    @property
    def blindspot_analysis(self) -> BlindspotAnalysis | None:
        """Convenience accessor for the Blindspot Hunter's result, if present."""
        result = self.agent_results.get("blindspot_hunter")
        return result if isinstance(result, BlindspotAnalysis) else None

    @property
    def evidence_analysis(self) -> EvidenceAnalysis | None:
        """Convenience accessor for the Evidence Agent's result, if present."""
        result = self.agent_results.get("evidence_agent")
        return result if isinstance(result, EvidenceAnalysis) else None

    @property
    def devil_advocate_analysis(self) -> DevilAdvocateAnalysis | None:
        """Convenience accessor for the Devil's Advocate's result, if present."""
        result = self.agent_results.get("devils_advocate")
        return result if isinstance(result, DevilAdvocateAnalysis) else None

    @property
    def regret_simulation(self) -> RegretSimulation | None:
        """Convenience accessor for the Regret Simulator's result, if present."""
        result = self.agent_results.get("regret_simulator")
        return result if isinstance(result, RegretSimulation) else None

    @property
    def threshold_analysis(self) -> ThresholdAnalysis | None:
        """Convenience accessor for the Threshold Engine's result, if present."""
        result = self.agent_results.get("threshold_engine")
        return result if isinstance(result, ThresholdAnalysis) else None

    @property
    def experiment_plan(self) -> ExperimentPlan | None:
        """Convenience accessor for the Experiment Planner's result, if present."""
        result = self.agent_results.get("experiment_planner")
        return result if isinstance(result, ExperimentPlan) else None

    @property
    def research_analysis(self) -> ResearchAnalysis | None:
        """Convenience accessor for the Research Agent's result, if present.

        `None` both when the Research Agent hasn't run yet AND when
        research was skipped/unavailable for this run - callers that need
        to distinguish those cases should check `agent_statuses` (see
        `app.agents.orchestrator`) rather than this property alone.
        """
        result = self.agent_results.get("research_agent")
        return result if isinstance(result, ResearchAnalysis) else None
