"""Shared analysis context passed between agents in the pipeline.

This is a plain, in-memory data holder built fresh by the orchestrator for
one analysis run - it is never persisted directly (structured results are
persisted individually through repositories) and never serialized back to
a client. It exists so later agents (assumption hunter, blindspot hunter,
evidence agent, devil's advocate, regret simulator, threshold engine,
experiment planner - none implemented yet) can read what earlier agents in
the same run produced without every agent re-deriving it from scratch.

Only the Decision Analyzer's slice of this is populated in this step.
"""

from dataclasses import dataclass, field
from typing import Any

from app.agents.schemas import DecisionAnalysis
from app.schemas.decision import DecisionResponse
from app.schemas.decision_resources import Evidence


@dataclass
class AnalysisContext:
    """Everything one orchestrator run gathers and produces for a decision.

    Fields beyond `decision`, `evidence`, and `agent_results` are placeholders
    for agents that don't exist yet - the shape is fixed now so those agents
    can be added later without changing this class's public surface, but
    nothing in this step writes to them.
    """

    decision: DecisionResponse
    evidence: list[Evidence] = field(default_factory=list)

    # Not populated by any agent implemented in this step. Reserved for
    # Assumption Hunter, Blindspot Hunter, Regret Simulator, Threshold
    # Engine, and Experiment Planner respectively.
    assumptions: list[Any] = field(default_factory=list)
    blindspots: list[Any] = field(default_factory=list)
    scenarios: list[Any] = field(default_factory=list)
    thresholds: list[Any] = field(default_factory=list)
    experiments: list[Any] = field(default_factory=list)

    # Structured output from each agent that has run this pass, keyed by a
    # short agent id (e.g. "decision_analyzer"). Downstream agents read from
    # here rather than re-deriving another agent's findings.
    agent_results: dict[str, Any] = field(default_factory=dict)

    @property
    def decision_analysis(self) -> DecisionAnalysis | None:
        """Convenience accessor for the Decision Analyzer's result, if present."""
        result = self.agent_results.get("decision_analyzer")
        return result if isinstance(result, DecisionAnalysis) else None
