"""Deterministic next-question selection (REGRET ENGINE 2.0, Step 27,
spec sections 5-11).

The Interview Agent (see `service.py`/`prompts.py`) never decides WHAT
topic to ask about - that is entirely this module's job, driven only by:
what is already known, what is still missing, a fixed importance
ordering, and whether a topic has already been asked. This keeps
question selection auditable, reproducible, and free of any LLM
judgment about what matters most - the one part of "intelligence" this
step deliberately keeps deterministic rather than delegating to Bedrock.

The REGRET question ("what would make you regret this decision?") and
the decision-changing question ("what information could change your
mind?") are folded into the UNCERTAINTY topic's own canned fallback text
(spec sections 10/11) - both are phrased as uncertainty-discovery
questions, never as a separate, additional topic, since they serve the
exact same purpose the UNCERTAINTY topic already exists for.
"""

from app.interview.schemas import DecisionInterviewState, QuestionType

# Spec section 6's exact priority order, expressed as an explicit list
# rather than magic numbers scattered through comparisons.
_PRIORITY_ORDER: list[QuestionType] = [
    QuestionType.GOAL,
    QuestionType.CONSTRAINT,
    QuestionType.COMMITMENT,
    QuestionType.BELIEF,
    QuestionType.UNCERTAINTY,
    QuestionType.ALTERNATIVE,
    QuestionType.PRIORITY,
    QuestionType.EVIDENCE,
]

# Deterministic fallback questions - used verbatim only when the model's
# own phrasing fails validation (spec section 29), so the interview can
# never crash or stall on a malformed response. Written to satisfy spec
# section 32's "no AI jargon, asks ONE thing, doesn't push toward a
# decision" quality bar on their own.
FALLBACK_QUESTIONS: dict[QuestionType, str] = {
    QuestionType.GOAL: "What would make this decision successful?",
    QuestionType.CONSTRAINT: "What could realistically limit this decision?",
    QuestionType.COMMITMENT: "What are you putting at stake if you go ahead?",
    QuestionType.BELIEF: "What are you currently assuming to be true here?",
    QuestionType.UNCERTAINTY: "What would make you regret this decision?",
    QuestionType.ALTERNATIVE: "What else could you do instead?",
    QuestionType.PRIORITY: "What matters most to you in this decision right now?",
    QuestionType.EVIDENCE: "What evidence do you already have about this?",
    QuestionType.STAKEHOLDER: "Who else is affected by this decision?",
    QuestionType.VALIDATION: "Does this match what you meant?",
    QuestionType.CLARIFICATION: "Could you say a bit more about that?",
    QuestionType.READINESS: "Is there anything important I haven't asked about yet?",
}


def _topic_is_covered(state: DecisionInterviewState, topic: QuestionType) -> bool:
    """Whether a topic already has real, extracted content - the exact
    mechanism behind spec section 8's "never ask redundant questions."
    A topic that was merely ASKED (see `questions_asked`) but produced
    no extracted content for it is NOT considered covered, so a
    non-answer doesn't permanently block ever revisiting it.
    """
    if topic == QuestionType.GOAL:
        return bool(state.desired_outcome)
    if topic == QuestionType.CONSTRAINT:
        return bool(state.constraints) or state.turn_number >= 3
    if topic == QuestionType.COMMITMENT:
        return bool(state.commitments)
    if topic == QuestionType.BELIEF:
        return bool(state.beliefs) or bool(state.discovered_assumptions)
    if topic == QuestionType.UNCERTAINTY:
        return bool(state.uncertainties) or bool(state.discovered_unknowns)
    if topic == QuestionType.ALTERNATIVE:
        return bool(state.alternatives) or state.turn_number >= 4
    if topic == QuestionType.EVIDENCE:
        return bool(state.evidence_summary)
    if topic == QuestionType.PRIORITY:
        # "Priority" has no dedicated state field of its own - it's
        # considered covered once we already have at least two other
        # substantive signals to weigh against each other (asking
        # "what matters most" before there's anything to compare is
        # not yet a meaningful question).
        signals = [
            state.desired_outcome,
            state.constraints,
            state.commitments,
            state.beliefs,
        ]
        return sum(1 for s in signals if s) < 2
    return False


def select_next_topic(state: DecisionInterviewState) -> QuestionType | None:
    """Returns the single most useful next topic, or `None` if every
    priority topic is already covered (spec section 6: "select only
    what is necessary," never all ten by default - this module never
    even considers STAKEHOLDER/VALIDATION/READINESS/CLARIFICATION as
    default candidates; those exist only for edge-case fallback
    phrasing, never the deterministic main sequence).

    Selection = first topic in `_PRIORITY_ORDER` that:
      - has not already produced real extracted content
        (`_topic_is_covered` is False), AND
      - has not already been asked twice in a row without an answer
        (guards against looping on a topic the user is clearly not
        going to answer that way).
    """
    asked_counts: dict[QuestionType, int] = {}
    for topic in state.questions_asked:
        asked_counts[topic] = asked_counts.get(topic, 0) + 1

    for topic in _PRIORITY_ORDER:
        if _topic_is_covered(state, topic):
            continue
        if asked_counts.get(topic, 0) >= 2:
            continue
        return topic

    return None


# Optional quick-response shortcuts (spec section 22) - purely a UX
# convenience the frontend may render as chips; the user can always
# type a free-text answer instead. Deliberately generic per topic since
# these are shown regardless of decision category - a category-specific
# set would risk becoming just another rigid form (the exact thing this
# step, and Step 26 before it, are meant to avoid).
QUICK_RESPONSE_CHIPS: dict[QuestionType, list[str]] = {
    QuestionType.PRIORITY: [
        "Career growth",
        "Money",
        "Lifestyle",
        "Stability",
        "Flexibility",
        "Something else",
    ],
    QuestionType.ALTERNATIVE: [
        "Do nothing",
        "Wait and see",
        "Choose a different option",
        "No real alternative",
    ],
    QuestionType.COMMITMENT: [
        "Money",
        "Time",
        "Relationships",
        "Reputation",
        "Career",
        "Nothing major",
    ],
    QuestionType.EVIDENCE: ["I have some data", "Only anecdotal", "Nothing yet"],
}


def suggested_chips_for_topic(topic: QuestionType) -> list[str]:
    return QUICK_RESPONSE_CHIPS.get(topic, [])


def should_stop(state: DecisionInterviewState) -> bool:
    """Hard stop conditions independent of readiness - spec section 12's
    "MUST NOT continue indefinitely." Readiness (`state.py::compute_readiness`)
    can end the interview earlier; this only enforces the ceiling.
    """
    if state.turn_number >= state.max_turns:
        return True
    return select_next_topic(state) is None
