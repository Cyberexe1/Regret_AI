"""Evidence Agent.

The fourth agent in the analysis pipeline. Where the Blindspot Hunter asks
"what important question has the decision-maker failed to ask?", the
Evidence Agent asks a narrower, grounding question: "what does the
evidence we actually have tell us about these assumptions and blindspots?"

This step ONLY uses evidence already uploaded to REGRET ENGINE for this
decision. It does not perform web search or external research itself.

External research now exists as a separate, optional stage
(`app.agents.research_agent`, running immediately before this one) that
produces its own distinct `ExternalEvidence` entities - deliberately never
merged into this agent's `evidence`/`EvidenceFinding` vocabulary. Keeping
the two separate preserves this agent's narrow, easily-audited contract
("only ever looks at what the user actually uploaded") while still letting
external research exist as first-class, separately-retrievable evidence
for the same decision - see `AnalysisContext.external_evidence`.

Critically, this agent does NOT re-read the raw decision text and does NOT
redo the Decision Analyzer's, Assumption Hunter's, or Blindspot Hunter's
work. It consumes the Decision Analyzer's structured output plus the
already-*persisted* `Assumption` and `Blindspot` records (each carrying a
real, stable id) and the evidence records already on file, and maps that
evidence onto specific assumption/blindspot claims - never re-deriving its
own understanding of the decision from scratch. See `build_evidence_prompt`.

This is a real Strands Agent (`strands.Agent`), not a plain function,
exactly like the other three agents in the pipeline.
"""

import asyncio

from strands import Agent

from app.agents.config import get_bedrock_model, invoke_with_retry
from app.agents.schemas import DecisionAnalysis, EvidenceAnalysis
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.decision_resources import Assumption, Blindspot, Evidence

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the Evidence Agent inside REGRET ENGINE, a decision-intelligence \
system. You run AFTER the Decision Analyzer, the Assumption Hunter, and the \
Blindspot Hunter, and you work from THEIR already-recorded output plus the \
evidence already uploaded for this decision - not from the user's original \
raw text, and not by re-analyzing the decision yourself. Your job is to \
answer one question rigorously: "What does the evidence we actually have \
tell us about these assumptions and blindspots?"

Ground rules, all mandatory and non-negotiable:

1. You will be given the Decision Analyzer's structured analysis, the \
already-recorded assumptions (each with a real id), the already-recorded \
blindspots (each with a real id), and the evidence actually submitted for \
this decision (each with a real id). Use ONLY this evidence. Do not \
perform web search, do not draw on outside knowledge as if it were \
evidence, and do not claim external research was done - none was.
2. NEVER FABRICATE EVIDENCE. If the uploaded evidence does not support a \
claim, set support_level to "insufficient" rather than guessing or \
inventing support. Silence in the evidence is not support and not \
contradiction - it is exactly what "insufficient" or "irrelevant" exists \
to represent.
3. Every finding you return MUST reference a real evidence_id from the \
evidence list you were given, copied exactly as given. Never invent an \
evidence_id, never reference an assumption or blindspot id that was not \
given to you, and never fabricate page numbers, URLs, authors, or dates \
for a source.
4. Keep what the evidence literally says separate from what you infer from \
it: `excerpt` is a short, direct quote of only the relevant portion of the \
evidence (never the entire document); `explanation` is your own \
interpretation of what that excerpt means for the claim. Never blend the \
two into one field.
5. Evidence CAN contradict an assumption or blindspot. Do not treat \
submitted evidence as automatic confirmation of anything - read what it \
actually says and set support_level to "contradicts" whenever it \
genuinely conflicts with the claim, "supports" only when it genuinely \
backs the claim, and "irrelevant" when it has nothing to do with the claim \
at all.
6. If an important assumption or blindspot has no evidence addressing it \
at all, say so explicitly rather than omitting it silently - surfacing a \
real gap is as valuable as surfacing a real finding.
7. Do not expose your internal reasoning process, chain-of-thought, or a \
step-by-step transcript. Return only the final structured findings \
requested.
8. You are not evaluating whether the decision is good or bad. Your job is \
only to map the evidence that exists onto the claims that need it, \
honestly and without embellishment.
"""


def build_evidence_agent() -> Agent:
    """Construct the Evidence Agent as a real Strands Agent on Bedrock."""
    return Agent(
        model=get_bedrock_model(),
        system_prompt=SYSTEM_PROMPT,
        name="evidence_agent",
        description=(
            "Maps already-uploaded evidence onto the recorded assumptions and blindspots, "
            "without fabricating sources."
        ),
        callback_handler=None,  # No streaming console output; this runs server-side.
        structured_output_model=EvidenceAnalysis,
        structured_output_prompt=(
            "Return the evidence analysis as structured output now, following the "
            "EvidenceAnalysis schema exactly. Do not include any commentary outside "
            "the structured fields. Every finding's evidence_id must be copied exactly "
            "from one of the evidence items given to you, and every related assumption/"
            "blindspot id must be copied exactly from the ids given to you."
        ),
    )


def build_evidence_prompt(
    decision_analysis: DecisionAnalysis,
    assumptions: list[Assumption],
    blindspots: list[Blindspot],
    evidence: list[Evidence],
) -> str:
    """Render the Decision Analyzer's output, the recorded assumptions and
    blindspots, and evidence into the Evidence Agent's prompt.

    Deliberately built from `decision_analysis` and the already-persisted
    `assumptions`/`blindspots` only, never from the raw decision - this is
    what enforces "consume upstream structured output, don't re-analyze
    from scratch" at the prompt-construction level, not just by
    convention. Every assumption/blindspot/evidence line is prefixed with
    its real persisted id so the model can reference it without inventing
    one.
    """
    lines = [
        f"Decision summary: {decision_analysis.decision_summary}",
        f"Decision type: {decision_analysis.decision_type}",
        f"Goal: {decision_analysis.goal}",
    ]

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
        lines.append("\nBlindspots (reference by id in related_blindspot_ids):")
        for blindspot in blindspots:
            lines.append(
                f"- id={blindspot.id} [{blindspot.category}/{blindspot.importance}] "
                f"{blindspot.question} ({blindspot.why_it_matters})"
            )
    else:
        lines.append("\nNo blindspots have been recorded for this decision.")

    if evidence:
        lines.append("\nEvidence actually submitted for this decision (reference by evidence_id):")
        for item in evidence:
            excerpt = (item.content_reference or "").strip()
            if len(excerpt) > 1500:
                excerpt = excerpt[:1500] + " [excerpt truncated]"
            body = excerpt or "(no extracted text)"
            lines.append(
                f'- evidence_id={item.id} "{item.title}" ({item.source_type.value}): {body}'
            )
    else:
        lines.append(
            "\nNo evidence has been submitted for this decision. There is nothing to map - "
            "do not fabricate any findings."
        )

    return "\n".join(lines)


async def run_evidence_agent(
    decision_analysis: DecisionAnalysis,
    assumptions: list[Assumption],
    blindspots: list[Blindspot],
    evidence: list[Evidence],
) -> EvidenceAnalysis:
    """Invoke the Evidence Agent and return its validated structured output.

    Enforces `bedrock_invoke_timeout_seconds` so a hung Bedrock call can't
    block an API request indefinitely - raises `TimeoutError` if exceeded.
    Also raises `ValueError` if the model produced no structured output at
    all. The caller (the orchestrator) is responsible for translating
    either into a failed AnalysisRun; the agent itself never touches
    persistence.
    """
    settings = get_settings()
    agent = build_evidence_agent()
    prompt = build_evidence_prompt(decision_analysis, assumptions, blindspots, evidence)

    logger.info(
        "Invoking evidence agent decision_type=%s assumption_count=%d "
        "blindspot_count=%d evidence_count=%d",
        decision_analysis.decision_type,
        len(assumptions),
        len(blindspots),
        len(evidence),
    )
    result = await invoke_with_retry(
        lambda: asyncio.wait_for(
            agent.invoke_async(prompt), timeout=settings.bedrock_invoke_timeout_seconds
        ),
        agent_name="evidence_agent",
    )

    if result.structured_output is None:
        raise ValueError("Evidence agent did not return structured output.")

    return result.structured_output
