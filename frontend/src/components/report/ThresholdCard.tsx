import { Gauge, HelpCircle } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import { cn } from '@/lib/cn';
import { toneText } from '@/lib/tone';
import type { ReportThreshold } from '@/types/report';

export interface ThresholdCardProps {
  threshold: ReportThreshold;
}

/**
 * One threshold, rendered honestly according to what the backend actually
 * knows:
 *
 * - A qualitative card (no numeric axis, no invented percentage) when the
 *   Threshold Engine could not derive a numeric value - this is the
 *   common case for early-stage decisions with thin evidence.
 * - A simple bounded gauge only when the backend supplied real
 *   `lower_bound`/`upper_bound` floats to plot a position within.
 *
 * Never places a threshold on a fake numeric chart, and never implies
 * certainty a `provisional`/`unknown` validation status contradicts.
 */
export function ThresholdCard({ threshold }: ThresholdCardProps) {
  const showGauge =
    threshold.hasNumericValue && threshold.lowerBound !== null && threshold.upperBound !== null;

  return (
    <div className="rounded-xl border border-hairline bg-surface p-5 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="eyebrow">{threshold.variable}</p>
          {threshold.direction ? (
            <p className="mt-1 text-small text-ink-muted">Direction: {threshold.direction}</p>
          ) : null}
        </div>
        <Badge tone={threshold.validationStatusTone} size="sm" dot>
          {threshold.validationStatusLabel}
        </Badge>
      </div>

      <div className="mt-4">
        {threshold.hasNumericValue ? (
          <div className="flex items-baseline gap-2">
            <Gauge className={cn('size-4', toneText[threshold.validationStatusTone])} aria-hidden />
            <span className="numeric text-metric text-ink">{threshold.thresholdValue}</span>
            {threshold.unit ? <span className="text-small text-ink-muted">{threshold.unit}</span> : null}
          </div>
        ) : (
          <div className="flex items-start gap-2.5 rounded-lg border border-hairline-strong bg-surface-inset px-4 py-3">
            <HelpCircle className="mt-0.5 size-4 shrink-0 text-ink-muted" aria-hidden />
            <p className="text-small text-ink-secondary">
              No numeric value has been established for this threshold yet. It remains a{' '}
              {threshold.validationStatusLabel.toLowerCase()} qualitative tipping point.
            </p>
          </div>
        )}
      </div>

      {showGauge && threshold.lowerBound !== null && threshold.upperBound !== null ? (
        <div className="mt-4">
          <Progress
            value={((Number(threshold.thresholdValue) - threshold.lowerBound) /
              (threshold.upperBound - threshold.lowerBound)) *
              100}
            tone={threshold.validationStatusTone}
            size="sm"
          />
          <div className="mt-1.5 flex justify-between text-micro text-ink-muted">
            <span className="numeric">{threshold.lowerBound}</span>
            <span className="numeric">{threshold.upperBound}</span>
          </div>
        </div>
      ) : null}

      {threshold.consequence ? (
        <p className="mt-4 border-t border-hairline pt-4 text-small text-ink-secondary">
          {threshold.consequence}
        </p>
      ) : null}

      {threshold.confidencePercent !== undefined ? (
        <p className="mt-3 text-micro text-ink-muted">Confidence: {threshold.confidencePercent}%</p>
      ) : null}
    </div>
  );
}
