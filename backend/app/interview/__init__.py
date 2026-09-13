"""Adaptive Decision Interview Agent (REGRET ENGINE 2.0, Step 27).

Replaces the long-form "fill in every field yourself" intake with a
short, adaptive Q&A: the user states a decision in their own words, and
this module asks a small number of targeted follow-up questions,
extracting structured context from each answer, until it has enough to
hand off to the EXISTING analysis pipeline.

CORE PRINCIPLE - this module is CONTEXT COLLECTION, never ANALYSIS:

    INTERVIEW    "What is this decision, and what does the user already
                 know/believe/fear about it?"
    ANALYSIS     "What could make it fail? What threshold matters? What
                 should be tested?" - still entirely the job of the
                 EXISTING Decision Analyzer -> Assumption Hunter ->
                 Blindspot Hunter -> Evidence Agent -> Devil's Advocate
                 -> Regret Simulator -> Threshold Engine -> VOI ->
                 Experiment Planner pipeline (see
                 `app.agents.orchestrator.AnalysisOrchestrator`), which
                 this module never bypasses, duplicates, or replaces.

The Interview Agent must NEVER say "your decision is good" or "you
should accept the job" - it only builds a `DecisionSnapshot` of what the
user said, believes, and is uncertain about. Whether the decision could
fail, and what to test, is determined ENTIRELY downstream by the real
analysis pipeline, exactly as before this step existed.

Question SELECTION is deterministic Python (`question_selector.py` -
what's known, what's missing, priority, decision category, whether a
topic was already covered) - the Strands Agent's only two jobs per turn
are (1) extract structured fields from the user's free-text answer and
(2) phrase ONE natural-language question about the topic the
deterministic selector already chose. The agent never picks what to ask
about, and it never exposes chain-of-thought - its structured output
schema (`InterviewAgentTurnOutput`) has no field for reasoning at all,
so there is nothing to accidentally persist even if the model tried.

Readiness (spec section 12/13) is likewise deterministic structured-
completeness checking (`state.py::compute_readiness`) - never a
fabricated confidence score, and never the model's own opinion of
itself.

Files:

- `schemas.py` - `DecisionInterviewState`, `InterviewTurn`,
  `DecisionSnapshot`, and their enums; API request/response schemas.
- `state.py` - readiness computation, known/assumed/unknown summaries,
  deterministic state-merge helpers.
- `question_selector.py` - deterministic next-topic priority scoring +
  stop condition + canned fallback question templates (used only if the
  model's own phrasing fails validation - see spec section 29).
- `prompts.py` - the Interview Agent's system prompt (extraction +
  phrasing only, explicit prompt-injection defense, no bias toward any
  outcome, no chain-of-thought) and per-turn prompt builder.
- `service.py` - `InterviewService`: start/respond/get_state/complete/
  skip, the one place that calls the Strands Agent, and the one place
  that maps a finished `DecisionSnapshot` onto the EXISTING
  `DecisionUpdate` contract (see `app.services.decisions.DecisionService`)
  so the existing `/analyze` pipeline needs zero changes.
- `repository.py` - DynamoDB persistence, reusing the existing
  single-table design (no new database).
"""
