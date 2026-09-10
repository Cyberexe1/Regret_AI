"""Devil's Advocate agent.

The fifth agent in the analysis pipeline. Where the Evidence Agent asks
"what does the evidence we have tell us?", the Devil's Advocate asks a
sharper, adversarial question: "what is the strongest evidence-based case
that this decision is wrong?"

This is not a generic chatbot that argues for the sake of arguing. Every
challenge it raises must connect a specific claim (an assumption, a
blindspot, or something the evidence itself says) to a concrete failure
mechanism - never generic filler like "competition could be a problem."

Critically, this agent does NOT re-read the raw decision text and does NOT
redo any upstream agent's work. It consumes the Decision Analyzer's
structured `DecisionAnalysis` plus the already-*persisted* `Assumption`,
`Blindspot`, and `EvidenceFinding` records (each carrying a real, stable
id) - never re-deriving its own understanding of the decision from
scratch. See `build_devils_advocate_prompt`.

This is a real Strands Agent (`strands.Agent`), not a plain function,
exactly like the other agents in the pipeline.
"""

import asyncio

from strands import Agent

from app.agents.config import get_bedrock_model
from app.agents.schemas import DecisionAnalysis, DevilAdvocateAnalysis
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.decision_resources import Assumption, Blindspot
from app.schemas.decision_resources import EvidenceFinding as StoredEvidenceFinding

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the Devil's Advocate inside REGRET ENGINE, a decision-intelligence \
system. You run AFTER the Decision Analyzer, the Assumption Hunter, the \
Blindspot Hunter, and the Evidence Agent, and you work from THEIR already-\
recorded structured output - not from the user's original raw text, and not \
by re-analyzing the decision yourself. Your job is to answer one question \
rigorously: "What is the strongest evidence-based case that this decision \
is wrong?"

Ground rules, all mandatory and non-negotiable:

1. You will be given the Decision Analyzer's structured analysis, the \
already-recorded assumptions (each with a real id), blindspots (each with \
a real id), and evidence findings (each with a real id) from the earlier \
stages. Work only from what you are given. Never invent facts, statistics, \
sources, studies, market data, or customer behavior data that were not \
provided to you, and never claim you performed outside research - you have \
not.
2. Do NOT produce generic criticism. "Competition could be a problem," \
"costs may increase," and "customers may not like the product" are all \
useless and forbidden. Every challenge must connect a SPECIFIC claim to a \
SPECIFIC failure mechanism, e.g. "The decision depends on reaching 25% \
repeat orders, but the supplied evidence only establishes initial demand. \
If repeat ordering stays below that level, the projected unit economics no \
longer hold."
3. Actively look for all of the following, grounded only in what you were \
given: which critical assumption, if false, would break the decision; \
which piece of evidence is being trusted more than it actually supports; \
which available evidence conflicts with the decision; what important fact \
is still unknown; what external dependency could break the decision; where \
the decision is relying on an unusually favorable outcome (optimism bias); \
whether the decision assumes an outcome that the given evidence suggests is \
uncommon (a base-rate concern - only raise this if the evidence you were \
given actually supports the claim, never from outside statistical \
knowledge); what happens if the assumed timeline is wrong; what happens \
after the obvious first-order outcome (second-order effects); and any \
plausible concrete scenario that causes the decision to fail.
4. For every challenge, keep supported claim, inference, and open \
uncertainty distinct in `evidence_basis` - never present speculation as if \
it were settled fact. Set `confidence` honestly: a well-evidenced challenge \
should read as more confident than a plausible-but-ungrounded one.
5. Reference only assumption/blindspot/evidence-finding ids that were \
actually given to you, copied exactly. Never invent an id, and never \
fabricate a citation, URL, study, or statistic to back up a challenge.
6. Do not expose your internal reasoning process, chain-of-thought, or a \
step-by-step transcript. Return only the final structured findings \
requested.
7. You are not the last word - a later step (the Regret Simulator) will \
turn your strongest challenges into concrete failure scenarios. Your job \
is only to build the sharpest honest case against the decision, using \
nothing but what you were actually given.
"""


def build_devils_advocate() -> Agent:
    """Construct the Devil's Advocate as a real Strands Agent on Bedrock."""
    return Agent(
        model=get_bedrock_model(),
        system_prompt=SYSTEM_PROMPT,
        name="devils_advocate",
        description=(
            "Builds the strongest evidence-based case that the decision could be wrong, from "
            "the recorded assumptions, blindspots, and evidence findings."
        ),
        callback_handler=None,  # No streaming console output; this runs server-side.
        structured_output_model=DevilAdvocateAnalysis,
        structured_output_prompt=(
            "Return the Devil's Advocate analysis as structured output now, following the "
            "DevilAdvocateAnalysis schema exactly. Do not include any commentary outside the "
            "structured fields. Every related id must be copied exactly from the assumption/"
            "blindspot/evidence-finding ids given to you - never invented."
        ),
    )


def build_devils_advocate_prompt(
    decision_analysis: DecisionAnalysis,
    assumptions: list[Assumption],
    blindspots: list[Blindspot],
    evidence_findings: list[StoredEvidenceFinding],
) -> str:
    """Render the Decision Analyzer's output and the recorded assumptions/
    blindspots/evidence findings into the Devil's Advocate's prompt.

    Deliberately built from `decision_analysis` and the already-persisted
    `assumptions`/`blindspots`/`evidence_findings` only, never from the raw
    decision and never from raw evidence documents - this is what enforces
    "consume upstream structured output, don't re-analyze from scratch" at
    the prompt-construction level, not just by convention. Every id-bearing
    line is prefixed with its real persisted id so the model can reference
    it without inventing one.
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
        lines.append("\nBlindspots (reference by id in related_blindspot_ids):")
        for blindspot in blindspots:
            lines.append(
                f"- id={blindspot.id} [{blindspot.category}/{blindspot.importance}] "
                f"{blindspot.question} ({blindspot.why_it_matters})"
            )
    else:
        lines.append("\nNo blindspots have been recorded for this decision.")

    if evidence_findings:
        lines.append("\nEvidence findings (reference by id in related_evidence_finding_ids):")
        for finding in evidence_findings:
            lines.append(
                f"- id={finding.id} [{finding.support_level}/{finding.credibility}] "
                f"{finding.claim}: {finding.explanation}"
            )
    else:
        lines.append(
            "\nNo evidence findings have been recorded for this decision. Do not fabricate "
            "any evidence-based challenge - rely on assumptions and blindspots instead, or "
            "note the absence of evidence as part of the challenge itself."
        )

    return "\n".join(lines)


async def run_devils_advocate(
    decision_analysis: DecisionAnalysis,
    assumptions: list[Assumption],
    blindspots: list[Blindspot],
    evidence_findings: list[StoredEvidenceFinding],
) -> DevilAdvocateAnalysis:
    """Invoke the Devil's Advocate and return its validated structured output.

    Enforces `bedrock_invoke_timeout_seconds` so a hung Bedrock call can't
    block an API request indefinitely - raises `TimeoutError` if exceeded.
    Also raises `ValueError` if the model produced no structured output at
    all. The caller (the orchestrator) is responsible for translating
    either into a failed AnalysisRun; the agent itself never touches
    persistence.
    """
    settings = get_settings()
    agent = build_devils_advocate()
    prompt = build_devils_advocate_prompt(
        decision_analysis, assumptions, blindspots, evidence_findings
    )

    logger.info(
        "Invoking devil's advocate decision_type=%s assumption_count=%d "
        "blindspot_count=%d evidence_finding_count=%d",
        decision_analysis.decision_type,
        len(assumptions),
        len(blindspots),
        len(evidence_findings),
    )
    result = await asyncio.wait_for(
        agent.invoke_async(prompt), timeout=settings.bedrock_invoke_timeout_seconds
    )

    if result.structured_output is None:
        raise ValueError("Devil's advocate did not return structured output.")

    return result.structured_output
