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
from app.memory.similarity_schemas import HistoricalContext
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
7. You may be given a "Historical context" section describing similar \
PAST decisions this same user made and what was actually learned from \
them. Treat it strictly as background context, never as truth about the \
CURRENT decision. If you use it at all, follow this priority order, \
highest first: (1) the current decision's own stated text and evidence, \
(2) explicit user constraints, (3) historical learnings that were \
actually VALIDATED by a real experiment result, (4) historical learnings \
that are still PROVISIONAL/unresolved. Never state a historical number as \
if it were a fact about the current decision - phrase it as "a previous \
decision observed X", never "X is true here." If historical context is \
absent or empty, proceed exactly as if it were never mentioned.
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
    historical_context: HistoricalContext | None = None,
) -> str:
    """Render the decision + evidence into the prompt the analyzer reads.

    Kept as plain, labeled text rather than raw JSON so the model sees a
    readable brief rather than a data dump - and so it's obvious in the
    prompt itself which fields are present versus omitted (never silently
    dropped).

    `historical_context` (REGRET ENGINE 2.0) is optional and additive -
    when present, it is rendered as its own, clearly-labeled section
    AFTER the current decision's own text/evidence, with explicit
    "previous decision observed..." framing for every individual insight,
    never phrased as a fact about the current decision. See
    `SYSTEM_PROMPT` rule 7 for the evidence-hierarchy instruction this
    section is designed to support.
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

    lines.append(_render_historical_context(historical_context))

    return "\n".join(lines)


def _render_historical_context(historical_context: HistoricalContext | None) -> str:
    """Render `HistoricalContext` as a clearly-labeled, low-priority
    section - or a plain "none available" line when absent/empty.

    Every insight is phrased as "A previous decision observed/found..."
    (never "X is true") and its historical relevance score is labeled
    explicitly as a similarity measure, never a probability - see this
    module's SYSTEM_PROMPT rule 7 and `app.memory.similarity_schemas`'s
    module docstring for why that distinction matters.
    """
    if historical_context is None or not historical_context.found:
        return (
            "\nHistorical context: none available. This is either the user's first "
            "relevant decision, or no sufficiently similar past decision was found. Do not "
            "reference any past decision."
        )

    lines = [
        "\nHistorical context (background only - from this SAME user's own past decisions; "
        "NEVER treat as fact about the current decision; the current decision's own text and "
        "evidence above always take priority over anything below):",
    ]
    for insight in historical_context.relevant_learnings:
        relevance_pct = round(insight.relevance_score * 100)
        validity = (
            "validated by a real experiment result"
            if insight.learning_type.value in {"threshold_validated", "assumption_validated"}
            else "still provisional/unresolved"
        )
        lines.append(
            f"- A previous decision observed: \"{insight.statement}\" "
            f"(historical relevance score: {relevance_pct}% similar wording/features - not a "
            f"probability; status: {validity})."
        )

    if not historical_context.relevant_learnings:
        lines.append(
            "- Similar past decisions were found, but none have recorded learnings yet."
        )

    return "\n".join(lines)


async def run_decision_analyzer(
    decision: DecisionResponse,
    evidence: list[Evidence],
    historical_context: HistoricalContext | None = None,
) -> DecisionAnalysis:
    """Invoke the Decision Analyzer and return its validated structured output.

    Enforces `bedrock_invoke_timeout_seconds` so a hung Bedrock call can't
    block an API request indefinitely - raises `TimeoutError` if exceeded.
    Also raises `ValueError` if the model produced no structured output at
    all. The caller (the orchestrator) is responsible for translating either
    into a failed AnalysisRun; the agent itself never touches persistence.

    `historical_context` (REGRET ENGINE 2.0) is optional, additive context
    from the same user's own past decisions - see `build_analysis_prompt`.
    """
    settings = get_settings()
    agent = build_decision_analyzer()
    prompt = build_analysis_prompt(decision, evidence, historical_context)

    logger.info(
        "Invoking decision analyzer decision_id=%s evidence_count=%d historical_context_found=%s",
        decision.id,
        len(evidence),
        historical_context.found if historical_context is not None else False,
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
