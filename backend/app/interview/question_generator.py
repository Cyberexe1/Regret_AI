"""Decision-aware, answer-aware question PHRASING (REGRET ENGINE 2.0,
Step 27A).

This module fixes the "adaptive interview asks the same questions no
matter what decision you type" bug. It does NOT change WHAT topic gets
asked next - `question_selector.select_next_topic` remains the single
place that decides that (spec section 6's deterministic priority order
is untouched). This module only decides HOW to phrase a question about
a topic the selector already chose, given:

  1. the user's actual decision text (`state.decision_text`),
  2. the categories they picked, if any (`state.selected_categories`),
  3. what's already been extracted from previous answers (goal,
     constraints, beliefs, ...), and
  4. the topic itself.

It is used ONLY as the deterministic path - i.e. exactly where
`FALLBACK_QUESTIONS[...]` used to be used verbatim:
  - the interview's very FIRST question (the real Strands agent is
    never called for turn zero - see `service.py::start_interview`),
  - resuming an already-started interview,
  - and any later turn where the Strands Interview Agent is unavailable
    or picked a different topic than the deterministic selector.

Whenever the real Strands Interview Agent DOES run successfully (every
turn after the first, when Bedrock is reachable), its own phrasing -
built from the full decision text and every already-known field via
`prompts.py::build_interview_prompt` - is still used instead, unchanged.
This module exists so the DETERMINISTIC fallback path is just as
decision-aware as the LLM path already was, not to replace the LLM path.

Deliberately a plain, deterministic mock (spec section 9's "Mock Mode
First") - no Bedrock/Strands call, so this can run instantly and be
demoed offline. `generate_question(state, topic)` is the one function
this module exposes; swapping it for a real Strands "phrasing agent"
later only means changing this function's body, never its callers.
"""

from enum import StrEnum

from app.interview.question_selector import FALLBACK_QUESTIONS
from app.interview.schemas import DecisionInterviewState, QuestionType


class InterviewDomain(StrEnum):
    """Mirrors the frontend's `DecisionCategory` values exactly (see
    `frontend/src/types/index.ts`) so a category the user already
    picked in the intake UI maps onto a domain here with zero
    translation. `OTHER` is the deliberate, always-safe catch-all -
    never a forced guess (mirrors `inferDecisionCategory`'s own "null
    is a legitimate result" principle)."""

    CAREER = "career"
    EDUCATION = "education"
    PERSONAL = "personal"
    FINANCIAL = "financial"
    BUSINESS = "business"
    PRODUCT = "product"
    TECHNOLOGY = "technology"
    HIRING = "hiring"
    OPERATIONS = "operations"
    STRATEGY = "strategy"
    RELATIONSHIPS = "relationships"
    HEALTH = "health"
    OTHER = "other"


# Keyword -> domain detection when the user didn't pick a category
# themselves. Order matters: it's the tie-break priority when a
# decision's text matches more than one domain's keywords (e.g. "invest
# ₹5,00,000 to launch a cloud kitchen" matches both BUSINESS's "launch"/
# "kitchen" and FINANCIAL's "invest"/"₹" - BUSINESS is checked first
# because the ACTIVITY being decided is starting a business, not merely
# moving money, and that's the more useful frame for the questions that
# follow). FINANCIAL is deliberately checked near-last since bare money
# mentions ("₹", "lakh", "crore") show up incidentally in almost every
# domain's example text and are the weakest standalone signal of what
# KIND of decision this actually is.
_DOMAIN_KEYWORDS: dict[InterviewDomain, tuple[str, ...]] = {
    InterviewDomain.CAREER: (
        "job",
        "offer",
        "salary",
        "promotion",
        "career",
        "relocat",
        "employer",
        "role at",
        "engineer",
        "manager position",
    ),
    InterviewDomain.EDUCATION: (
        "degree",
        "course",
        "university",
        "college",
        "ms in",
        "masters",
        "phd",
        "certification",
        "bootcamp",
        "study",
        "program",
    ),
    InterviewDomain.HIRING: ("hire", "candidate", "recruit", "headcount"),
    InterviewDomain.TECHNOLOGY: (
        "migrat",
        "database",
        "postgres",
        "dynamodb",
        "architecture",
        "infrastructure",
        "framework",
        "tech stack",
        "server",
        "latency",
        "microservice",
        "api ",
        "cloud provider",
    ),
    InterviewDomain.BUSINESS: (
        "startup",
        "business",
        "launch",
        "venture",
        "kitchen",
        "store",
        "shop",
        "franchise",
        "company",
        "customers",
        "revenue",
    ),
    InterviewDomain.PRODUCT: ("feature", "product", "roadmap", "build our"),
    InterviewDomain.OPERATIONS: (
        "process",
        "workflow",
        "operations",
        "vendor",
        "supplier",
    ),
    InterviewDomain.STRATEGY: (
        "strategy",
        "strategic",
        "market",
        "expand",
        "pivot",
    ),
    InterviewDomain.RELATIONSHIPS: (
        "relationship",
        "partner",
        "marry",
        "marriage",
        "friend",
        "family",
    ),
    InterviewDomain.HEALTH: (
        "health",
        "gym",
        "diet",
        "therapy",
        "surgery",
        "fitness",
    ),
    InterviewDomain.PERSONAL: (
        "buy",
        "purchase",
        "car",
        "suv",
        "house",
        "apartment",
        "move to",
        "moving to",
    ),
    InterviewDomain.FINANCIAL: (
        "invest",
        "stock",
        "mutual fund",
        "loan",
        "mortgage",
        "savings",
        "portfolio",
        "crore",
        "lakh",
        "rupee",
        "₹",
        "$",
    ),
}

# Explicit priority order for tie-breaking - see the comment above.
_DOMAIN_DETECTION_ORDER: tuple[InterviewDomain, ...] = (
    InterviewDomain.CAREER,
    InterviewDomain.EDUCATION,
    InterviewDomain.HIRING,
    InterviewDomain.TECHNOLOGY,
    InterviewDomain.BUSINESS,
    InterviewDomain.PRODUCT,
    InterviewDomain.OPERATIONS,
    InterviewDomain.STRATEGY,
    InterviewDomain.RELATIONSHIPS,
    InterviewDomain.HEALTH,
    InterviewDomain.PERSONAL,
    InterviewDomain.FINANCIAL,
)


def _detect_domain(state: DecisionInterviewState) -> InterviewDomain:
    """The user's own selected category wins outright, if it maps to a
    known domain (spec section 3: "use the selected categories AND the
    actual decision text"). Otherwise, a keyword match against the
    decision's own text. `OTHER` if nothing matches - a real, valid
    outcome, never forced.
    """
    for category in state.selected_categories:
        try:
            return InterviewDomain(category.strip().lower())
        except ValueError:
            continue

    text = state.decision_text.lower()
    for domain in _DOMAIN_DETECTION_ORDER:
        if any(keyword in text for keyword in _DOMAIN_KEYWORDS[domain]):
            return domain
    return InterviewDomain.OTHER


# Per-(topic, domain) phrasing. Every topic's `OTHER` entry is exactly
# the old category-agnostic `FALLBACK_QUESTIONS` text, so a decision
# whose domain can't be determined still gets a perfectly reasonable,
# never-broken question - it just isn't domain-flavored.
_QUESTION_TEMPLATES: dict[QuestionType, dict[InterviewDomain, str]] = {
    QuestionType.GOAL: {
        InterviewDomain.CAREER: "What would make this career decision successful for you?",
        InterviewDomain.EDUCATION: "What outcome would make this degree worth the time and money?",
        InterviewDomain.PERSONAL: (
            "What would make this personal decision feel like the right trade-off?"
        ),
        InterviewDomain.FINANCIAL: "What would make this investment successful for you?",
        InterviewDomain.BUSINESS: "What result would make this business decision worth pursuing?",
        InterviewDomain.PRODUCT: "What would make this product decision worth shipping?",
        InterviewDomain.TECHNOLOGY: (
            "What must this technology change achieve for you to consider it successful?"
        ),
        InterviewDomain.HIRING: (
            "What would this hire need to deliver for you to call it a success?"
        ),
        InterviewDomain.OPERATIONS: "What would make this operational change worth making?",
        InterviewDomain.STRATEGY: "What outcome would make this strategic move the right call?",
        InterviewDomain.RELATIONSHIPS: (
            "What would make this feel like the right decision for the relationship?"
        ),
        InterviewDomain.HEALTH: "What would make this worth it for your health or wellbeing?",
        InterviewDomain.OTHER: FALLBACK_QUESTIONS[QuestionType.GOAL],
    },
    QuestionType.CONSTRAINT: {
        InterviewDomain.CAREER: (
            "What's the hard constraint here - a decision deadline, notice period, "
            "or something else?"
        ),
        InterviewDomain.EDUCATION: (
            "What's actually limiting this - program start dates, financing, "
            "or a visa/timeline issue?"
        ),
        InterviewDomain.PERSONAL: (
            "What could realistically limit this decision - budget, timeline, or something else?"
        ),
        InterviewDomain.FINANCIAL: (
            "What constraints are you working within - how much capital, what time "
            "horizon, how much risk you can absorb?"
        ),
        InterviewDomain.BUSINESS: (
            "What's the real constraint here - capital available, time to break even, "
            "or something operational?"
        ),
        InterviewDomain.PRODUCT: (
            "What's constraining this - engineering time, budget, or a launch deadline?"
        ),
        InterviewDomain.TECHNOLOGY: (
            "What are the hard constraints on this - a maintenance window, team bandwidth, "
            "or a compliance deadline?"
        ),
        InterviewDomain.HIRING: (
            "What's the constraint - how fast you need this role filled, or your "
            "compensation budget?"
        ),
        InterviewDomain.OPERATIONS: (
            "What's limiting this change - budget, team capacity, or a compliance requirement?"
        ),
        InterviewDomain.STRATEGY: (
            "What's the real constraint - capital, time, or organizational appetite for change?"
        ),
        InterviewDomain.RELATIONSHIPS: (
            "What's genuinely limiting this - time, distance, or something else?"
        ),
        InterviewDomain.HEALTH: (
            "What's constraining this - cost, time, or a medical consideration?"
        ),
        InterviewDomain.OTHER: FALLBACK_QUESTIONS[QuestionType.CONSTRAINT],
    },
    QuestionType.COMMITMENT: {
        InterviewDomain.CAREER: (
            "What are you actually giving up if you go ahead - your current role, "
            "equity, stability, location?"
        ),
        InterviewDomain.EDUCATION: (
            "What are you committing here - the tuition itself, or also the income "
            "you'd give up while studying?"
        ),
        InterviewDomain.PERSONAL: "What are you putting at stake if you go ahead with this?",
        InterviewDomain.FINANCIAL: (
            "How much are you actually putting at risk, and could you afford to lose it?"
        ),
        InterviewDomain.BUSINESS: (
            "What capital and time are you committing, and what happens if it doesn't work out?"
        ),
        InterviewDomain.PRODUCT: (
            "What are you committing to build this - time, budget, or the rest of the "
            "roadmap you'd delay?"
        ),
        InterviewDomain.TECHNOLOGY: (
            "What's the real cost of this - engineering time, and the risk if the "
            "cutover goes wrong?"
        ),
        InterviewDomain.HIRING: (
            "What's the cost if this hire doesn't work out - salary, ramp-up time, "
            "team disruption?"
        ),
        InterviewDomain.OPERATIONS: "What would this change cost you if it doesn't go as planned?",
        InterviewDomain.STRATEGY: (
            "What resources are you committing, and what's the cost if this bet doesn't pay off?"
        ),
        InterviewDomain.RELATIONSHIPS: "What are you willing to give up or change for this?",
        InterviewDomain.HEALTH: (
            "What are you committing - money, time, or comfort - and is that sustainable?"
        ),
        InterviewDomain.OTHER: FALLBACK_QUESTIONS[QuestionType.COMMITMENT],
    },
    QuestionType.BELIEF: {
        InterviewDomain.CAREER: (
            "What are you currently assuming about this role that you haven't actually confirmed?"
        ),
        InterviewDomain.EDUCATION: (
            "What are you assuming this degree will get you that you haven't verified yet?"
        ),
        InterviewDomain.PERSONAL: "What are you currently assuming to be true here?",
        InterviewDomain.FINANCIAL: (
            "What return or outcome are you assuming, and how confident are you in that?"
        ),
        InterviewDomain.BUSINESS: (
            "What are you assuming about your customers or market that you haven't tested yet?"
        ),
        InterviewDomain.PRODUCT: (
            "What are you assuming users actually want, that you haven't validated?"
        ),
        InterviewDomain.TECHNOLOGY: (
            "What are you assuming about the new system's performance or reliability "
            "that hasn't been verified?"
        ),
        InterviewDomain.HIRING: (
            "What are you assuming about this candidate that the interviews didn't "
            "actually confirm?"
        ),
        InterviewDomain.OPERATIONS: (
            "What are you assuming about how this change will land with the team?"
        ),
        InterviewDomain.STRATEGY: (
            "What are you assuming about the market or competitors that you haven't verified?"
        ),
        InterviewDomain.RELATIONSHIPS: (
            "What are you assuming about how the other person feels or will react?"
        ),
        InterviewDomain.HEALTH: (
            "What are you assuming about the outcome that you haven't confirmed with evidence?"
        ),
        InterviewDomain.OTHER: FALLBACK_QUESTIONS[QuestionType.BELIEF],
    },
    QuestionType.UNCERTAINTY: {
        InterviewDomain.CAREER: "What would make you regret accepting this six months from now?",
        InterviewDomain.EDUCATION: (
            "What would make you regret this degree a few years after finishing it?"
        ),
        InterviewDomain.PERSONAL: "What would make you look back and regret this decision?",
        InterviewDomain.FINANCIAL: "What outcome would make you regret making this investment?",
        InterviewDomain.BUSINESS: "What would make you regret launching this, a year in?",
        InterviewDomain.PRODUCT: "What would make you regret shipping this?",
        InterviewDomain.TECHNOLOGY: (
            "What would make you regret this migration once it's live in production?"
        ),
        InterviewDomain.HIRING: "What would make you regret this hire six months in?",
        InterviewDomain.OPERATIONS: "What would make you regret making this operational change?",
        InterviewDomain.STRATEGY: (
            "What would make you regret this strategic move a year from now?"
        ),
        InterviewDomain.RELATIONSHIPS: "What would make you regret this decision later?",
        InterviewDomain.HEALTH: "What would make you regret this choice down the line?",
        InterviewDomain.OTHER: FALLBACK_QUESTIONS[QuestionType.UNCERTAINTY],
    },
    QuestionType.ALTERNATIVE: {
        InterviewDomain.CAREER: (
            "What's the realistic alternative - staying in your current role, or "
            "negotiating something different?"
        ),
        InterviewDomain.EDUCATION: (
            "What's the alternative to this - a cheaper program, self-study, or not "
            "pursuing it at all?"
        ),
        InterviewDomain.PERSONAL: "What else could you do instead?",
        InterviewDomain.FINANCIAL: "What else could you do with this money instead?",
        InterviewDomain.BUSINESS: (
            "What's the alternative - a smaller pilot, a different model, or not "
            "launching at all?"
        ),
        InterviewDomain.PRODUCT: (
            "What's the alternative - a smaller version of this, or not building it at all?"
        ),
        InterviewDomain.TECHNOLOGY: (
            "What's the alternative to this migration - staying on the current system, "
            "or a smaller incremental change?"
        ),
        InterviewDomain.HIRING: (
            "What's the alternative - a different candidate, a contractor, or leaving "
            "the role open longer?"
        ),
        InterviewDomain.OPERATIONS: (
            "What's the alternative to this change - keeping the current process, or "
            "a smaller adjustment?"
        ),
        InterviewDomain.STRATEGY: "What's the alternative strategic path here?",
        InterviewDomain.RELATIONSHIPS: (
            "What's the alternative here - waiting, or a different approach?"
        ),
        InterviewDomain.HEALTH: (
            "What's the alternative - a different option, timing, or doing nothing for now?"
        ),
        InterviewDomain.OTHER: FALLBACK_QUESTIONS[QuestionType.ALTERNATIVE],
    },
    QuestionType.PRIORITY: {
        InterviewDomain.CAREER: (
            "Between career growth, compensation, and stability, what matters most "
            "to you right now?"
        ),
        InterviewDomain.EDUCATION: (
            "Between the career outcome and the total cost, what matters most to you here?"
        ),
        InterviewDomain.PERSONAL: "What matters most to you in this decision right now?",
        InterviewDomain.FINANCIAL: (
            "Between expected return and downside risk, what matters more to you here?"
        ),
        InterviewDomain.BUSINESS: (
            "Between growth speed and financial safety, what matters most right now?"
        ),
        InterviewDomain.PRODUCT: "What matters most here - user impact, speed, or cost?",
        InterviewDomain.TECHNOLOGY: (
            "Between reliability and speed of migration, what matters most here?"
        ),
        InterviewDomain.HIRING: (
            "What matters most here - capability, cultural fit, or speed of hiring?"
        ),
        InterviewDomain.OPERATIONS: (
            "What matters most - efficiency, risk reduction, or team impact?"
        ),
        InterviewDomain.STRATEGY: (
            "What matters most here - speed, certainty, or long-term position?"
        ),
        InterviewDomain.RELATIONSHIPS: "What matters most to you in this?",
        InterviewDomain.HEALTH: "What matters most here - outcome, cost, or peace of mind?",
        InterviewDomain.OTHER: FALLBACK_QUESTIONS[QuestionType.PRIORITY],
    },
    QuestionType.EVIDENCE: {
        InterviewDomain.CAREER: (
            "What evidence do you have that this will actually deliver the growth "
            "you're expecting?"
        ),
        InterviewDomain.EDUCATION: (
            "What evidence do you have that this program actually leads to the outcomes "
            "you want - placement data, alumni results?"
        ),
        InterviewDomain.PERSONAL: "What evidence do you already have about this?",
        InterviewDomain.FINANCIAL: (
            "What evidence or data do you have backing the return you're expecting?"
        ),
        InterviewDomain.BUSINESS: (
            "What evidence do you have of real customer demand - signups, pre-orders, "
            "conversations?"
        ),
        InterviewDomain.PRODUCT: "What evidence do you have that users actually want this?",
        InterviewDomain.TECHNOLOGY: (
            "What evidence do you have that the new system will actually perform "
            "better at your scale?"
        ),
        InterviewDomain.HIRING: (
            "What evidence do you have from the interviews that this person can "
            "actually do the job?"
        ),
        InterviewDomain.OPERATIONS: (
            "What evidence do you have that this change will improve things?"
        ),
        InterviewDomain.STRATEGY: "What evidence supports this strategic direction?",
        InterviewDomain.RELATIONSHIPS: "What have you seen or heard that supports this?",
        InterviewDomain.HEALTH: (
            "What evidence do you have supporting this - a diagnosis, professional "
            "advice, research?"
        ),
        InterviewDomain.OTHER: FALLBACK_QUESTIONS[QuestionType.EVIDENCE],
    },
}


def _truncate(text: str, max_length: int = 160) -> str:
    cleaned = text.strip().rstrip(".")
    return cleaned if len(cleaned) <= max_length else cleaned[: max_length - 1].rstrip() + "…"


def generate_question(state: DecisionInterviewState, topic: QuestionType) -> str:
    """The one entry point this module exposes (spec section 9: swap-in
    point for a real Strands agent later). Returns a decision-aware,
    category-aware, and - where the topic itself is inherently a
    follow-up (EVIDENCE, UNCERTAINTY, ALTERNATIVE) - answer-aware
    question, deterministically, in constant time, with no model call.

    Falls back to the domain-agnostic `FALLBACK_QUESTIONS[topic]` text
    for any topic this module has no template for (STAKEHOLDER,
    VALIDATION, CLARIFICATION, READINESS - none of which the
    deterministic selector ever chooses by default; see
    `question_selector.py`), so this function can never raise or return
    an empty string.
    """
    domain = _detect_domain(state)

    # Answer-aware follow-ups (spec section 4): once something is
    # already known, later questions reference it directly rather than
    # asking the same generic thing a second time - mirrors the spec's
    # own worked example ("What evidence do you have that this role
    # will actually accelerate your AI career?" after the user already
    # named "AI career growth" as the goal).
    if topic == QuestionType.EVIDENCE and state.desired_outcome:
        goal = _truncate(state.desired_outcome)
        return f'What evidence do you have that this will actually deliver "{goal}"?'
    if topic == QuestionType.UNCERTAINTY and state.desired_outcome:
        goal = _truncate(state.desired_outcome)
        return (
            f'Given that what you\'re going for is "{goal}", '
            "what would make you regret this decision six months from now?"
        )
    if topic == QuestionType.ALTERNATIVE and state.constraints:
        constraint = _truncate(state.constraints[0]).lower()
        return f"Given {constraint}, what's the realistic alternative here?"

    table = _QUESTION_TEMPLATES.get(topic)
    if table is None:
        return FALLBACK_QUESTIONS[topic]
    return table.get(domain) or table.get(InterviewDomain.OTHER) or FALLBACK_QUESTIONS[topic]
