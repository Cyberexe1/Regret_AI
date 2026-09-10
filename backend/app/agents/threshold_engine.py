"""Threshold Engine agent.

The seventh agent in the analysis pipeline. Where the Regret Simulator asks
"what future would make this decision a regret?", the Threshold Engine asks
a narrower, actionable question: "what specific variable, crossing what
specific tipping point, would make that regret concrete?"

    Regret Scenario -> Failure Condition -> Trigger Variable -> Threshold -> Consequence

A risk says "costs might increase." A threshold says "if monthly operating
cost rises above ₹1.8 lakh, the projected margin becomes unacceptable." The
second is actionable - it is the entire point of this agent.

Critically, this agent does NOT re-read the raw decision text and does NOT
redo any upstream agent's work. It consumes the Decision Analyzer's
structured `DecisionAnalysis` plus the already-*persisted* `Assumption`,
`Blindspot`, `EvidenceFinding`, `Challenge`, and `RegretScenario` records
(each carrying a real, stable id) - never re-deriving its own understanding
of the decision from scratch. See `build_threshold_engine_prompt`.

Arithmetic is deliberately kept out of the model's hands. The model's job
is to decide WHICH variable matters and WHICH named formula (if any) from
`app.agents.threshold_calculations` applies, and to state the numeric
inputs it believes it has evidence for; `run_threshold_engine` then
independently, deterministically recomputes that formula in plain Python
and only accepts the result if it can verify it end to end - if the model
names an unrecognized formula, omits a required input, or the calculation
is mathematically invalid (division by zero, a missing input, a malformed
value), the threshold is downgraded to a qualitative/unknown one rather
than trusting the model's own arithmetic or fabricating a number.

This is a real Strands Agent (`strands.Agent`), not a plain function,
exactly like the other agents in the pipeline.
"""

import asyncio

from strands import Agent

from app.agents.config import get_bedrock_model
from app.agents.schemas import DecisionAnalysis, ThresholdAnalysis, ThresholdDerivation
from app.agents.threshold_calculations import CALCULATIONS, evaluate
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.decision_resources import Assumption, Blindspot, Challenge
from app.schemas.decision_resources import EvidenceFinding as StoredEvidenceFinding
from app.schemas.decision_resources import RegretScenario as StoredRegretScenario

logger = get_logger(__name__)

_RECOGNIZED_FORMULAS = ", ".join(sorted(CALCULATIONS))

SYSTEM_PROMPT = f"""You are the Threshold Engine inside REGRET ENGINE, a decision-intelligence \
system. You run AFTER the Decision Analyzer, the Assumption Hunter, the \
Blindspot Hunter, the Evidence Agent, the Devil's Advocate, and the Regret \
Simulator, and you work from THEIR already-recorded structured output - not \
from the user's original raw text, and not by re-analyzing the decision \
yourself. Your job is to answer one question rigorously: "What specific \
variable could cross what specific tipping point and make this decision \
stop being attractive, viable, or safe?"

The core concept you must apply: regret scenario -> failure condition -> \
trigger variable -> threshold -> consequence. A risk says "costs might \
increase." A threshold says "if monthly operating cost rises above ₹1.8 \
lakh, the projected margin becomes unacceptable." Always aim for the second.

Ground rules, all mandatory and non-negotiable:

1. You will be given the Decision Analyzer's structured analysis, the \
already-recorded assumptions, blindspots, evidence findings, Devil's \
Advocate challenges, and Regret Simulator scenarios (each with a real id). \
Work only from what you are given. Never invent facts, statistics, or \
evidence that were not provided to you.
2. THE MOST IMPORTANT RULE: NEVER INVENT A THRESHOLD NUMBER. Do not \
fabricate a value like "retention threshold = 37%" because it sounds \
plausible or impressive. Every numeric threshold_value must have a \
defensible basis - either an explicit constraint the decision owner \
actually stated, or a deterministic calculation from numbers actually \
present in what you were given.
3. Use the strongest available source, in this priority order: (1) an \
explicit user-provided constraint (e.g. "I cannot spend more than ₹5 lakh") \
- derivation=derived_from_user_input; (2) a mathematical derivation from \
supplied numbers, using ONLY a recognized formula name and inputs you \
actually found in what you were given - derivation=calculated_from_evidence; \
(3) a provisional threshold the Regret Simulator already surfaced, \
validated where possible - derivation=derived_from_existing_analysis; (4) a \
qualitative condition when no reliable number can be derived - \
derivation=qualitative; (5) unknown, when even a qualitative condition \
cannot be meaningfully established - derivation=unknown. Never skip \
straight to a number without working through this priority order.
4. If you use derivation=calculated_from_evidence, you must set \
calculation_formula to EXACTLY one of these recognized formula names - \
never a formula name you invent, and never free-form arithmetic text: \
{_RECOGNIZED_FORMULAS}. Populate calculation_inputs with only the specific \
numeric values you actually found in the given decision/evidence, using \
the exact parameter names each formula requires. You are NOT the one who \
performs the arithmetic - a deterministic calculator recomputes and \
verifies your formula/inputs independently. If you cannot name a \
recognized formula with inputs you actually have evidence for, do not \
force derivation=calculated_from_evidence - fall back to a qualitative \
threshold instead.
5. Threshold types are not limited to numbers. Use NUMERIC when a single \
value applies; RANGE when a safe band applies (set lower_bound/upper_bound); \
QUALITATIVE when only a describable condition applies (e.g. "at least two \
enterprise customers must commit before hiring"); BINARY for a yes/no \
gating condition (e.g. "if regulatory approval is not obtained, do not \
proceed"); TIME_BASED for a deadline-style condition (e.g. "if the pilot \
does not reach the required milestone within 30 days, reassess"). Do not \
force a qualitative condition into a fake number.
6. Every threshold must answer four questions as completely as the given \
information allows: what variable; which direction is dangerous; where the \
tipping point is (or explicitly unknown); what happens if crossed \
(consequence). If one cannot be established, mark that specific field \
unknown rather than guessing.
7. `confidence` means confidence THAT THIS THRESHOLD IS MEANINGFUL - i.e. \
that it is well-derived and actually relevant to the decision. It is NOT a \
probability that the decision will fail or that the threshold will be \
crossed. Never conflate the two, and never present confidence as if it were \
a probability of failure.
8. Set validation_status honestly: "validated" only for a threshold backed \
directly by an explicit user constraint or a verified deterministic \
calculation; "provisional" for a useful inferred tipping point that still \
needs real-world validation; "unknown" when there truly isn't enough to \
establish a meaningful threshold. Do not default to "validated" just \
because a number is present.
9. Reference only assumption/regret-scenario ids that were actually given \
to you, copied exactly. Never invent an id.
10. Rank importance conceptually by impact, irreversibility, how many \
assumptions/scenarios a threshold touches, decision sensitivity, and how \
poorly validated it currently is - never by an arbitrary or fabricated \
numeric score. Choose `primary_threshold_id` as whichever threshold most \
materially could change the decision if crossed; leave it null only if \
nothing clearly dominates.
11. Do not expose your internal reasoning process, chain-of-thought, or a \
step-by-step transcript. `calculation_provenance`, if set, must be one \
concise sentence describing the derivation (e.g. "Derived from monthly \
fixed cost and contribution per customer supplied by the user."), never a \
step-by-step transcript of your reasoning.
12. It is better to return fewer thresholds, or a threshold with \
validation_status=unknown, than to fabricate false precision anywhere.
"""


def build_threshold_engine() -> Agent:
    """Construct the Threshold Engine as a real Strands Agent on Bedrock."""
    return Agent(
        model=get_bedrock_model(),
        system_prompt=SYSTEM_PROMPT,
        name="threshold_engine",
        description=(
            "Identifies the specific tipping points at which this decision stops being "
            "attractive, viable, or safe, from the recorded pipeline output."
        ),
        callback_handler=None,  # No streaming console output; this runs server-side.
        structured_output_model=ThresholdAnalysis,
        structured_output_prompt=(
            "Return the threshold analysis as structured output now, following the "
            "ThresholdAnalysis schema exactly. Do not include any commentary outside the "
            "structured fields. Never invent a threshold_value or calculation_formula - use "
            "only recognized formula names and numeric inputs you actually found in what you "
            "were given, and mark unknown fields explicitly rather than guessing."
        ),
    )


def build_threshold_engine_prompt(
    decision_analysis: DecisionAnalysis,
    assumptions: list[Assumption],
    blindspots: list[Blindspot],
    evidence_findings: list[StoredEvidenceFinding],
    challenges: list[Challenge],
    regret_scenarios: list[StoredRegretScenario],
) -> str:
    """Render the Decision Analyzer's output and the recorded upstream
    records into the Threshold Engine's prompt.

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
        lines.append("Constraints (may be explicit user-provided thresholds):")
        lines.extend(f"- {item}" for item in decision_analysis.constraints)

    if decision_analysis.key_variables:
        lines.append("Key variables the outcome depends on:")
        lines.extend(f"- {item}" for item in decision_analysis.key_variables)

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
        lines.append("\nEvidence findings (may contain numeric inputs for calculations):")
        for finding in evidence_findings:
            lines.append(f"- id={finding.id} [{finding.support_level}] {finding.claim}")
    else:
        lines.append("\nNo evidence findings have been recorded for this decision.")

    if challenges:
        lines.append("\nDevil's Advocate challenges:")
        for challenge in challenges:
            lines.append(
                f"- id={challenge.id} [{challenge.severity}] {challenge.claim}: "
                f"{challenge.failure_mechanism}"
            )
    else:
        lines.append("\nNo Devil's Advocate challenges have been recorded for this decision.")

    if regret_scenarios:
        lines.append(
            "\nRegret scenarios (reference by id in related_regret_scenario_ids; formalize "
            "their provisional_threshold where you can, or explain why you cannot):"
        )
        for scenario in regret_scenarios:
            lines.append(
                f"- id={scenario.id} [{scenario.trigger_direction}] "
                f"trigger_variable={scenario.trigger_variable} {scenario.failure_condition} "
                f"(provisional threshold: {scenario.provisional_threshold or 'none stated'}; "
                f"consequence: {scenario.consequence})"
            )
    else:
        lines.append(
            "\nNo regret scenarios have been recorded for this decision. Build thresholds "
            "from the assumptions and blindspots above instead, or return an empty threshold "
            "list if nothing given supports a concrete, defensible tipping point."
        )

    lines.append(
        "\nRecognized calculation_formula names and their required numeric inputs, for "
        "derivation=calculated_from_evidence (do not use any other formula name):"
    )
    for name, spec in sorted(CALCULATIONS.items()):
        lines.append(f"- {name}({', '.join(spec.required_inputs)})")

    return "\n".join(lines)


def _verify_calculations(analysis: ThresholdAnalysis) -> ThresholdAnalysis:
    """Independently recompute every calculated threshold's arithmetic.

    For each threshold claiming `derivation=calculated_from_evidence`, this
    recomputes `calculation_formula(**calculation_inputs)` deterministically
    in Python (see `app.agents.threshold_calculations.evaluate`) and only
    keeps the model's `threshold_value` if it matches. If the formula name
    is unrecognized, a required input is missing, or the calculation fails
    (division by zero, non-finite/negative result), the threshold is
    downgraded in place to an unverifiable one - `threshold_value` and the
    calculation fields are cleared, `derivation` becomes `unknown`, and
    `validation_status` becomes `unknown` - rather than persisting an
    unverified number or a silently-accepted mismatch. This is what keeps
    the model's own arithmetic from ever being trusted outright.
    """
    verified_thresholds = []
    for threshold in analysis.thresholds:
        if threshold.derivation != ThresholdDerivation.CALCULATED_FROM_EVIDENCE:
            verified_thresholds.append(threshold)
            continue

        computed = None
        if threshold.calculation_formula and threshold.calculation_inputs:
            computed = evaluate(threshold.calculation_formula, threshold.calculation_inputs)

        if computed is None:
            logger.warning(
                "Threshold engine calculation could not be verified formula=%s inputs=%s",
                threshold.calculation_formula,
                threshold.calculation_inputs,
            )
            downgraded = threshold.model_copy(
                update={
                    "threshold_value": None,
                    "derivation": ThresholdDerivation.UNKNOWN,
                    "validation_status": "unknown",
                    "calculation_formula": None,
                    "calculation_inputs": None,
                    "calculation_provenance": None,
                }
            )
            verified_thresholds.append(downgraded)
            continue

        # The calculation verified successfully - replace threshold_value
        # with the independently-computed number (formatted plainly) rather
        # than trusting whatever string the model wrote, so the persisted
        # value is always traceable to this exact deterministic result.
        verified_thresholds.append(
            threshold.model_copy(update={"threshold_value": _format_number(computed)})
        )

    return analysis.model_copy(update={"thresholds": verified_thresholds})


def _format_number(value: float) -> str:
    """Render a computed float without a spurious trailing '.0' when it's a whole number."""
    if value == int(value):
        return str(int(value))
    return f"{value:.4g}"


async def run_threshold_engine(
    decision_analysis: DecisionAnalysis,
    assumptions: list[Assumption],
    blindspots: list[Blindspot],
    evidence_findings: list[StoredEvidenceFinding],
    challenges: list[Challenge],
    regret_scenarios: list[StoredRegretScenario],
) -> ThresholdAnalysis:
    """Invoke the Threshold Engine and return its validated, calculation-
    verified structured output.

    Enforces `bedrock_invoke_timeout_seconds` so a hung Bedrock call can't
    block an API request indefinitely - raises `TimeoutError` if exceeded.
    Also raises `ValueError` if the model produced no structured output at
    all. The caller (the orchestrator) is responsible for translating
    either into a failed AnalysisRun; the agent itself never touches
    persistence.
    """
    settings = get_settings()
    agent = build_threshold_engine()
    prompt = build_threshold_engine_prompt(
        decision_analysis, assumptions, blindspots, evidence_findings, challenges, regret_scenarios
    )

    logger.info(
        "Invoking threshold engine decision_type=%s assumption_count=%d "
        "blindspot_count=%d evidence_finding_count=%d challenge_count=%d "
        "regret_scenario_count=%d",
        decision_analysis.decision_type,
        len(assumptions),
        len(blindspots),
        len(evidence_findings),
        len(challenges),
        len(regret_scenarios),
    )
    result = await asyncio.wait_for(
        agent.invoke_async(prompt), timeout=settings.bedrock_invoke_timeout_seconds
    )

    if result.structured_output is None:
        raise ValueError("Threshold engine did not return structured output.")

    return _verify_calculations(result.structured_output)
