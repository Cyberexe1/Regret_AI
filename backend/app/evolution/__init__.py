"""Decision Evolution & Causal Timeline (REGRET ENGINE 2.0, Step 22).

Every prior step (18-21) already persists its own timestamped, id-bearing
record: `AnalysisRun`, `Assumption`/`Blindspot`/`Threshold`/
`RegretScenario`, `Experiment`/`ExperimentResult`, `ReEvaluation`,
`MemoryLearning`, `ValueOfInformationAnalysis`, `AdaptiveExperimentState`.
This module does not add a new event-sourcing table that duplicates any
of that. It ASSEMBLES a read-only, derived timeline from those canonical
records - a VIEW, never a second parallel history.

The product question this answers: "What changed my mind? Why did the
system change its assessment? What evidence caused that change?" The
timeline is therefore built as BELIEF -> EVIDENCE -> TEST -> RESULT ->
CHANGE, not a generic activity log of every database write.

Causality rule: an event only states "X happened because of Y" when the
source record itself supports that link (e.g. a `ReEvaluation` that
explicitly references a `ThresholdComparison`). Nothing here infers a
causal relationship data doesn't already establish.

Files:

- `schemas.py` - `DecisionEvolutionEvent`, `DecisionEvolution`, `DecisionDelta`.
- `repository.py` - read-only aggregation across every existing
  repository (`DecisionRepository`, `AnalysisRepository`,
  `EvidenceRepository`, `MemoryRepository`,
  `ValueOfInformationRepository`, `AdaptiveStateRepository`) - no writes,
  no new DynamoDB items.
- `service.py` - `DecisionEvolutionService`: deterministic event
  assembly, ordering, and delta computation. No LLM call anywhere in
  this package.
"""
