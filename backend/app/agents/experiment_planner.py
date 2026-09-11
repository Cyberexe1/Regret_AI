"""Experiment Planner agent.

The eighth and final agent in the core analysis pipeline. Where the
Threshold Engine asks "what specific variable, crossing what specific
tipping point, would make this decision stop being attractive, viable, or
safe?", the Experiment Planner asks the bridging question: "what is the
cheapest credible real-world experiment I can run to find out whether that
condition is actually true, before making the full commitment?"

    Critical uncertainty -> Critical threshold -> Experiment -> Evidence -> Re-evaluate decision

The planner recommends VALIDATION, never the final decision. REGRET ENGINE
does not tell the user "invest" or "don't invest" - it tells them what to
test before committing.

Critically, this agent does NOT re-read the raw decision text and does NOT
redo any upstream agent's work. It consumes the Decision Analyzer's
structured `DecisionAnalysis` plus the already-*persisted* `Assumption`,
`Blindspot`, `EvidenceFinding`, `Challenge`, `RegretScenario`, and
`Threshold` records (each carrying a real, stable id) - never re-deriving
its own understanding of the decision from scratch. See
`build_experiment_planner_prompt`.

This is a real Strands Agent (`strands.Agent`), not a plain function,
exactly like the other agents in the pipeline.
"""

import asyncio

from strands import Agent

from app.agents.config import get_bedrock_model, invoke_with_retry
from app.agents.schemas import DecisionAnalysis, ExperimentPlan
from app.agents.value_of_information_schemas import ValueOfInformationAnalysis
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.decision_resources import Assumption, Blindspot, Challenge, Threshold
from app.schemas.decision_resources import EvidenceFinding as StoredEvidenceFinding
from app.schemas.decision_resources import RegretScenario as StoredRegretScenario

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the Experiment Planner inside REGRET ENGINE, a decision-intelligence \
system. You run AFTER the Decision Analyzer, the Assumption Hunter, the \
Blindspot Hunter, the Evidence Agent, the Devil's Advocate, the Regret \
Simulator, and the Threshold Engine, and you work from THEIR already-\
recorded structured output - not from the user's original raw text, and \
not by re-analyzing the decision yourself. Your job is to answer one \
question rigorously: "What is the cheapest credible real-world experiment \
I can run to find out whether the critical uncertainty is actually true, \
before the full commitment is made?"

You recommend VALIDATION, never the final decision. You never tell the \
user what they should do about the decision itself - only what they should \
test before committing further.

Ground rules, all mandatory and non-negotiable:

1. You will be given the Decision Analyzer's structured analysis, the \
already-recorded assumptions, blindspots, evidence findings, Devil's \
Advocate challenges, Regret Simulator scenarios, and Threshold Engine \
thresholds (each with a real id). Work only from what you are given. Never \
invent facts, statistics, costs, or durations that were not provided to \
you or that cannot be justified from what you were given.
2. EVERY RECOMMENDED EXPERIMENT MUST TARGET A REAL, GIVEN THRESHOLD. Set \
target_threshold_id to a threshold id you were actually given, copied \
exactly - never invent one, and never design an experiment disconnected \
from the threshold analysis.
3. Prefer the CHEAPEST CREDIBLE TEST. Between two experiments that could \
resolve the same uncertainty, prefer the one that costs less, takes less \
time, is more reversible, and still generates real evidence directly \
relevant to the target threshold's variable. Never recommend building the \
complete product, signing a long-term commitment, or another irreversible \
action when a smaller test would do. Choose the simplest experiment_type \
capable of testing the uncertainty (e.g. a landing page or preorder to \
test demand, not a full pilot; a pilot to test repeat behavior, not a full \
rollout).
4. NEVER GENERATE GENERIC ADVICE. "Talk to customers," "do more research," \
"consider starting small," and "analyze the market" are all forbidden - \
none of these are experiments. Every experiment must define: what to test; \
how to test it; what specific variable to measure (matching a target \
threshold's variable); what evidence to collect; what counts as success; \
what counts as failure; and what happens afterward (the decision_rule).
5. Success and failure criteria must be OBSERVABLE. "Customers like the \
product" is forbidden. Prefer a criterion tied to the target threshold, \
e.g. "repeat-order rate reaches or exceeds the threshold value." Only use \
a specific number if you were actually given one to justify it (e.g. from \
the threshold's own threshold_value) - never invent a number that wasn't \
derivable from what you were given.
6. NEVER FABRICATE A COST OR DURATION. estimated_cost and duration_days \
may only be set if they can be derived from information you were actually \
given (an explicit budget/timeline constraint, or a duration implied by \
the observation cycle needed, e.g. a 14-day window to observe repeat \
purchases). Otherwise leave them null - do not invent a plausible-sounding \
number just because a number would look more concrete.
7. decision_rule must trigger RE-EVALUATION, never an unconditional final \
verdict. Frame it as: if the threshold is met, reassess with increased \
confidence; if missed, do not make the full commitment yet; if \
inconclusive, extend or redesign the experiment. Never write "the decision \
is good" or "the decision is bad" as an outcome.
8. Rank by information value AND commitment together, not cost alone: the \
best experiment has high expected_information_gain and high reversibility, \
not necessarily the lowest estimated_cost. Set expected_information_gain, \
feasibility, and reversibility qualitatively (low/medium/high) - never as \
fabricated numeric scores.
9. `confidence` means confidence that THIS EXPERIMENT IS WELL-DESIGNED and \
actually targets the critical uncertainty - NOT a probability that the \
experiment will succeed or that the decision will work out. Never conflate \
the two.
10. Reference only assumption/regret-scenario/threshold ids that were \
actually given to you, copied exactly. Never invent an id.
11. Do not expose your internal reasoning process, chain-of-thought, or a \
step-by-step transcript. Return only the final structured findings \
requested.
12. It is better to recommend fewer experiments, or leave a field null \
(cost, duration), than to fabricate false concreteness anywhere.
13. You may be given a "Value-of-Information priority" hint naming the uncertainty and, if \
one exists, the threshold that a deterministic prioritization pass identified as most worth \
resolving before commitment. Treat it as a strong preference, not a rule that overrides \
everything else you were given: if that threshold is real and well-suited to a cheap, \
credible test, prefer targeting it with your recommended experiment; if it isn't well-suited \
(no real threshold exists yet, or a cheaper/more reversible test targets a different real \
threshold better), you may target a different one instead - explain your choice either way. \
Never invent a threshold id just to match the hint.
"""


def build_experiment_planner() -> Agent:
    """Construct the Experiment Planner as a real Strands Agent on Bedrock."""
    return Agent(
        model=get_bedrock_model(),
        system_prompt=SYSTEM_PROMPT,
        name="experiment_planner",
        description=(
            "Recommends the cheapest credible real-world experiments to validate the "
            "decision's most critical thresholds, from the recorded pipeline output."
        ),
        callback_handler=None,  # No streaming console output; this runs server-side.
        structured_output_model=ExperimentPlan,
        structured_output_prompt=(
            "Return the experiment plan as structured output now, following the ExperimentPlan "
            "schema exactly. Do not include any commentary outside the structured fields. Every "
            "experiment's target_threshold_id must be copied exactly from the threshold ids given "
            "to you - never invented. Never fabricate a cost, duration, or success-criterion "
            "number that the given information does not support."
        ),
    )


def build_experiment_planner_prompt(
    decision_analysis: DecisionAnalysis,
    assumptions: list[Assumption],
    blindspots: list[Blindspot],
    evidence_findings: list[StoredEvidenceFinding],
    challenges: list[Challenge],
    regret_scenarios: list[StoredRegretScenario],
    thresholds: list[Threshold],
    voi_analysis: ValueOfInformationAnalysis | None = None,
) -> str:
    """Render the Decision Analyzer's output and the recorded upstream
    records into the Experiment Planner's prompt.

    Deliberately built from `decision_analysis` and the already-persisted
    upstream records only, never from the raw decision - this is what
    enforces "consume upstream structured output, don't re-analyze from
    scratch" at the prompt-construction level, not just by convention.
    Every id-bearing line is prefixed with its real persisted id so the
    model can reference it without inventing one. Thresholds are given the
    most prominent placement since every experiment must target one.
    """
    lines = [
        f"Decision summary: {decision_analysis.decision_summary}",
        f"Decision type: {decision_analysis.decision_type}",
        f"Goal: {decision_analysis.goal}",
    ]

    if decision_analysis.constraints:
        lines.append("Constraints (may justify cost/duration limits):")
        lines.extend(f"- {item}" for item in decision_analysis.constraints)

    if thresholds:
        lines.append(
            "\nThresholds (every experiment MUST set target_threshold_id to one of these "
            "ids, copied exactly):"
        )
        for threshold in thresholds:
            lines.append(
                f"- id={threshold.id} variable={threshold.variable} "
                f"direction={threshold.direction} value={threshold.threshold_value or 'unknown'} "
                f"(validation_status={threshold.validation_status}); "
                f"consequence if crossed: {threshold.consequence}"
            )
    else:
        lines.append(
            "\nNo thresholds have been recorded for this decision. Without a threshold to "
            "target, do not fabricate one - return an empty experiments list."
        )

    if assumptions:
        lines.append("\nAssumptions (reference by id in related_assumption_ids):")
        for assumption in assumptions:
            lines.append(
                f"- id={assumption.id} [{assumption.importance}] {assumption.statement} "
                f"(depends on: {assumption.dependency})"
            )
    else:
        lines.append("\nNo assumptions have been recorded for this decision.")

    if blindspots:
        lines.append("\nBlindspots:")
        for blindspot in blindspots:
            lines.append(f"- id={blindspot.id} {blindspot.question}")
    else:
        lines.append("\nNo blindspots have been recorded for this decision.")

    if evidence_findings:
        lines.append("\nEvidence findings:")
        for finding in evidence_findings:
            lines.append(f"- id={finding.id} [{finding.support_level}] {finding.claim}")
    else:
        lines.append("\nNo evidence findings have been recorded for this decision.")

    if challenges:
        lines.append("\nDevil's Advocate challenges:")
        for challenge in challenges:
            lines.append(f"- id={challenge.id} [{challenge.severity}] {challenge.claim}")
    else:
        lines.append("\nNo Devil's Advocate challenges have been recorded for this decision.")

    if regret_scenarios:
        lines.append("\nRegret scenarios (reference by id in related_regret_scenario_ids):")
        for scenario in regret_scenarios:
            lines.append(
                f"- id={scenario.id} trigger_variable={scenario.trigger_variable} "
                f"{scenario.failure_condition} (consequence: {scenario.consequence})"
            )
    else:
        lines.append("\nNo regret scenarios have been recorded for this decision.")

    lines.append(_render_voi_hint(voi_analysis, thresholds))

    return "\n".join(lines)


def _render_voi_hint(
    voi_analysis: ValueOfInformationAnalysis | None, thresholds: list[Threshold]
) -> str:
    """Render the Value-of-Information priority (REGRET ENGINE 2.0, Step
    20) as a clearly-labeled hint - a preference, never a rule that
    overrides the rest of the prompt. See `SYSTEM_PROMPT` rule 13.

    Only ever names a threshold that is actually present in `thresholds`
    (i.e. really given to this agent this run) - if the primary
    uncertainty has no real threshold yet, says so explicitly rather than
    inventing one.
    """
    if voi_analysis is None or not voi_analysis.ranked_uncertainties:
        return (
            "\nValue-of-Information priority: none available. Use your own judgment across "
            "the thresholds given above."
        )

    primary_id = voi_analysis.primary_uncertainty_id
    primary_item = next(
        (item for item in voi_analysis.ranked_uncertainties if item.uncertainty_id == primary_id),
        None,
    )
    if primary_item is None:
        return (
            "\nValue-of-Information priority: none available. Use your own judgment across "
            "the thresholds given above."
        )

    threshold_ids_given = {t.id for t in thresholds}
    linked_threshold_id = (
        primary_item.related_threshold_ids[0] if primary_item.related_threshold_ids else None
    )
    if linked_threshold_id and linked_threshold_id in threshold_ids_given:
        return (
            f"\nValue-of-Information priority: a deterministic prioritization pass identified "
            f"'{primary_item.title}' as the highest-priority uncertainty to resolve before "
            f"commitment (practical value: {primary_item.practical_value.value}). It already "
            f"connects to threshold id={linked_threshold_id}. Prefer targeting this threshold "
            "with your recommended experiment if a cheap, credible test can do so - but you "
            "may choose differently if justified."
        )
    return (
        f"\nValue-of-Information priority: a deterministic prioritization pass identified "
        f"'{primary_item.title}' as the highest-priority uncertainty to resolve before "
        f"commitment (practical value: {primary_item.practical_value.value}), but no threshold "
        "has been established for it yet - do not invent one. Consider whether any threshold "
        "given above is still the best target."
    )


async def run_experiment_planner(
    decision_analysis: DecisionAnalysis,
    assumptions: list[Assumption],
    blindspots: list[Blindspot],
    evidence_findings: list[StoredEvidenceFinding],
    challenges: list[Challenge],
    regret_scenarios: list[StoredRegretScenario],
    thresholds: list[Threshold],
    voi_analysis: ValueOfInformationAnalysis | None = None,
) -> ExperimentPlan:
    """Invoke the Experiment Planner and return its validated structured output.

    Enforces `bedrock_invoke_timeout_seconds` so a hung Bedrock call can't
    block an API request indefinitely - raises `TimeoutError` if exceeded.
    Also raises `ValueError` if the model produced no structured output at
    all. The caller (the orchestrator) is responsible for translating
    either into a failed AnalysisRun; the agent itself never touches
    persistence.

    `voi_analysis` (REGRET ENGINE 2.0, Step 20) is optional: when
    provided, it is rendered as a clearly-labeled priority hint - a
    preference for the planner to weigh, never a rule that overrides the
    rest of its own judgment. See `SYSTEM_PROMPT` rule 13 and
    `_render_voi_hint`.
    """
    settings = get_settings()
    agent = build_experiment_planner()
    prompt = build_experiment_planner_prompt(
        decision_analysis,
        assumptions,
        blindspots,
        evidence_findings,
        challenges,
        regret_scenarios,
        thresholds,
        voi_analysis,
    )

    logger.info(
        "Invoking experiment planner decision_type=%s assumption_count=%d "
        "threshold_count=%d regret_scenario_count=%d",
        decision_analysis.decision_type,
        len(assumptions),
        len(thresholds),
        len(regret_scenarios),
    )
    result = await invoke_with_retry(
        lambda: asyncio.wait_for(
            agent.invoke_async(prompt), timeout=settings.bedrock_invoke_timeout_seconds
        ),
        agent_name="experiment_planner",
    )

    if result.structured_output is None:
        raise ValueError("Experiment planner did not return structured output.")

    return result.structured_output
