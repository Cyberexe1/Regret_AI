import { motion, useReducedMotion } from 'framer-motion';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { cn } from '@/lib/cn';
import { toneText } from '@/lib/tone';
import type { ExperimentDetail } from '@/types';
import { DURATION, EASE_OUT } from '@/lib/motion';

export interface ExperimentResultsProps {
  detail: ExperimentDetail;
}

/**
 * Observed value against the threshold. A purpose-built bar rather than a chart
 * library: it is one comparison, and it should read instantly.
 */
/**
 * Sits directly on the page rather than in a card: the metric tiles above are
 * already cards, and nesting another one made the section read as card soup.
 */
function ThresholdComparison({ detail }: { detail: ExperimentDetail }) {
  const reduceMotion = useReducedMotion();
  const { observedValue, thresholdValue, scaleMax } = detail;

  const toPercent = (value: number) => `${(value / scaleMax) * 100}%`;
  const shortfall = (thresholdValue - observedValue).toFixed(1);

  return (
    <div className="border-t border-hairline pt-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <p className="eyebrow">Repeat rate against threshold</p>
        <p className="numeric text-small text-warning-ink">{shortfall} points short</p>
      </div>

      <div className="relative mt-5 h-2.5 w-full rounded-full bg-canvas">
        <motion.div
          className="absolute inset-y-0 left-0 rounded-full bg-warning"
          initial={reduceMotion ? undefined : { width: 0 }}
          animate={{ width: toPercent(observedValue) }}
          transition={{ duration: DURATION.fill, ease: EASE_OUT }}
        />
        <div
          className="absolute -top-1.5 -bottom-1.5 w-0.5 rounded-full bg-danger"
          style={{ left: toPercent(thresholdValue) }}
          aria-hidden
        />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2">
        <span className="inline-flex items-center gap-2 text-small text-ink-secondary">
          <span className="size-2 rounded-sm bg-warning" aria-hidden />
          Observed {observedValue}%
        </span>
        <span className="inline-flex items-center gap-2 text-small text-ink-secondary">
          <span className="h-3 w-0.5 rounded-full bg-danger" aria-hidden />
          Threshold {thresholdValue}%
        </span>
        <span className="numeric ml-auto text-small text-ink-muted">Scale 0–{scaleMax}%</span>
      </div>
    </div>
  );
}

export function ExperimentResults({ detail }: ExperimentResultsProps) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {detail.results.map((metric) => (
          <Card key={metric.label} className="flex flex-col gap-2">
            <p className="eyebrow">{metric.label}</p>
            <p
              className={cn(
                'numeric text-metric',
                metric.tone ? toneText[metric.tone] : 'text-ink',
              )}
            >
              {metric.value}
            </p>
            {metric.hint ? <p className="text-small text-ink-muted">{metric.hint}</p> : null}
          </Card>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3 pt-1">
        <span className="text-small text-ink-secondary">Status</span>
        <Badge tone={detail.statusTone} dot>
          {detail.statusLabel}
        </Badge>
        <span className="text-small text-ink-muted">
          Measured on day {detail.currentDay} of {detail.durationDays}
        </span>
      </div>

      <ThresholdComparison detail={detail} />
    </div>
  );
}
