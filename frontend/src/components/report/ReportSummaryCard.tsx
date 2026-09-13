import type { LucideIcon } from 'lucide-react';
import { FlaskConical, Gauge, ShieldAlert, ShieldCheck } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import type { ApiExperiment } from '@/api/types';
import type { CriticalUncertainty, QualityAssessmentSummary, ReportThreshold } from '@/types/report';
import type { Tone } from '@/types';

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
 * a user never HAS to scroll through all 13 sections to get an answer.
 * Nothing here is a new judgment: every value is the same top-ranked
 * item/summary the corresponding section below already shows, just
 * pulled to the top and stripped of its supporting detail.
 */
export function ReportSummaryCard({
  topUncertainty,
  primaryThreshold,
  recommendedExperiment,
  quality,
}: ReportSummaryCardProps) {
  return (
    <Card variant="raised" className="border-accent-line">
      <p className="eyebrow">In short</p>

      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryFact
          icon={ShieldAlert}
          label="Biggest risk"
          value={topUncertainty ? topUncertainty.title : 'None identified yet'}
          tone={topUncertainty?.importanceTone}
          toneLabel={topUncertainty ? `${topUncertainty.importanceLabel} importance` : undefined}
        />

        <SummaryFact
          icon={Gauge}
          label="Threshold that decides it"
          value={primaryThreshold ? primaryThreshold.variable : 'Not established yet'}
          tone={primaryThreshold?.validationStatusTone}
          toneLabel={primaryThreshold?.validationStatusLabel}
        />

        <SummaryFact
          icon={FlaskConical}
          label="What to test first"
          value={recommendedExperiment ? recommendedExperiment.title : 'No experiment recommended yet'}
        />

        <SummaryFact
          icon={ShieldCheck}
          label="Analysis quality"
          value={quality.found ? quality.overallBandLabel : 'Not assessed yet'}
          tone={quality.found ? quality.overallBandTone : undefined}
        />
      </div>
    </Card>
  );
}

function SummaryFact({
  icon: Icon,
  label,
  value,
  tone,
  toneLabel,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  tone?: Tone;
  toneLabel?: string;
}) {
  return (
    <div className="min-w-0">
      <div className="flex items-center gap-1.5 text-ink-muted">
        <Icon className="size-3.5 shrink-0" aria-hidden />
        <p className="text-micro">{label}</p>
      </div>
      <p className="mt-1.5 line-clamp-2 text-small font-medium text-ink">{value}</p>
      {tone && toneLabel ? (
        <Badge tone={tone} size="sm" className="mt-2">
          {toneLabel}
        </Badge>
      ) : null}
    </div>
  );
}
