"""Regret Simulator agent.

The sixth agent in the analysis pipeline, and one of the most important in
REGRET ENGINE. Its job is not to predict the future - it is to construct
plausible failure futures and identify what would have to become true for
committing to this decision now to become a regret:

    Decision -> failure condition -> threshold/tipping point -> consequence -> regret

A risk is something that might go wrong. Regret is a future condition where
the decision-maker could look back and conclude that committing now was
the wrong choice. The Regret Simulator prioritizes scenarios that create
meaningful regret, not scenarios that merely sound bad.

Critically, this agent does NOT re-read the raw decision text and does NOT
redo any upstream agent's work. It consumes the Decision Analyzer's
structured `DecisionAnalysis` plus the already-*persisted* `Assumption`,
`Blindspot`, `EvidenceFinding`, and `Challenge` records (each carrying a
real, stable id) - never re-deriving its own understanding of the decision
from scratch. See `build_regret_simulator_prompt`.

The Threshold Engine (not implemented in this step) will later formalize
any provisional thresholds this agent identifies - this agent may name a
tentative tipping point only when the supplied information actually
supports deriving one; otherwise it must say so rather than inventing a
number.

This is a real Strands Agent (`strands.Agent`), not a plain function,
exactly like the other agents in the pipeline.
"""

import asyncio

from strands import Agent

from app.agents.config import get_bedrock_model, invoke_with_retry
from app.agents.schemas import DecisionAnalysis, RegretSimulation
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.decision_resources import Assumption, Blindspot, Challenge
from app.schemas.decision_resources import EvidenceFinding as StoredEvidenceFinding

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the Regret Simulator inside REGRET ENGINE, a decision-intelligence \
system. You run AFTER the Decision Analyzer, the Assumption Hunter, the \
Blindspot Hunter, the Evidence Agent, and the Devil's Advocate, and you work \
from THEIR already-recorded structured output - not from the user's \
original raw text, and not by re-analyzing the decision yourself. Your job \
is NOT to predict the future. Your job is to construct plausible failure \
futures and identify what would have to become true for this decision to \
become a regret.

The core concept you must apply: decision -> failure condition -> \
threshold/tipping point -> consequence -> regret. A risk is something that \
might go wrong. Regret is a future condition where the decision-maker could \
look back and conclude that committing now was the wrong choice - e.g. the \
user commits the full budget before validating a key assumption, and that \
assumption then turns out false. Always prefer framing scenarios as regret \
conditions like that, not as generic risks.

Ground rules, all mandatory and non-negotiable:

1. You will be given the Decision Analyzer's structured analysis, the \
already-recorded assumptions, blindspots, evidence findings, and Devil's \
Advocate challenges (each with a real id). Work only from what you are \
given. Never invent facts, statistics, sources, or evidence that were not \
provided to you.
2. Only create a scenario if it could materially change the decision. Do \
not create scenarios merely for variety or to fill out a list.
3. NEVER FABRICATE A PROBABILITY. You must not produce a numeric \
probability like "68% chance" unless the supplied evidence provides an \
actual quantitative basis for it - which will essentially never be the \
case here. Use only the qualitative probability_band values: low, medium, \
high, or unknown. Prefer "unknown" over a guess dressed up as a number.
4. NEVER FABRICATE A NUMERIC THRESHOLD. `provisional_threshold` may only \
contain a number if that number can actually be derived from the \
information you were given (e.g. an explicit constraint or figure already \
present in the decision analysis). Otherwise, describe the tipping point \
qualitatively (e.g. "once repeat orders fall meaningfully below what was \
assumed") or leave it unset. The dedicated Threshold Engine will formalize \
real thresholds later - you are not that system.
5. Weigh scenarios conceptually by likelihood, impact, AND irreversibility \
together - never compute or state a fake combined numeric score. A \
low-probability but catastrophic and irreversible scenario can still \
deserve the highest priority.
6. For every scenario, name a specific, concrete trigger_variable (not a \
vague theme) and the direction it would have to move in \
(trigger_direction) to reach the failure_condition. State the consequence \
in terms of regret - what the decision-maker would have committed to \
before the failure condition was resolved - not just as an abstract risk \
statement.
7. Reference only assumption/challenge ids that were actually given to \
you, copied exactly. Never invent an id.
8. Keep supported evidence, inference, and open uncertainty distinct in \
`evidence_basis`. Do not present speculation as settled fact.
9. Do not expose your internal reasoning process, chain-of-thought, or a \
step-by-step transcript. Return only the final structured findings \
requested.
10. If the given inputs are sparse or incomplete, do the best honest job \
you can with what exists - use "unknown" bands and qualitative thresholds \
rather than fabricating certainty you don't have. It is acceptable to \
return few scenarios, or none, if nothing given supports a scenario worth \
raising.
"""


def build_regret_simulator() -> Agent:
    """Construct the Regret Simulator as a real Strands Agent on Bedrock."""
    return Agent(
        model=get_bedrock_model(),
        system_prompt=SYSTEM_PROMPT,
        name="regret_simulator",
        description=(
            "Constructs plausible failure futures and identifies what would have to become "
            "true for this decision to become a regret, from the recorded pipeline output."
        ),
        callback_handler=None,  # No streaming console output; this runs server-side.
        structured_output_model=RegretSimulation,
        structured_output_prompt=(
            "Return the regret simulation as structured output now, following the "
            "RegretSimulation schema exactly. Do not include any commentary outside the "
            "structured fields. Each scenario's own `id` only needs to be unique within this "
            "response. Every related_assumption_ids/related_challenge_ids entry must be copied "
            "exactly from the ids given to you - never invented. Never fabricate a numeric "
            "probability or threshold that the given information does not support."
        ),
    )


def build_regret_simulator_prompt(
    decision_analysis: DecisionAnalysis,
    assumptions: list[Assumption],
    blindspots: list[Blindspot],
    evidence_findings: list[StoredEvidenceFinding],
    challenges: list[Challenge],
) -> str:
    """Render the Decision Analyzer's output and the recorded assumptions/
    blindspots/evidence findings/challenges into the Regret Simulator's
    prompt.

    Deliberately built from `decision_analysis` and the already-persisted
    upstream records only, never from the raw decision - this is what
    enforces "consume upstream structured output, don't re-analyze from
    scratch" at the prompt-construction level, not just by convention.
    Every id-bearing line is prefixed with its real persisted id so the
    model can reference it without inventing one.
    """
    lines = [
        f"Decision summary: {decision_analysis.decision_summary}",
        f"Decision type: {decision_analysis.decision_type}",
        f"Goal: {decision_analysis.goal}",
    ]

    if decision_analysis.constraints:
        lines.append("Constraints:")
        lines.extend(f"- {item}" for item in decision_analysis.constraints)

    if assumptions:
        lines.append("\nAssumptions (reference by id in related_assumption_ids):")
        for assumption in assumptions:
            lines.append(
                f"- id={assumption.id} [{assumption.importance}] {assumption.statement} "
                f"(depends on: {assumption.dependency}; if false: {assumption.failure_consequence})"
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
        lines.append(
            "\nDevil's Advocate challenges (reference by id in related_challenge_ids):"
        )
        for challenge in challenges:
            lines.append(
                f"- id={challenge.id} [{challenge.severity}] {challenge.claim}: "
                f"{challenge.attack} (failure mechanism: {challenge.failure_mechanism})"
            )
    else:
        lines.append(
            "\nNo Devil's Advocate challenges have been recorded for this decision. Build "
            "scenarios from the assumptions and blindspots above instead, or return an empty "
            "scenario list if nothing given supports a concrete failure future."
        )

    return "\n".join(lines)


async def run_regret_simulator(
    decision_analysis: DecisionAnalysis,
    assumptions: list[Assumption],
    blindspots: list[Blindspot],
    evidence_findings: list[StoredEvidenceFinding],
    challenges: list[Challenge],
) -> RegretSimulation:
    """Invoke the Regret Simulator and return its validated structured output.

    Enforces `bedrock_invoke_timeout_seconds` so a hung Bedrock call can't
    block an API request indefinitely - raises `TimeoutError` if exceeded.
    Also raises `ValueError` if the model produced no structured output at
    all. The caller (the orchestrator) is responsible for translating
    either into a failed AnalysisRun; the agent itself never touches
    persistence.
    """
    settings = get_settings()
    agent = build_regret_simulator()
    prompt = build_regret_simulator_prompt(
        decision_analysis, assumptions, blindspots, evidence_findings, challenges
    )

    logger.info(
        "Invoking regret simulator decision_type=%s assumption_count=%d "
        "blindspot_count=%d evidence_finding_count=%d challenge_count=%d",
        decision_analysis.decision_type,
        len(assumptions),
        len(blindspots),
        len(evidence_findings),
        len(challenges),
    )
    result = await invoke_with_retry(
        lambda: asyncio.wait_for(
            agent.invoke_async(prompt), timeout=settings.bedrock_invoke_timeout_seconds
        ),
        agent_name="regret_simulator",
    )

    if result.structured_output is None:
        raise ValueError("Regret simulator did not return structured output.")

    return result.structured_output
