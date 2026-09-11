import { ShieldCheck } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import type { QualityAssessmentSummary, QualityCheckRow } from '@/types/report';

export interface QualityAssessmentPanelProps {
  summary: QualityAssessmentSummary;
  isLoading?: boolean;
}

/**
 * REGRET ENGINE 2.0's Decision Intelligence Quality Engine (Step 24):
 * "HOW STRONG IS THIS ANALYSIS?" - a deterministic, inspectable
 * self-assessment of how well-grounded this decision's CURRENT
 * structured analysis is. Never a re-judgment of whether the decision
 * itself is wise.
 *
 * IMPORTANT: analysis quality is not the same as decision quality. A
 * decision can be high quality but poorly evidenced. A decision can be
 * poorly supported even if the AI sounds confident. Every band shown
 * here is deterministically derived from the checks listed below it -
 * it can never silently disagree with what a user can inspect.
 *
 * Structure, top to bottom:
 *   1. Overall band + the 8 category bands (evidence, assumptions,
 *      thresholds, experiments, provenance, consistency, freshness,
 *      historical learning).
 *   2. "What should you be careful about?" - blocking issues + warnings.
 *   3. Demo checklist - every check that passed, framed as a concrete
 *      strength ("Evidence grounded", "Thresholds connected", ...).
 */
export function QualityAssessmentPanel({ summary, isLoading = false }: QualityAssessmentPanelProps) {
  if (isLoading) {
    return (
      <EmptyState
        icon={ShieldCheck}
        title="Checking how well-grounded this analysis is…"
        description="Running deterministic checks against the decision's own evidence, assumptions, and thresholds."
      />
    );
  }

  if (!summary.found) {
    return (
      <EmptyState
        icon={ShieldCheck}
        title="No quality assessment yet"
        description="Run a quality check to see how well-grounded this decision's current analysis is."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-hairline bg-surface p-5 md:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="eyebrow">Overall analysis quality</p>
          <Badge tone={summary.overallBandTone} size="sm" dot>
            {summary.overallBandLabel}
          </Badge>
        </div>
        <p className="mt-2 text-small text-ink-secondary">
          This describes how well-grounded the ANALYSIS is - not whether the decision itself is
          wise. A decision can be high quality but poorly evidenced, or well supported even when
          it still feels uncertain.
        </p>

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {summary.categoryBands.map((band) => (
            <Card key={band.category} variant="inset" padding="sm" className="flex flex-col gap-1.5">
              <p className="text-micro text-ink-muted">{band.categoryLabel}</p>
              <Badge tone={band.bandTone} size="sm">
                {band.bandLabel}
              </Badge>
            </Card>
          ))}
        </div>
      </div>

      <CarefulAboutSection blockingIssues={summary.blockingIssues} warnings={summary.warnings} />

      <StrengthsChecklist strengths={summary.strengths} />
    </div>
  );
}

function CarefulAboutSection({
  blockingIssues,
  warnings,
}: {
  blockingIssues: QualityCheckRow[];
  warnings: QualityCheckRow[];
}) {
  if (blockingIssues.length === 0 && warnings.length === 0) {
    return (
      <div className="rounded-xl border border-hairline bg-surface-inset p-5 md:p-6">
        <p className="eyebrow">What should you be careful about?</p>
        <p className="mt-3 text-small text-ink-secondary">
          No blocking issues or warnings were found in this analysis's current evidence,
          assumptions, or thresholds.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-hairline-strong bg-surface-raised p-5 md:p-6">
      <p className="eyebrow">What should you be careful about?</p>
      <ul className="mt-3 space-y-3">
        {[...blockingIssues, ...warnings].map((check) => (
          <li key={check.checkId} className="border-t border-hairline pt-3 first:border-t-0 first:pt-0">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <p className="text-small text-ink">{check.message}</p>
              <Badge tone={check.statusTone} size="sm">
                {check.severityLabel}
              </Badge>
            </div>
            {check.recommendation ? (
              <p className="mt-1.5 text-micro text-ink-muted">{check.recommendation}</p>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

function StrengthsChecklist({ strengths }: { strengths: QualityCheckRow[] }) {
  if (strengths.length === 0) return null;

  return (
    <div className="rounded-xl border border-hairline bg-surface p-5 md:p-6">
      <p className="eyebrow">What's well-grounded</p>
      <ul className="mt-3 grid gap-2 sm:grid-cols-2">
        {strengths.map((check) => (
          <li key={check.checkId} className="flex items-start gap-2 text-small text-ink-secondary">
            <span className="mt-0.5 text-success-ink" aria-hidden>
              ✓
            </span>
            <span>{check.message}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
