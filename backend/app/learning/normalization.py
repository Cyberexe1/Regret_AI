"""Deterministic normalization for Cross-Decision Learning (REGRET ENGINE
2.0, Step 23).

Turns free-text structured fields (a `Threshold.variable`, an
`Assumption.statement`'s topic, a `DecisionAnalysis.decision_type`, an
`Experiment.experiment_type`) into a stable grouping key, so two
decisions' observations can be recognized as "the same recurring thing"
without ever guessing at meaning.

DELIBERATELY NOT semantic/embedding-based (spec section 3's explicit
prohibition: "do NOT build an uncontrolled semantic clustering system").
Normalization here is exact-match-after-cleanup: lowercase, strip
punctuation, collapse whitespace, drop a small stopword list, and sort
the remaining tokens - two strings normalize to the same key only when
they share the same significant words, in any order ("customer
retention" and "retention customer" match; "customer retention" and
"repeat purchase behavior" do NOT, even though a human might consider
them related, because nothing here performs synonym/topic clustering).

This mirrors `app.memory.similarity`'s own tokenization approach exactly
(same stopword philosophy, same "lightweight heuristic, not an NLP
pipeline" scope) so the two modules never disagree about what counts as
"the same variable."
"""

import re

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

# Mirrors `app.memory.similarity._STOPWORDS`'s scope and philosophy - a
# short, generic list, not a full NLP stopword corpus.
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "then",
        "than",
        "so",
        "of",
        "to",
        "in",
        "on",
        "for",
        "with",
        "at",
        "by",
        "from",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "i",
        "we",
        "you",
        "he",
        "she",
        "they",
        "my",
        "our",
        "your",
        "their",
        "not",
        "no",
        "do",
        "does",
        "did",
        "will",
        "would",
        "should",
        "could",
        "can",
        "may",
        "might",
        "must",
        "have",
        "has",
        "had",
        "about",
        "into",
        "over",
        "after",
        "before",
        "there",
        "here",
        "what",
        "which",
        "rate",
        "level",
        "value",
        "amount",
        "number",
    }
)

# Trailing/leading words that carry no distinguishing meaning for a
# variable/topic key - dropped only when they appear as a WHOLE token,
# never a substring, so "rating" is never mistaken for "rate".
_GENERIC_SUFFIX_WORDS = frozenset({"rate", "level", "score", "percentage", "percent"})


def _tokenize(text: str) -> list[str]:
    tokens = _TOKEN_PATTERN.findall(text.lower())
    return [token for token in tokens if token not in _STOPWORDS and len(token) >= 3]


def normalize_variable(variable: str | None) -> str | None:
    """Deterministic grouping key for a threshold/experiment variable
    name or an assumption's topic - `None` for empty/whitespace-only
    input, never a fabricated key for something that wasn't provided.

    Examples (all real, structured-field-derived, never LLM-guessed):
        "Customer retention rate"      -> "customer retention"
        "Repeat customer rate"          -> "customer repeat"
        "Repeat-order rate"              -> "order repeat"

    Note "customer retention rate" and "repeat customer rate" do NOT
    normalize to the same key here - they share only the word
    "customer", not the full token set - which is intentional: this
    function refuses to guess that "retention" and "repeat" mean the
    same thing. Recognizing that relationship requires either an exact
    structured match elsewhere (e.g. both thresholds reference the same
    real `Assumption.id`) or explicit, bounded LLM-assisted normalization
    (spec section 3, not implemented in this step) - never an implicit
    fuzzy-match performed here.
    """
    if not variable or not variable.strip():
        return None
    tokens = {token for token in _tokenize(variable) if token not in _GENERIC_SUFFIX_WORDS}
    if not tokens:
        return None
    return " ".join(sorted(tokens))


def normalize_decision_type(decision_type: str | None) -> str | None:
    """Deterministic grouping key for a `DecisionAnalysis.decision_type`
    free-text field (e.g. "market entry", "Market-Entry Decision")."""
    if not decision_type or not decision_type.strip():
        return None
    tokens = _tokenize(decision_type)
    if not tokens:
        return None
    return " ".join(sorted(tokens))


def normalize_experiment_type(experiment_type: str | None) -> str | None:
    """Deterministic grouping key for an `Experiment.experiment_type`
    free-text field (e.g. "landing_page", "Landing Page Test")."""
    if not experiment_type or not experiment_type.strip():
        return None
    tokens = _tokenize(experiment_type.replace("_", " "))
    if not tokens:
        return None
    return " ".join(sorted(tokens))


def normalize_domain(text: str | None) -> str | None:
    """Deterministic grouping key for a coarse decision domain/topic,
    derived only from real, already-provided text (e.g. a decision's own
    title/description) - never inferred from an external taxonomy."""
    if not text or not text.strip():
        return None
    tokens = _tokenize(text)
    if not tokens:
        return None
    # A domain key is intentionally coarser than a variable key - only
    # the first few significant tokens, so unrelated long descriptions
    # don't produce two decisions with a spuriously identical key merely
    # because they share every rare word somewhere in a long text.
    return " ".join(sorted(tokens[:5]))


def variables_match(a: str | None, b: str | None) -> bool:
    """Whether two raw variable/topic strings normalize to the exact
    same key - the ONLY test this module ever uses to decide "these are
    the same recurring thing." Returns `False` whenever either input
    normalizes to `None` (nothing to compare), never a fallback "assume
    they match" guess."""
    key_a = normalize_variable(a)
    key_b = normalize_variable(b)
    return key_a is not None and key_a == key_b
