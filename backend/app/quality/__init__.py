"""Decision Intelligence Quality & Calibration Engine (REGRET ENGINE 2.0,
Step 24).

Every prior step (18-23) produces structured output - assumptions,
thresholds, experiments, results, re-evaluations, memory, historical
context, adaptive cycles, an evolution timeline, and cross-decision
patterns. None of them ever asks: **how trustworthy is this analysis,
right now?**

CORE PRINCIPLE - this module keeps two questions strictly separate:

    ANALYSIS QUALITY   "Is this conclusion sufficiently grounded in real,
                        traceable evidence?"
    DECISION QUALITY   "Is this a good decision to make?"

This module answers only the first question, and it never answers the
second. A decision can be a genuinely good bet with thin evidence (low
analysis quality); a decision can look bad even though its analysis is
extremely well-grounded (high analysis quality). REGRET ENGINE never
conflates the two, and this module's own output never says "this
decision is good/bad" - only "this conclusion is/isn't well-supported."

No LLM call happens anywhere in this package. Every check in `rules.py`
is deterministic Python over already-persisted, already-structured
records this codebase built in Steps 1-23 - never a re-judgment by a
model, never a fabricated confidence percentage.

Files:

- `schemas.py` - `QualityAssessment`, `QualityCheck`, and their enums.
- `rules.py` - deterministic check functions, one group per quality
  category (evidence/assumption/threshold/experiment/provenance/
  consistency/freshness/historical/completeness).
- `calibration.py` - `CalibrationInsight` and expected-vs-observed
  aggregation over a user's own completed experiments, never claiming
  statistical significance from a small sample.
- `repository.py` - DynamoDB persistence, mirroring the existing
  single-table design exactly (no new database).
- `service.py` - `QualityService`/`CalibrationService`: orchestrates the
  rule functions into one `QualityAssessment`, and aggregates
  calibration observations, respectively.
"""
