"""Quality data model (REGRET ENGINE 2.0, Step 24).

`QualityAssessment` is the one new persisted entity this step adds - a
snapshot of how well-grounded a decision's CURRENT structured analysis
is, built entirely from deterministic checks (`QualityCheck` rows) over
real, already-persisted records. It is never a re-judgment of whether
the decision itself is wise - see the package docstring's "analysis
quality vs decision quality" principle.

Append-only, exactly like `ReEvaluation`/`ValueOfInformationAnalysis`:
running the quality engine again after new evidence arrives creates a
NEW `QualityAssessment`, never overwrites the previous one, so the full
history of "how much did we trust this analysis, and when" stays
reconstructable.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class QualityBand(StrEnum):
    """A category's (or the overall) grounding level - never a
    fabricated percentage. `INSUFFICIENT` is distinct from `WEAK`: it
    means there wasn't even enough structured data to judge the
    category at all (e.g. no thresholds exist yet), not that what
    exists is weak.
    """

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    INSUFFICIENT = "insufficient"


class QualityCheckStatus(StrEnum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class QualityCheckSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class QualityCheckCategory(StrEnum):
    EVIDENCE = "evidence"
    ASSUMPTION = "assumption"
    THRESHOLD = "threshold"
    EXPERIMENT = "experiment"
    PROVENANCE = "provenance"
    CONSISTENCY = "consistency"
    FRESHNESS = "freshness"
    HISTORICAL = "historical"
    COMPLETENESS = "completeness"


class QualityCheck(BaseModel):
    """One deterministic check's real result - always traceable to a
    specific real record via `related_entity_type`/`related_entity_id`.
    Never a generic, unattributed "something might be wrong" - every
    check names exactly what it inspected.
    """

    check_id: str = Field(
        ...,
        description="Deterministic, derived from (quality_id, category, name, "
        "related_entity_id) - re-running the same check against the same record always "
        "produces the same id.",
    )
    category: QualityCheckCategory
    name: str = Field(
        ...,
        description="A short, stable rule name, e.g. "
        "'critical_assumption_has_evidence' - identifies WHICH deterministic rule ran.",
    )
    status: QualityCheckStatus
    severity: QualityCheckSeverity
    message: str = Field(
        ...,
        description="Plain-language explanation, built only from the real fields the "
        "check inspected - never free-form LLM prose.",
    )
    related_entity_type: str | None = Field(
        default=None,
        description="The canonical record kind this check is about, e.g. "
        "'assumption', 'threshold', 'experiment', 'evidence_finding'.",
    )
    related_entity_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    recommendation: str | None = Field(
        default=None,
        description="A concrete, actionable next step - only present when the "
        "check actually found something worth acting on (warning/failed).",
    )
    created_at: datetime


class QualityAssessment(BaseModel):
    """A full snapshot of how well-grounded a decision's current
    analysis is - assembled entirely from `QualityCheck` rows.

    `overall_quality` is never a separate, independently-judged number -
    it is deterministically derived from the category bands themselves
    (see `app.quality.rules.overall_band_from_categories`), so it can
    never silently disagree with the categories a user can inspect right
    below it.
    """

    quality_id: str = Field(
        ...,
        description="Deterministic, derived from (decision_id, analysis_run_id) when an "
        "analysis run exists, else from (decision_id, generated_at) - re-running the check "
        "with no new evidence and against the same analysis run produces the SAME id.",
    )
    decision_id: str
    analysis_run_id: str | None = None
    user_id: str
    overall_quality: QualityBand
    evidence_quality: QualityBand
    assumption_quality: QualityBand
    threshold_quality: QualityBand
    experiment_quality: QualityBand
    provenance_quality: QualityBand
    consistency_quality: QualityBand
    freshness_quality: QualityBand
    historical_learning_quality: QualityBand
    blocking_issues: list[QualityCheck] = Field(
        default_factory=list,
        description="Every check with status=failed and severity in {high, critical} - the "
        "spec's 'blocking issues' surface.",
    )
    warnings: list[QualityCheck] = Field(default_factory=list)
    strengths: list[QualityCheck] = Field(
        default_factory=list,
        description="Every check with status=passed - the demo-ready 'Evidence grounded / "
        "Thresholds connected / ...' checklist (spec section 23).",
    )
    checks: list[QualityCheck] = Field(
        default_factory=list,
        description="Every check that ran, regardless of outcome - the "
        "full, inspectable audit trail behind the summary fields above.",
    )
    generated_at: datetime
    methodology_version: str = Field(default="quality-v1")
