"""Deterministic state helpers for the Adaptive Decision Interview
(REGRET ENGINE 2.0, Step 27).

Everything in this file is plain Python over already-extracted
structured fields - no LLM call, no fabricated confidence number. This
is the module that decides "do we know enough yet?" (spec sections 12/13)
and "what does the live decision model currently look like?" (spec
section 9's KNOWN/ASSUMED/UNKNOWN split).
"""

from datetime import UTC, datetime

from app.interview.schemas import (
    DecisionInterviewState,
    ExtractedFields,
    ReadinessLevel,
)

# A short cap per list field so one very talkative answer can't blow up
# the persisted state or the prompt built from it on the next turn -
# mirrors every other "*_max_*" bounding convention in this codebase
# (see `app.core.config.Settings`'s per-step comment blocks).
_MAX_ITEMS_PER_FIELD = 12


def _merge_list(existing: list[str], new_items: list[str]) -> list[str]:
    """Appends only genuinely new items (case-insensitive de-dup),
    preserving the order they were first mentioned, bounded to
    `_MAX_ITEMS_PER_FIELD` - never drops something already known to
    make room for something new (spec section 8: "never ask redundant
    questions" implies never losing an answer already given, either).
    """
    seen = {item.strip().lower() for item in existing}
    merged = list(existing)
    for item in new_items:
        cleaned = item.strip()
        if not cleaned or cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        merged.append(cleaned)
    return merged[:_MAX_ITEMS_PER_FIELD]


def merge_extracted_fields(
    state: DecisionInterviewState, extracted: ExtractedFields
) -> DecisionInterviewState:
    """Folds one turn's `ExtractedFields` into the running
    `DecisionInterviewState` - every list field is additive, and
    `desired_outcome` is only ever set once (the FIRST clear statement
    of it wins; a later answer refining it is captured instead as a
    belief/constraint rather than silently overwriting the original
    goal - keeps the "what we know" panel from flip-flopping turn to
    turn).
    """
    updated = state.model_copy(deep=True)

    if extracted.desired_outcome and not updated.desired_outcome:
        updated.desired_outcome = extracted.desired_outcome.strip()

    updated.constraints = _merge_list(updated.constraints, extracted.constraints)
    updated.beliefs = _merge_list(updated.beliefs, extracted.beliefs)
    updated.uncertainties = _merge_list(updated.uncertainties, extracted.uncertainties)
    updated.alternatives = _merge_list(updated.alternatives, extracted.alternatives)
    updated.commitments = _merge_list(updated.commitments, extracted.commitments)
    updated.stakeholders = _merge_list(updated.stakeholders, extracted.stakeholders)
    updated.important_variables = _merge_list(
        updated.important_variables, extracted.important_variables
    )
    updated.evidence_summary = _merge_list(updated.evidence_summary, extracted.evidence_mentions)
    updated.discovered_assumptions = _merge_list(
        updated.discovered_assumptions, extracted.discovered_assumptions
    )
    updated.discovered_unknowns = _merge_list(
        updated.discovered_unknowns, extracted.discovered_unknowns
    )

    updated.updated_at = datetime.now(UTC)
    return updated


def compute_readiness(state: DecisionInterviewState) -> tuple[ReadinessLevel, str]:
    """Deterministic, structured-completeness readiness (spec sections
    12/13) - counts how many of the 5 substantive criteria are actually
    satisfied. NEVER a fabricated confidence percentage.

    Criteria (spec section 13, "do not require every field" - explicit
    absence counts the same as a positive statement, since both are
    real information):
      1. desired_outcome present, OR at least one belief/uncertainty
         already gives the analyzer something to work with instead.
      2. at least one constraint - OR the user has answered enough
         turns that an explicit "no meaningful constraint" is a
         reasonable read (we never ask the user to literally say "I
         have no constraints"; enough turns without one surfacing is
         itself the signal).
      3. at least one commitment/stake.
      4. at least one belief OR discovered_assumption.
      5. at least one uncertainty OR discovered_unknown.
      6. at least one alternative - OR enough turns have passed that
         "no alternatives volunteered" is treated as the answer.

    `ENOUGH`/`READY` is reached once at least 4 of these 6 hold AND at
    least `_MIN_TURNS_BEFORE_READY` real user turns have happened -
    the turn-count floor exists so a single unusually rich answer can't
    end the interview after one turn (spec section 20's "small number
    of relevant questions" still implies more than one, in general).
    `READY` (spec's strongest state, "I've identified the main
    uncertainties worth testing") additionally requires uncertainty
    AND commitment to both be present - the two criteria most directly
    tied to what the downstream Threshold Engine/Experiment Planner
    actually need.
    """
    turns = state.turn_number

    has_goal_signal = (
        bool(state.desired_outcome) or bool(state.beliefs) or bool(state.uncertainties)
    )
    has_constraint_signal = bool(state.constraints) or turns >= 3
    has_commitment_signal = bool(state.commitments)
    has_belief_signal = bool(state.beliefs) or bool(state.discovered_assumptions)
    has_uncertainty_signal = bool(state.uncertainties) or bool(state.discovered_unknowns)
    has_alternative_signal = bool(state.alternatives) or turns >= 4

    satisfied = sum(
        [
            has_goal_signal,
            has_constraint_signal,
            has_commitment_signal,
            has_belief_signal,
            has_uncertainty_signal,
            has_alternative_signal,
        ]
    )

    _MIN_TURNS_BEFORE_READY = 2

    if turns < _MIN_TURNS_BEFORE_READY or satisfied < 3:
        return (
            ReadinessLevel.EARLY,
            "We're still understanding the decision.",
        )

    if has_uncertainty_signal and has_commitment_signal and satisfied >= 5:
        return (
            ReadinessLevel.READY,
            "I've identified the main uncertainties worth testing.",
        )

    if satisfied >= 4:
        return (
            ReadinessLevel.ENOUGH,
            "I have enough context to stress-test this decision.",
        )

    return (
        ReadinessLevel.EARLY,
        "We're still understanding the decision.",
    )


def missing_information(state: DecisionInterviewState) -> list[str]:
    """Plain list of topics the interview never covered - handed to the
    existing analysis pipeline as an honest signal of what it will need
    to discover on its own (spec section 13/16), never hidden."""
    missing: list[str] = []
    if not state.desired_outcome:
        missing.append("desired outcome")
    if not state.constraints:
        missing.append("constraints")
    if not state.commitments:
        missing.append("what is being committed/at stake")
    if not (state.beliefs or state.discovered_assumptions):
        missing.append("current beliefs/assumptions")
    if not (state.uncertainties or state.discovered_unknowns):
        missing.append("critical uncertainty")
    if not state.alternatives:
        missing.append("alternatives considered")
    if not state.evidence_summary:
        missing.append("evidence already available")
    return missing


def known_assumed_unknown(state: DecisionInterviewState) -> dict[str, list[str]]:
    """The "WHAT WE KNOW / WHAT WE ASSUME / WHAT WE DON'T KNOW" split
    for the live decision-model panel (spec section 9). Explicitly NOT
    the final REGRET analysis - just an early, inspectable summary of
    what the interview itself has gathered so far.
    """
    known: list[str] = []
    if state.desired_outcome:
        known.append(state.desired_outcome)
    known.extend(state.constraints)
    known.extend(state.commitments)

    assumed = list(state.beliefs) + list(state.discovered_assumptions)
    unknown = list(state.uncertainties) + list(state.discovered_unknowns)

    return {"known": known, "assumed": assumed, "unknown": unknown}
