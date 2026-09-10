"""Decision Analyzer agent.

The first agent in the (eventually multi-agent) analysis pipeline. Its job
is narrow: understand the decision as stated, before any other agent goes
looking for assumptions, blindspots, or evidence gaps. It does not make the
decision, does not fabricate facts or sources, and never exposes its
reasoning process - only the structured findings defined in
`app.agents.schemas.DecisionAnalysis`.

This is a real Strands Agent (`strands.Agent`), not a plain function - the
agent object is what actually talks to Amazon Bedrock via the model
provider from `app.agents.config`.
"""

import asyncio

from strands import Agent

from app.agents.config import get_bedrock_model, invoke_with_retry
from app.agents.schemas import DecisionAnalysis
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.decision import DecisionResponse
from app.schemas.decision_resources import Evidence

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the Decision Analyzer inside REGRET ENGINE, a decision-intelligence \
system. Your only job is to build a clear, structured understanding of a \
decision BEFORE any other analysis happens. You do not evaluate whether the \
decision is good or bad, and you never recommend what the user should do.

Ground rules, all mandatory:

1. Base your analysis only on the decision context and evidence you are \
given. Never invent facts, statistics, sources, or evidence that were not \
provided to you.
2. Classify every claim you make about the decision as exactly one of: \
FACT (directly stated or verifiable from the given evidence), ASSUMPTION \
(a belief the decision currently relies on but that is not verified), or \
UNKNOWN (something important that the given context does not resolve). \
Never present an assumption as if it were a fact.
3. Be explicit about uncertainty. If evidence is thin or missing for \
something important, say so as an UNKNOWN rather than guessing.
4. Do not expose your internal reasoning process, chain-of-thought, or a \
step-by-step transcript of how you arrived at your answer. Return only the \
final structured findings requested.
5. Be concise. Favor short, concrete statements over generic business \
advice. Ground everything in the specific decision you were given, not in \
generic best practices.
6. You are not the last word. Later specialized steps will dig deeper into \
assumptions, blindspots, and evidence. Your job is only to lay the \
groundwork: what kind of decision this is, what it's trying to achieve, \
what it depends on, and what is still unknown.
"""


def build_decision_analyzer() -> Agent:
    """Construct the Decision Analyzer as a real Strands Agent on Bedrock."""
    return Agent(
        model=get_bedrock_model(),
        system_prompt=SYSTEM_PROMPT,
        name="decision_analyzer",
        description="Understands a decision's type, goal, constraints, and open questions.",
        callback_handler=None,  # No streaming console output; this runs server-side.
        structured_output_model=DecisionAnalysis,
        structured_output_prompt=(
            "Return the decision analysis as structured output now, following the "
            "DecisionAnalysis schema exactly. Do not include any commentary outside "
            "the structured fields."
        ),
    )


def build_analysis_prompt(
    decision: DecisionResponse,
    evidence: list[Evidence],
) -> str:
    """Render the decision + evidence into the prompt the analyzer reads.

    Kept as plain, labeled text rather than raw JSON so the model sees a
    readable brief rather than a data dump - and so it's obvious in the
    prompt itself which fields are present versus omitted (never silently
    dropped).
    """
    lines = [
        f"Title: {decision.title}",
        f"Description: {decision.description}",
    ]
    if decision.desired_outcome:
        lines.append(f"Desired outcome: {decision.desired_outcome}")
    if decision.budget is not None:
        currency = decision.currency or ""
        lines.append(f"Budget: {decision.budget} {currency}".strip())
    if decision.timeline:
        lines.append(f"Timeline: {decision.timeline}")
    if decision.location:
        lines.append(f"Location: {decision.location}")
    if decision.risk_tolerance:
        lines.append(f"Stated risk tolerance: {decision.risk_tolerance}")
    if decision.beliefs:
        lines.append(f"Stated beliefs/assumptions from the user: {decision.beliefs}")

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


async def run_decision_analyzer(
    decision: DecisionResponse,
    evidence: list[Evidence],
) -> DecisionAnalysis:
    """Invoke the Decision Analyzer and return its validated structured output.

    Enforces `bedrock_invoke_timeout_seconds` so a hung Bedrock call can't
    block an API request indefinitely - raises `TimeoutError` if exceeded.
    Also raises `ValueError` if the model produced no structured output at
    all. The caller (the orchestrator) is responsible for translating either
    into a failed AnalysisRun; the agent itself never touches persistence.
    """
    settings = get_settings()
    agent = build_decision_analyzer()
    prompt = build_analysis_prompt(decision, evidence)

    logger.info(
        "Invoking decision analyzer decision_id=%s evidence_count=%d", decision.id, len(evidence)
    )
    result = await invoke_with_retry(
        lambda: asyncio.wait_for(
            agent.invoke_async(prompt), timeout=settings.bedrock_invoke_timeout_seconds
        ),
        agent_name="decision_analyzer",
    )

    if result.structured_output is None:
        raise ValueError("Decision analyzer did not return structured output.")

    return result.structured_output
