"""Adaptive Experiment Loop (REGRET ENGINE 2.0, Step 21).

Closes the loop Step 20 opened. Value-of-Information (Step 20) ranks
which uncertainty is most worth resolving *once*. This module makes that
ranking a repeatable cycle:

    Decision -> Uncertainties -> Value of Information -> Best Experiment
        -> Real-world Result -> Re-evaluation -> Updated Uncertainties
        -> Value of Information again -> Next Best Experiment -> ...

Nothing here duplicates Step 20's scoring formula
(`app.services.value_of_information_service`) - this module only adds
the deterministic bookkeeping needed to turn one VOI computation into a
sequence: which thresholds have already been conclusively tested (so the
same experiment is never blindly repeated), how many cycles have run,
what the current evidence-supported state of the decision is, and what
happens next. No LLM call is involved anywhere in this package.

Files:

- `schemas.py` - `AdaptiveExperimentState` and its supporting enums.
- `service.py` - `AdaptiveExperimentService`: the cycle logic.
- `repository.py` - DynamoDB persistence, append-only like every other
  history-bearing entity in this codebase (`ReEvaluation`,
  `ValueOfInformationAnalysis`).
"""
