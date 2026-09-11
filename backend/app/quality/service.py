"""Quality & Calibration orchestration (REGRET ENGINE 2.0, Step 24).

`QualityService.run_quality_check` is the one operation that actually
(re)computes a `QualityAssessment` - it is invoked additively after the
analysis pipeline completes and after each re-evaluation (see
`app.agents.orchestrator`/`app.api.routes.experiments`), never on every
read. `get_latest`/`list_history` only ever return what the last check
already persisted.

`CalibrationService.refresh_calibration` mirrors
`CrossDecisionLearningService.refresh_patterns` exactly: bounded,
user-scoped loading of a user's own decisions, deterministic
aggregation, idempotent upsert. Neither service ever aggregates across
different users.

No LLM call happens anywhere in this module.
"""

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from app.core.config import get_settings
from app.core.logging import get_logger
from app.learning.repository import CrossDecisionLearningRepository
from app.learning.schemas import HistoricalLearningSignal
from app.memory.memory_repository import MemoryRepository
from app.quality import rules
from app.quality.calibration import (
    CalibrationInsight,
    DecisionCalibrationSignals,
    compute_calibration_insights,
)
from app.quality.repository import CalibrationRepository, QualityRepository
from app.quality.rules import DecisionQualitySignals
from app.quality.schemas import (
    QualityAssessment,
    QualityBand,
    QualityCheck,
    QualityCheckCategory,
    QualityCheckStatus,
)
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.decision_repository import DecisionRepository
from app.repositories.evidence_repository import EvidenceRepository

logger = get_logger(__name__)

_QUALITY_NAMESPACE = uuid5(NAMESPACE_URL, "regret-engine:quality:assessment")

# spec section 3's exact status->severity->band derivation, expressed as
# ordered bounds rather than magic numbers scattered through the logic.
_BLOCKING_SEVERITIES = {"high", "critical"}


def _category_band(checks: list[QualityCheck]) -> QualityBand:
    """Deterministically derives one category's band from its own
    checks' statuses/severities - never a separately-judged number that
    could disagree with the checks a user can inspect directly below it.
    """
    if not checks:
        return QualityBand.INSUFFICIENT

    has_critical_failure = any(
        c.status == QualityCheckStatus.FAILED and c.severity.value in _BLOCKING_SEVERITIES
        for c in checks
    )
    if has_critical_failure:
        return QualityBand.WEAK

    failed_count = sum(1 for c in checks if c.status == QualityCheckStatus.FAILED)
    warning_count = sum(1 for c in checks if c.status == QualityCheckStatus.WARNING)
    passed_count = sum(1 for c in checks if c.status == QualityCheckStatus.PASSED)

    if failed_count > 0:
        return QualityBand.WEAK
    if warning_count > passed_count:
        return QualityBand.MODERATE
    if warning_count > 0:
        return QualityBand.MODERATE
    if passed_count > 0:
        return QualityBand.STRONG
    return QualityBand.INSUFFICIENT


_BAND_ORDER = [QualityBand.INSUFFICIENT, QualityBand.WEAK, QualityBand.MODERATE, QualityBand.STRONG]


def overall_band_from_categories(category_bands: list[QualityBand]) -> QualityBand:
    """The overall band is always the WEAKEST category band that has any
    real signal (i.e. isn't `INSUFFICIENT` due to having nothing to
    check) - never an independently-computed average that could
    disagree with what a user sees per-category. If every category is
    `INSUFFICIENT`, the overall is `INSUFFICIENT` too."""
    meaningful = [b for b in category_bands if b != QualityBand.INSUFFICIENT]
    if not meaningful:
        return QualityBand.INSUFFICIENT
    return min(meaningful, key=lambda b: _BAND_ORDER.index(b))


class QualityService:
    """Runs the deterministic quality checks for one decision and
    persists the resulting `QualityAssessment`."""

    def __init__(
        self,
        decision_repository: DecisionRepository,
        evidence_repository: EvidenceRepository,
        analysis_repository: AnalysisRepository,
        memory_repository: MemoryRepository,
        learning_repository: CrossDecisionLearningRepository,
        quality_repository: QualityRepository,
    ) -> None:
        self._decisions = decision_repository
        self._evidence = evidence_repository
        self._analyses = analysis_repository
        self._memory = memory_repository
        self._learning = learning_repository
        self._quality = quality_repository

    def get_latest(self, decision_id: UUID) -> QualityAssessment | None:
        return self._quality.get_latest(str(decision_id))

    def list_history(self, decision_id: UUID) -> list[QualityAssessment]:
        return self._quality.list_for_decision(str(decision_id))

    def run_quality_check(self, decision_id: UUID, user_id: str) -> QualityAssessment:
        """(Re)computes and persists a fresh `QualityAssessment` for
        this decision, from its CURRENT canonical records. Idempotent in
        spirit: the resulting `quality_id` is deterministic per
        `(decision_id, analysis_run_id)`, so re-running with the same
        underlying analysis run produces a check set that is content-
        identical (though a fresh, later `generated_at`) - callers that
        want to avoid persisting a no-op duplicate can compare the new
        assessment's checks against `get_latest` first.
        """
        signals = self._load_signals(decision_id, user_id)
        quality_id = self._quality_id(decision_id, signals.analysis_run_id)

        primary_uncertainty_variable = self._primary_uncertainty_variable(signals)
        historical_signal, _ = self._historical_signal(user_id, primary_uncertainty_variable)

        checks_by_category: dict[QualityCheckCategory, list[QualityCheck]] = {
            QualityCheckCategory.EVIDENCE: rules.check_evidence_quality(quality_id, signals),
            QualityCheckCategory.ASSUMPTION: rules.check_assumption_quality(quality_id, signals),
            QualityCheckCategory.THRESHOLD: rules.check_threshold_quality(quality_id, signals),
            QualityCheckCategory.EXPERIMENT: rules.check_experiment_quality(
                quality_id, signals, primary_uncertainty_variable
            ),
            QualityCheckCategory.PROVENANCE: rules.check_provenance_quality(
                quality_id, signals, user_id
            ),
            QualityCheckCategory.CONSISTENCY: rules.check_consistency(quality_id, signals),
            QualityCheckCategory.FRESHNESS: rules.check_freshness(quality_id, signals),
            QualityCheckCategory.HISTORICAL: (
                rules.check_historical_learning(quality_id, signals)
                + rules.check_historical_reliance(
                    quality_id, historical_signal, len(signals.evidence_findings)
                )
            ),
            QualityCheckCategory.COMPLETENESS: rules.check_completeness(quality_id, signals),
        }

        category_bands = {
            category: _category_band(checks) for category, checks in checks_by_category.items()
        }
        # "Completeness" informs the overall band but has no dedicated
        # QualityAssessment field (spec's field list doesn't include
        # one) - folded into evidence_quality's own signal since a
        # missing required stage IS an evidence-completeness concern.
        overall = overall_band_from_categories(list(category_bands.values()))

        all_checks = [check for checks in checks_by_category.values() for check in checks]
        blocking_issues = [
            c
            for c in all_checks
            if c.status == QualityCheckStatus.FAILED and c.severity.value in _BLOCKING_SEVERITIES
        ]
        warnings = [c for c in all_checks if c.status == QualityCheckStatus.WARNING]
        strengths = [c for c in all_checks if c.status == QualityCheckStatus.PASSED]

        assessment = QualityAssessment(
            quality_id=quality_id,
            decision_id=str(decision_id),
            analysis_run_id=signals.analysis_run_id,
            user_id=user_id,
            overall_quality=overall,
            evidence_quality=category_bands[QualityCheckCategory.EVIDENCE],
            assumption_quality=category_bands[QualityCheckCategory.ASSUMPTION],
            threshold_quality=category_bands[QualityCheckCategory.THRESHOLD],
            experiment_quality=category_bands[QualityCheckCategory.EXPERIMENT],
            provenance_quality=category_bands[QualityCheckCategory.PROVENANCE],
            consistency_quality=category_bands[QualityCheckCategory.CONSISTENCY],
            freshness_quality=category_bands[QualityCheckCategory.FRESHNESS],
            historical_learning_quality=category_bands[QualityCheckCategory.HISTORICAL],
            blocking_issues=blocking_issues,
            warnings=warnings,
            strengths=strengths,
            checks=all_checks,
            generated_at=datetime.now(UTC),
        )

        self._quality.create(assessment)
        logger.info(
            "Quality assessment computed decision_id=%s quality_id=%s overall=%s "
            "checks=%d blocking=%d warnings=%d",
            decision_id,
            quality_id,
            overall.value,
            len(all_checks),
            len(blocking_issues),
            len(warnings),
        )
        return assessment

    # --- internal ------------------------------------------------------------

    def _quality_id(self, decision_id: UUID, analysis_run_id: str | None) -> str:
        discriminator = analysis_run_id or "no-analysis-run"
        return str(uuid5(_QUALITY_NAMESPACE, f"{decision_id}:{discriminator}"))

    def _primary_uncertainty_variable(self, signals: DecisionQualitySignals) -> str | None:
        """Best-effort, real-data-only lookup of the primary
        uncertainty's variable name, resolved via whichever threshold
        the highest-importance assumption/blindspot links to - never a
        fabricated guess when nothing links."""
        threshold_by_assumption: dict[str, str] = {}
        for threshold in signals.thresholds:
            for aid in threshold.related_assumption_ids:
                threshold_by_assumption[aid] = threshold.variable

        critical_assumptions = [
            a for a in signals.assumptions if (a.importance or "").lower() in {"critical", "high"}
        ]
        for assumption in critical_assumptions:
            variable = threshold_by_assumption.get(str(assumption.id))
            if variable:
                return variable
        return None

    def _historical_signal(
        self, user_id: str, variable: str | None
    ) -> tuple[HistoricalLearningSignal, str]:
        try:
            patterns = self._learning.list_patterns_for_user(user_id, variable=variable)
        except Exception:  # noqa: BLE001 - historical signal is additive, never required
            return HistoricalLearningSignal.NONE, ""
        if not patterns:
            return HistoricalLearningSignal.NONE, ""
        strongest = max(patterns, key=lambda p: p.occurrence_count)
        if strongest.status.value == "established":
            return HistoricalLearningSignal.STRONG, strongest.title
        return HistoricalLearningSignal.MODERATE, strongest.title

    def _load_signals(self, decision_id: UUID, user_id: str) -> DecisionQualitySignals:
        """Bounded, single-decision load of every canonical record the
        quality rules need - mirrors
        `CrossDecisionLearningService._load_signals`'s exact shape, just
        scoped to ONE decision instead of a user's whole history."""
        decision = self._decisions.get(decision_id)
        if decision is None:
            raise ValueError(f"Decision {decision_id} not found.")

        memory_records = self._memory.list_memory_for_decision(decision_id)
        analysis_runs = self._analyses.list_for_decision(decision_id)
        latest_run = max(analysis_runs, key=lambda r: r.created_at) if analysis_runs else None

        analysis_result_keys: set[str] = set()
        if latest_run is not None and latest_run.result:
            analysis_result_keys = set(latest_run.result.keys())

        try:
            patterns = self._learning.get_patterns_for_decision(user_id, decision_id)
        except Exception:  # noqa: BLE001 - historical patterns are additive, never required
            patterns = []

        return DecisionQualitySignals(
            decision=decision,
            assumptions=self._decisions.list_assumptions(decision_id),
            blindspots=self._decisions.list_blindspots(decision_id),
            evidence=self._evidence.list_for_decision(decision_id),
            evidence_findings=self._decisions.list_evidence_findings(decision_id),
            thresholds=self._decisions.list_thresholds(decision_id),
            experiments=self._decisions.list_experiments(decision_id),
            experiment_results=self._decisions.list_experiment_results(decision_id),
            reevaluations=self._decisions.list_reevaluations(decision_id),
            memory=memory_records[0] if memory_records else None,
            learnings=self._memory.list_learnings_for_decision(decision_id),
            cross_decision_patterns=patterns,
            analysis_run_id=str(latest_run.id) if latest_run else None,
            analysis_result_keys=analysis_result_keys,
            analysis_completed_at=latest_run.completed_at if latest_run else None,
        )


class CalibrationService:
    """Aggregates a user's OWN calibration observations across their
    completed experiments/re-evaluations - never across users."""

    def __init__(
        self,
        decision_repository: DecisionRepository,
        calibration_repository: CalibrationRepository,
    ) -> None:
        self._decisions = decision_repository
        self._calibration = calibration_repository

    def list_for_user(self, user_id: str) -> list[CalibrationInsight]:
        return self._calibration.list_for_user(user_id)

    def get_for_variable(self, user_id: str, variable: str) -> CalibrationInsight | None:
        return self._calibration.get_for_variable(user_id, variable)

    def refresh_calibration(self, user_id: str) -> list[CalibrationInsight]:
        """Rebuilds every calibration insight for one user from their
        current canonical records. Bounded to the user's own most
        recent `settings.learning_max_decisions_scanned` decisions -
        the SAME bound Step 23's Cross-Decision Learning already
        established, reused here rather than inventing a second one.
        """
        settings = get_settings()
        decisions, _ = self._decisions.list_for_user(
            user_id, limit=settings.learning_max_decisions_scanned
        )

        signals = [
            DecisionCalibrationSignals(
                decision_id=str(decision.id),
                thresholds=self._decisions.list_thresholds(decision.id),
                reevaluations=self._decisions.list_reevaluations(decision.id),
            )
            for decision in decisions
        ]

        insights = compute_calibration_insights(user_id, signals)
        for insight in insights:
            self._calibration.upsert(insight)
        return insights
