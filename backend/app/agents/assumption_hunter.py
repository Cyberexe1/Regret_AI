"""Assumption Hunter agent.

The second agent in the analysis pipeline. Where the Decision Analyzer
builds a first-pass structural understanding of a decision, the Assumption
Hunter asks a narrower question about that understanding: "what must be
true for this to work?" It surfaces assumptions behind the goal,
constraints, success criteria, key variables, and implied approach - each
one classified by source (explicit/implicit), importance, confidence,
evidence status, what it underpins, and what breaks if it's wrong.

Critically, this agent does NOT re-read the raw decision text. It consumes
the Decision Analyzer's structured `DecisionAnalysis` output plus any
evidence - never re-deriving its own understanding of the decision from
scratch. See `build_assumption_prompt`.

This is a real Strands Agent (`strands.Agent`), not a plain function,
exactly like the Decision Analyzer.
"""

import asyncio

from strands import Agent

from app.agents.config import get_bedrock_model, invoke_with_retry
from app.agents.schemas import AssumptionAnalysis, DecisionAnalysis
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.decision_resources import Evidence

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the Assumption Hunter inside REGRET ENGINE, a decision-intelligence \
system. You run AFTER the Decision Analyzer, and you work from ITS structured \
understanding of the decision - not from the user's original raw text. Your \
job is to answer one question rigorously: "What must be true for this \
decision to work?"

Ground rules, all mandatory:

1. You will be given a structured decision analysis (goal, constraints, \
success criteria, key variables, and the analyzer's own initial \
assumptions/unknowns) plus any evidence submitted for this decision. Work \
only from what you are given. Never invent facts, statistics, sources, or \
evidence that were not provided to you, and never claim you performed \
outside research - you have not.
2. Surface assumptions hiding behind the goal, the constraints, the success \
criteria, the key variables, and the approach the decision implies -
not just the ones the Decision Analyzer already listed. Look for what is \
being taken for granted, not only what was stated.
3. For every assumption you report, determine all of the following: what is \
being assumed; whether it was stated explicitly by the decision owner or is \
implicit; how important it is to the decision's success; how confident you \
are (as a 0.0-1.0 probability, not a vague label) that it actually holds; \
whether the evidence you were given supports it, contradicts it, or never \
addresses it; what specific part of the decision it underpins; and what \
would happen to the decision if it turned out to be false.
4. Evidence status is about the evidence you were actually given for THIS \
decision, nothing else. If no evidence addresses an assumption, that is \
"not_addressed" - it is not evidence of falsehood, and it is not something \
you can fill in with outside knowledge.
5. Do not expose your internal reasoning process, chain-of-thought, or a \
step-by-step transcript. Return only the final structured findings \
requested.
6. Be concise and specific to this decision. Do not pad the list with \
generic business-risk platitudes that would apply to any decision.
7. You are not evaluating whether the decision is good or bad, and you are \
not the last word - later specialized steps will dig into blindspots and \
stress-test scenarios. Your job is only to make what this decision quietly \
depends on visible and explicit.
"""


def build_assumption_hunter() -> Agent:
    """Construct the Assumption Hunter as a real Strands Agent on Bedrock."""
    return Agent(
        model=get_bedrock_model(),
        system_prompt=SYSTEM_PROMPT,
        name="assumption_hunter",
        description=(
            "Surfaces the assumptions a decision depends on, from the Decision Analyzer's output."
        ),
        callback_handler=None,  # No streaming console output; this runs server-side.
        structured_output_model=AssumptionAnalysis,
        structured_output_prompt=(
            "Return the assumption analysis as structured output now, following the "
            "AssumptionAnalysis schema exactly. Do not include any commentary outside "
            "the structured fields."
        ),
    )


def build_assumption_prompt(
    decision_analysis: DecisionAnalysis,
    evidence: list[Evidence],
) -> str:
    """Render the Decision Analyzer's output + evidence into the hunter's prompt.

    Deliberately built from `decision_analysis` only, never from the raw
    decision - this is what enforces "consume the Decision Analyzer's
    output, don't re-analyze from scratch" at the prompt-construction
    level, not just by convention.
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

    if decision_analysis.initial_assumptions:
        lines.append(
            "Assumptions the Decision Analyzer already flagged "
            "(do not just repeat these verbatim - dig further):"
        )
        for assumption in decision_analysis.initial_assumptions:
            lines.append(
                f"- [{assumption.classification.value}] {assumption.statement}"
                f" ({assumption.reason})"
            )

    if decision_analysis.unknowns:
        lines.append("Open unknowns the Decision Analyzer could not resolve:")
        lines.extend(f"- {item}" for item in decision_analysis.unknowns)

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


async def run_assumption_hunter(
    decision_analysis: DecisionAnalysis,
    evidence: list[Evidence],
) -> AssumptionAnalysis:
    """Invoke the Assumption Hunter and return its validated structured output.

    Enforces `bedrock_invoke_timeout_seconds` so a hung Bedrock call can't
    block an API request indefinitely - raises `TimeoutError` if exceeded.
    Also raises `ValueError` if the model produced no structured output at
    all. The caller (the orchestrator) is responsible for translating either
    into a failed AnalysisRun; the agent itself never touches persistence.
    """
    settings = get_settings()
    agent = build_assumption_hunter()
    prompt = build_assumption_prompt(decision_analysis, evidence)

    logger.info(
        "Invoking assumption hunter decision_type=%s evidence_count=%d",
        decision_analysis.decision_type,
        len(evidence),
    )
    result = await invoke_with_retry(
        lambda: asyncio.wait_for(
            agent.invoke_async(prompt), timeout=settings.bedrock_invoke_timeout_seconds
        ),
        agent_name="assumption_hunter",
    )

    if result.structured_output is None:
        raise ValueError("Assumption hunter did not return structured output.")

    return result.structured_output
