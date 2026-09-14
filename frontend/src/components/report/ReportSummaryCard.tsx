import type { LucideIcon } from 'lucide-react';
import { FlaskConical, Gauge, ShieldAlert, ShieldCheck } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import type { ApiExperiment } from '@/api/types';
import type { CriticalUncertainty, QualityAssessmentSummary, ReportThreshold } from '@/types/report';
import type { Tone } from '@/types';
import { cn } from '@/lib/cn';

export interface ReportSummaryCardProps {
  /** Already sorted by importance - see `buildCriticalUncertainties`.
   * `uncertainties[0]` is the biggest thing that could break this
   * decision, never re-derived here. */
  topUncertainty: CriticalUncertainty | null;
  /** Already sorted; a decision may have no threshold yet if analysis
   * hasn't reached the Threshold Engine stage. */
  primaryThreshold: ReportThreshold | null;
  recommendedExperiment: ApiExperiment | null;
  quality: QualityAssessmentSummary;
}

/**
 * The report's "read this first" card - four already-computed facts the
 * rest of the page repeats in full detail further down, surfaced here so
 * a user never HAS to scroll through every section to get an answer.
 * Nothing here is a new judgment: every value is the same top-ranked
 * item/summary the corresponding section below already shows.
 *
 * Rendered as full-width rows rather than a tight 4-up grid so the actual
 * TEXT is readable - the biggest risk's real statement, not three words
 * of it cut off with an ellipsis - plus a short "why it matters" line
 * under each fact, so a user can act on this card alone if they want to.
 */
export function ReportSummaryCard({
  topUncertainty,
  primaryThreshold,
  recommendedExperiment,
  quality,
}: ReportSummaryCardProps) {
  return (
    <Card variant="raised" padding="none" className="overflow-hidden border-accent-line">
      <div className="border-b border-accent-line bg-panel-accent px-5 py-4 md:px-6">
        <p className="eyebrow text-accent-ink">In short</p>
        <p className="mt-1 text-small text-ink-secondary">
          The four things worth knowing before you read the full report below.
        </p>
      </div>

      <div className="divide-y divide-hairline">
        <SummaryRow
          icon={ShieldAlert}
          label="Biggest risk"
          title={topUncertainty ? topUncertainty.title : 'No critical risk identified yet'}
          detail={
            topUncertainty?.failureConsequence ?? topUncertainty?.whyItMatters ?? topUncertainty?.evidenceGap
          }
          tone={topUncertainty?.importanceTone}
          toneLabel={topUncertainty ? `${topUncertainty.importanceLabel} importance` : undefined}
        />

        <SummaryRow
          icon={Gauge}
          label="Threshold that decides it"
          title={
            primaryThreshold
              ? primaryThreshold.thresholdValue
                ? `${primaryThreshold.variable}: ${primaryThreshold.thresholdValue}${primaryThreshold.unit ?? ''}`
                : primaryThreshold.variable
              : 'No threshold established yet'
          }
          detail={primaryThreshold?.consequence}
          tone={primaryThreshold?.validationStatusTone}
          toneLabel={primaryThreshold?.validationStatusLabel}
        />

        <SummaryRow
          icon={FlaskConical}
          label="What to test first"
          title={recommendedExperiment ? recommendedExperiment.title : 'No experiment recommended yet'}
          detail={recommendedExperiment?.hypothesis}
        />

        <SummaryRow
          icon={ShieldCheck}
          label="Analysis quality"
          title={quality.found ? quality.overallBandLabel : 'Not assessed yet'}
          detail={
            quality.found
              ? quality.blockingIssues.length > 0
                ? `${quality.blockingIssues.length} thing${quality.blockingIssues.length === 1 ? '' : 's'} to be careful about before you rely on this analysis.`
                : "This analysis is well-grounded - see 'Analysis Quality' below for the full breakdown."
              : undefined
          }
          tone={quality.found ? quality.overallBandTone : undefined}
        />
      </div>
    </Card>
  );
}

function SummaryRow({
  icon: Icon,
  label,
  title,
  detail,
  tone,
  toneLabel,
}: {
  icon: LucideIcon;
  label: string;
  title: string;
  detail?: string | null;
  tone?: Tone;
  toneLabel?: string;
}) {
  return (
    <div className="flex gap-4 px-5 py-4 md:px-6">
      <span
        className={cn(
          'flex size-9 shrink-0 items-center justify-center rounded-lg border',
          tone ? toneShellClass(tone) : 'border-hairline bg-surface-inset text-ink-muted',
        )}
      >
        <Icon className="size-4" aria-hidden />
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-micro font-medium tracking-[0.06em] text-ink-muted uppercase">{label}</p>
          {toneLabel ? (
            <Badge tone={tone ?? 'neutral'} size="sm">
              {toneLabel}
            </Badge>
          ) : null}
        </div>
        <p className="mt-1 text-body font-medium text-ink">{title}</p>
        {detail ? <p className="mt-1 text-small text-ink-secondary">{detail}</p> : null}
      </div>
    </div>
  );
}

function toneShellClass(tone: Tone): string {
  const shell: Record<Tone, string> = {
    neutral: 'border-hairline bg-surface-inset text-ink-muted',
    accent: 'border-accent-line bg-accent-soft text-accent-ink',
    success: 'border-success-line bg-success-soft text-success-ink',
    warning: 'border-warning-line bg-warning-soft text-warning-ink',
    danger: 'border-danger-line bg-danger-soft text-danger-ink',
    info: 'border-info-line bg-info-soft text-info-ink',
  };
  return shell[tone];
}
