"""Data model for the Adaptive Decision Interview (REGRET ENGINE 2.0,
Step 27).

Every field here is either a plain user-visible string/list of strings
(no hidden reasoning, no chain-of-thought - see the package docstring)
or a small, closed enum. `InterviewAgentTurnOutput` is the ONLY schema
ever passed as a Strands `structured_output_model` - it has exactly two
things in it: extracted fields, and one natural-language question. There
is nowhere in this file for a "reasoning"/"thoughts"/"analysis" field to
even exist.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class InterviewStatus(StrEnum):
    """Lifecycle of one interview - spec section 2's exact status list."""

    NOT_STARTED = "not_started"
    ACTIVE = "active"
    AWAITING_ANSWER = "awaiting_answer"
    READY = "ready"
    COMPLETED = "completed"
    USER_STOPPED = "user_stopped"
    BLOCKED = "blocked"
    FAILED = "failed"


class TurnRole(StrEnum):
    USER = "user"
    REGRET = "regret"


class QuestionType(StrEnum):
    """What TOPIC a question/answer is about - spec section 3's exact
    list, doubling as the deterministic priority-selector's topic
    vocabulary (see `question_selector.py`)."""

    CLARIFICATION = "clarification"
    GOAL = "goal"
    CONSTRAINT = "constraint"
    BELIEF = "belief"
    UNCERTAINTY = "uncertainty"
    ALTERNATIVE = "alternative"
    COMMITMENT = "commitment"
    EVIDENCE = "evidence"
    STAKEHOLDER = "stakeholder"
    PRIORITY = "priority"
    VALIDATION = "validation"
    READINESS = "readiness"


class ReadinessLevel(StrEnum):
    """Deterministic, structured-completeness readiness band - NEVER a
    fabricated confidence score (spec section 12). See
    `state.py::compute_readiness`."""

    EARLY = "early"
    ENOUGH = "enough"
    READY = "ready"


class ExtractedFields(BaseModel):
    """Structured information pulled from ONE user answer (spec section
    4) - never chain-of-thought, only the concrete facts the answer
    actually contained. Every list is additive when merged into
    `DecisionInterviewState` (see `state.py::merge_extracted_fields`) -
    nothing here ever overwrites previously-known information, it only
    adds to it.
    """

    desired_outcome: str | None = Field(
        default=None, max_length=500, description="What the user said would make this successful."
    )
    constraints: list[str] = Field(default_factory=list, max_length=10)
    beliefs: list[str] = Field(default_factory=list, max_length=10)
    uncertainties: list[str] = Field(default_factory=list, max_length=10)
    alternatives: list[str] = Field(default_factory=list, max_length=10)
    commitments: list[str] = Field(default_factory=list, max_length=10)
    stakeholders: list[str] = Field(default_factory=list, max_length=10)
    important_variables: list[str] = Field(default_factory=list, max_length=10)
    evidence_mentions: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Evidence the user mentioned having (spec section 31) - "
        "e.g. 'a spreadsheet from 50 customers'. Never assumed to be uploaded.",
    )
    discovered_assumptions: list[str] = Field(default_factory=list, max_length=10)
    discovered_unknowns: list[str] = Field(default_factory=list, max_length=10)

    def is_empty(self) -> bool:
        return not any(
            [
                self.desired_outcome,
                self.constraints,
                self.beliefs,
                self.uncertainties,
                self.alternatives,
                self.commitments,
                self.stakeholders,
                self.important_variables,
                self.evidence_mentions,
                self.discovered_assumptions,
                self.discovered_unknowns,
            ]
        )


class InterviewAgentTurnOutput(BaseModel):
    """The ONLY structured output the Strands Interview Agent ever
    returns (see `prompts.py`/`service.py`). Two narrow jobs, nothing
    else: extract what the answer said, and phrase ONE natural question
    about a topic the deterministic selector already chose to be
    relevant. `selected_topic` MUST be one of the candidates the prompt
    offered - `service.py` validates this and falls back to a
    deterministic canned question (never a crash, never a fabricated
    topic) if the model picks something else or returns malformed
    output (spec section 29).
    """

    extracted: ExtractedFields
    selected_topic: QuestionType
    next_question: str = Field(
        default="",
        max_length=300,
        description="One plain-language question about `selected_topic`. Empty "
        "only when the agent judges no further question is needed.",
    )


class InterviewTurn(BaseModel):
    """One turn of the conversation - spec section 3's exact fields.
    `extracted_fields` is the concise structured result, never a
    chain-of-thought transcript."""

    turn_id: str
    interview_id: str
    turn_number: int = Field(..., ge=0)
    role: TurnRole
    message: str = Field(..., max_length=2000)
    extracted_fields: ExtractedFields | None = None
    question_type: QuestionType | None = None
    created_at: datetime


class DecisionInterviewState(BaseModel):
    """The full, persisted state of one interview - spec section 2's
    exact field list. Every list field is additive/deduplicated as the
    interview proceeds (see `state.py`) - nothing is ever silently
    dropped once discovered.
    """

    interview_id: str
    decision_id: str
    user_id: str
    status: InterviewStatus = InterviewStatus.NOT_STARTED
    turn_number: int = Field(default=0, ge=0)
    max_turns: int = Field(default=7, ge=1)

    decision_text: str = Field(..., max_length=600)
    # Frontend-selected category metadata, if any (Step 25/26's
    # `DecisionCategory[]`) - contextual only, see `question_selector.py`.
    decision_type: str | None = None
    selected_categories: list[str] = Field(default_factory=list)

    desired_outcome: str | None = None
    constraints: list[str] = Field(default_factory=list)
    beliefs: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    commitments: list[str] = Field(default_factory=list)
    stakeholders: list[str] = Field(default_factory=list)
    important_variables: list[str] = Field(default_factory=list)
    evidence_summary: list[str] = Field(default_factory=list)
    discovered_assumptions: list[str] = Field(default_factory=list)
    discovered_unknowns: list[str] = Field(default_factory=list)

    questions_asked: list[QuestionType] = Field(default_factory=list)
    answers: list[str] = Field(default_factory=list)
    current_question: str | None = None

    readiness: ReadinessLevel = ReadinessLevel.EARLY
    readiness_reason: str = ""

    created_at: datetime
    updated_at: datetime


class DecisionSnapshot(BaseModel):
    """The structured output of a completed/skipped interview (spec
    section 16) - the input to the EXISTING Decision Analyzer, never a
    replacement for it. Nothing here is a verdict on the decision -
    see the package docstring's "interview findings vs REGRET analysis
    vs validated evidence" distinction (spec section 34).
    """

    decision: str
    goal: str | None = None
    constraints: list[str] = Field(default_factory=list)
    commitments: list[str] = Field(default_factory=list)
    beliefs: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    important_variables: list[str] = Field(default_factory=list)
    stakeholders: list[str] = Field(default_factory=list)
    decision_criteria: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(
        default_factory=list,
        description="Topics never covered by the interview - the existing "
        "analysis pipeline is expected to discover these on its own (spec section 13).",
    )
    interview_summary: str = Field(
        default="", description="Short, factual summary of what the interview covered."
    )


# --- API request/response schemas (spec section 25) -------------------------------


class StartInterviewResponse(BaseModel):
    interview_id: str
    first_question: str
    state: DecisionInterviewState


class RespondRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    # Optional idempotency guard (spec section 27), mirroring
    # `DecisionUpdate.expected_updated_at`'s own optimistic-concurrency
    # pattern: the `turn_number` the client believes it is currently
    # answering (i.e. `current_state.turn_number` from the last response
    # it actually saw). If provided and it no longer matches the
    # interview's actual current turn number, this request is a stale
    # duplicate/retry - the CURRENT state is returned unchanged rather
    # than processing the message as an answer to a later question it
    # was never shown. Omit to respond unconditionally (e.g. simple
    # clients/tests that don't need this guard).
    expected_turn_number: int | None = Field(default=None, ge=0)


class RespondResponse(BaseModel):
    response: str = Field(
        ..., description="REGRET's next message (the next question, or a closing line)."
    )
    extracted_fields: ExtractedFields
    current_state: DecisionInterviewState
    next_question: str | None = None
    readiness: ReadinessLevel
    turn_number: int
    # Optional quick-response shortcuts for the CURRENT question - never
    # required, purely a UX convenience (spec section 22).
    suggested_chips: list[str] = Field(default_factory=list)
    # False only when the Interview Agent's own extraction/phrasing call
    # failed this turn and a deterministic fallback question was used
    # instead (spec sections 28/29) - the frontend uses this to show
    # "REGRET couldn't continue the interview, but you can continue with
    # the information you've already provided," never a silent swap.
    agent_available: bool = True


class CompleteInterviewResponse(BaseModel):
    snapshot: DecisionSnapshot
    readiness: ReadinessLevel
    missing_information: list[str] = Field(default_factory=list)


class StartInterviewRequest(BaseModel):
    """Optional body for starting an interview - both fields are
    frontend-selected metadata carried over from the existing intake
    flow (Step 25/26), never required."""

    selected_categories: list[str] = Field(default_factory=list, max_length=10)
