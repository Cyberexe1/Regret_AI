"""Blindspot Hunter agent.

The third agent in the analysis pipeline. Where the Assumption Hunter asks
"what must be true for this to work?", the Blindspot Hunter asks a
different question about the same structured material: "what important
question has the decision-maker failed to ask?" It looks for missing
variables, evidence gaps, contradictions between assumptions and evidence,
untested dependencies, overlooked constraints, edge cases, second-order
effects, stakeholder effects, and timing risks - anything that could
materially change the decision if left unanswered.

Critically, this agent does NOT re-read the raw decision text and does NOT
redo the Decision Analyzer's or Assumption Hunter's work. It consumes the
Decision Analyzer's structured `DecisionAnalysis` and the Assumption
Hunter's already-*persisted* `Assumption` records - never re-deriving its
own understanding of the decision from scratch. Persisted assumptions
(rather than the agent's raw `AssumptionFinding` output) are used
deliberately: they carry a real, stable `id` the model can reference in
`related_assumption_ids`, so this agent is never left having to invent one.
See `build_blindspot_prompt`.

This is a real Strands Agent (`strands.Agent`), not a plain function,
exactly like the Decision Analyzer and Assumption Hunter.
"""

import asyncio

from strands import Agent

from app.agents.config import get_bedrock_model
from app.agents.schemas import BlindspotAnalysis, DecisionAnalysis
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.decision_resources import Assumption, Evidence

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the Blindspot Hunter inside REGRET ENGINE, a decision-intelligence \
system. You run AFTER the Decision Analyzer and the Assumption Hunter, and you \
work from THEIR structured output - not from the user's original raw text, \
and not by re-analyzing the decision yourself. Your job is to answer one \
question rigorously: "What important question has the decision-maker \
failed to ask?"

Ground rules, all mandatory:

1. You will be given the Decision Analyzer's structured analysis (goal, \
constraints, success criteria, key variables, unknowns), the already-\
recorded assumptions from the Assumption Hunter (each with a real id), and \
any evidence submitted for this decision. Work only from what you are \
given. Never invent facts, statistics, sources, or evidence that were not \
provided to you, and never claim you performed outside research - you have \
not.
2. Do NOT redo the Decision Analyzer's work and do NOT redo the Assumption \
Hunter's work. Do not produce another general summary of the decision and \
do not just restate assumptions that were already recorded. Your job is to \
find what is MISSING from what they already produced: missing questions, \
missing variables, evidence gaps, contradictions between assumptions and \
evidence, untested dependencies, overlooked constraints, edge cases, \
second-order effects, stakeholder effects, environmental/contextual \
factors, timing-related risks, and dependencies that could invalidate the \
decision.
3. Be concrete and specific to this decision. A blindspot must be a sharp, \
answerable question about THIS decision - e.g. "What happens to unit \
economics if repeat orders fall below 20%?" - never generic filler that \
would apply to any decision, like "consider market conditions."
4. Prioritize blindspots that could materially change the decision if left \
unanswered. Do not pad the list with low-stakes trivia.
5. For every blindspot you report, determine all of the following: the \
question itself; which category it falls into (use "other" if nothing else \
genuinely fits - do not force a category); how important it is; how \
confident you are (0.0-1.0) that this is a real, material gap and not a \
false alarm; whether the evidence you were given already answers it \
(already_supported), partly answers it (partially_addressed), contradicts \
something related to it (contradicted), or never addresses it at all \
(not_addressed); which of the given assumption ids it relates to, if any \
- copy the id exactly as given, never invent one; why it matters to the \
decision; and, if applicable, what specific evidence is missing that would \
resolve it.
6. Evidence status is about the evidence you were actually given for THIS \
decision, nothing else. Do not claim evidence exists when it does not, and \
never fabricate citations or invent external research.
7. Do not expose your internal reasoning process, chain-of-thought, or a \
step-by-step transcript. Return only the final structured findings \
requested.
8. You are not evaluating whether the decision is good or bad, and you are \
not the last word - a later step (the Evidence Agent) will map available \
evidence against your findings. Your job is only to make the unasked \
questions visible and explicit.
"""


def build_blindspot_hunter() -> Agent:
    """Construct the Blindspot Hunter as a real Strands Agent on Bedrock."""
    return Agent(
        model=get_bedrock_model(),
        system_prompt=SYSTEM_PROMPT,
        name="blindspot_hunter",
        description=(
            "Surfaces important questions the decision-maker has not asked, from the "
            "Decision Analyzer's structured output and the recorded assumptions."
        ),
        callback_handler=None,  # No streaming console output; this runs server-side.
        structured_output_model=BlindspotAnalysis,
        structured_output_prompt=(
            "Return the blindspot analysis as structured output now, following the "
            "BlindspotAnalysis schema exactly. Do not include any commentary outside "
            "the structured fields. Every related_assumption_ids entry must be copied "
            "exactly from one of the assumption ids given to you."
        ),
    )


def build_blindspot_prompt(
    decision_analysis: DecisionAnalysis,
    assumptions: list[Assumption],
    evidence: list[Evidence],
) -> str:
    """Render the Decision Analyzer's output, the recorded assumptions, and
    evidence into the hunter's prompt.

    Deliberately built from `decision_analysis` and the already-persisted
    `assumptions` only, never from the raw decision - this is what enforces
    "consume upstream structured output, don't re-analyze from scratch" at
    the prompt-construction level, not just by convention. Each assumption
    line is prefixed with its real persisted id so the model can reference
    it in `related_assumption_ids` without inventing one.
    """
    lines = [
        f"Decision summary: {decision_analysis.decision_summary}",
        f"Decision type: {decision_analysis.decision_type}",
        f"Goal: {decision_analysis.goal}",
    ]

    if decision_analysis.constraints:
        lines.append("Constraints:")
        lines.extend(f"- {item}" for item in decision_analysis.constraints)

    if decision_analysis.success_criteria:
        lines.append("Success criteria:")
        lines.extend(f"- {item}" for item in decision_analysis.success_criteria)

    if decision_analysis.key_variables:
        lines.append("Key variables the outcome depends on:")
        lines.extend(f"- {item}" for item in decision_analysis.key_variables)

    if decision_analysis.unknowns:
        lines.append("Open unknowns the Decision Analyzer could not resolve:")
        lines.extend(f"- {item}" for item in decision_analysis.unknowns)

    if assumptions:
        lines.append(
            "\nAssumptions already recorded by the Assumption Hunter "
            "(reference by id in related_assumption_ids; do not just restate these - "
            "find what is missing from them):"
        )
        for assumption in assumptions:
            source = assumption.source.value if assumption.source else "unknown"
            lines.append(
                f"- id={assumption.id} [{source}/{assumption.importance}/"
                f"{assumption.evidence_status.value}] {assumption.statement} "
                f"(depends on: {assumption.dependency}; if false: {assumption.failure_consequence})"
            )
    else:
        lines.append("\nNo assumptions have been recorded for this decision.")

    if evidence:
        lines.append("\nAvailable evidence:")
        for item in evidence:
            excerpt = (item.content_reference or "").strip()
            if len(excerpt) > 1000:
                excerpt = excerpt[:1000] + " [excerpt truncated]"
            body = excerpt or "(no extracted text)"
            lines.append(f'- "{item.title}" ({item.source_type.value}): {body}')
    else:
        lines.append("\nNo evidence has been submitted for this decision yet.")

    return "\n".join(lines)


async def run_blindspot_hunter(
    decision_analysis: DecisionAnalysis,
    assumptions: list[Assumption],
    evidence: list[Evidence],
) -> BlindspotAnalysis:
    """Invoke the Blindspot Hunter and return its validated structured output.

    Enforces `bedrock_invoke_timeout_seconds` so a hung Bedrock call can't
    block an API request indefinitely - raises `TimeoutError` if exceeded.
    Also raises `ValueError` if the model produced no structured output at
    all. The caller (the orchestrator) is responsible for translating either
    into a failed AnalysisRun; the agent itself never touches persistence.
    """
    settings = get_settings()
    agent = build_blindspot_hunter()
    prompt = build_blindspot_prompt(decision_analysis, assumptions, evidence)

    logger.info(
        "Invoking blindspot hunter decision_type=%s assumption_count=%d evidence_count=%d",
        decision_analysis.decision_type,
        len(assumptions),
        len(evidence),
    )
    result = await asyncio.wait_for(
        agent.invoke_async(prompt), timeout=settings.bedrock_invoke_timeout_seconds
    )

    if result.structured_output is None:
        raise ValueError("Blindspot hunter did not return structured output.")

    return result.structured_output
