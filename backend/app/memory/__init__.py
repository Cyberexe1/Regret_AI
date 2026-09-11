"""Decision Memory: REGRET ENGINE 2.0's record of what was believed, what
was tested, what actually happened, and what changed as a result.

This package does not replace or duplicate the existing analysis pipeline
(`app.agents`) or re-evaluation service (`app.services.re_evaluation_service`).
It sits one layer above them: `MemoryService` reads the same
already-persisted `DecisionRepository` records (assumptions, thresholds,
regret scenarios, experiments, experiment results, re-evaluations) and
distills a durable summary plus a set of individually provenance-tracked
`MemoryLearning` records - never re-running the agent pipeline, never
duplicating every original record, and never inventing a fact that isn't
already backed by a stored experiment result or re-evaluation.

See `memory_schemas.py` for the data model, `memory_repository.py` for
DynamoDB access (same single-table design as every other repository in
`app.repositories`), and `memory_service.py` for the business logic.
"""
