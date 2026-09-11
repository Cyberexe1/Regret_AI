"""Cross-Decision Learning Engine (REGRET ENGINE 2.0, Step 23).

Step 19 (`app.memory.historical_context`) answers "which past decisions
are relevant to THIS decision?" Step 23 answers a different question:
"what keeps happening across ALL of my decisions?" - recurring patterns
detected across a user's own completed decisions, never a single
decision's relevance to another.

CORE PRINCIPLE: no generic AI-generated "insight" is ever produced here.
Every `CrossDecisionPattern` is traceable to real, already-persisted
canonical records - `DecisionMemory`, `MemoryLearning`, `ExperimentResult`,
`ReEvaluation`, `Threshold` - via `PatternOccurrence` rows that carry a
real `source_type`/`source_id`. There is no LLM call anywhere in this
package; pattern detection is deterministic Python over structured data
this codebase already computed in Steps 18-22.

USER ISOLATION IS ABSOLUTE: every read/write in this package requires a
`user_id` and every repository query is scoped to it. A pattern is never
built from, or returned to, more than one user's decisions. There is no
global learning, no cross-user aggregation, and no shared statistics
anywhere in this module.

Files:

- `schemas.py` - `CrossDecisionPattern`, `PatternOccurrence`, and their enums.
- `normalization.py` - deterministic (non-LLM) normalization of variable
  names, decision types, and experiment types, so "customer retention"
  and "repeat customer rate" can be recognized as candidates for the
  SAME pattern only when the underlying structured fields actually say
  so (never a semantic/embedding-based guess).
- `pattern_detector.py` - deterministic recurring-pattern detection over
  a user's own `DecisionMemory`/`MemoryLearning`/`ReEvaluation`/
  `Threshold` records.
- `repository.py` - DynamoDB persistence, user-scoped
  (`PK=USER#<user_id>`), idempotent upsert.
- `service.py` - `CrossDecisionLearningService`: orchestrates detection,
  minimum-evidence validation, and provenance-preserving upsert; the
  explicit "why did REGRET learn this?" surface.
"""
