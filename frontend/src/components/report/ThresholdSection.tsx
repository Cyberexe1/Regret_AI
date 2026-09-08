import { lazy, Suspense } from 'react';
import { Skeleton } from '@/components/ui/Skeleton';
import { cn } from '@/lib/cn';
import type { DecisionReport } from '@/types';
import { ThresholdJourney } from './ThresholdJourney';

/**
 * Recharts is loaded on demand so the report route does not carry the charting
 * library in the main bundle.
 */
const ThresholdChart = lazy(async () => {
  const module = await import('./ThresholdChart');
  return { default: module.ThresholdChart };
});

function ChartFallback() {
  return (
    <div className="h-64 w-full sm:h-72" aria-busy>
      <Skeleton shape="block" className="size-full" />
    </div>
  );
}

interface LegendItem {
  label: string;
  swatch: string;
}

const legend: LegendItem[] = [
  { label: 'Current estimate', swatch: 'bg-warning' },
  { label: 'Critical threshold', swatch: 'bg-danger' },
  { label: 'Safe zone', swatch: 'bg-success' },
];

export interface ThresholdSectionProps {
  report: DecisionReport;
}

export function ThresholdSection({ report }: ThresholdSectionProps) {
  const { threshold, recommendation, uncertainties } = report;
  const [low, high] = threshold.currentRange;
  const headline = uncertainties[0];

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-danger-line bg-panel-danger px-5 py-4 md:px-6">
        <p className="text-body text-ink">{threshold.narrative}</p>
      </div>

      <ThresholdJourney
        currentValue={`${low}–${high}%`}
        thresholdValue={`${threshold.thresholdValue}%`}
        experimentValue={recommendation.costLabel}
        experimentCaption="14-day pilot settles it"
      />

      <div className="rounded-xl border border-hairline bg-surface p-5 md:p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
          <div>
            <p className="eyebrow">{threshold.valueLabel}</p>
            <p className="mt-1 text-small text-ink-muted">
              Plotted against {threshold.metricLabel.toLowerCase()}
            </p>
          </div>
          <p className="numeric text-small text-ink-muted">
            Break-even at {threshold.breakEvenRate}%
          </p>
        </div>

        <div className="mt-5">
          <Suspense fallback={<ChartFallback />}>
            <ThresholdChart threshold={threshold} />
          </Suspense>
        </div>

        <ul className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-hairline pt-4">
          {legend.map((item) => (
            <li key={item.label} className="flex items-center gap-2 text-small text-ink-secondary">
              <span className={cn('size-2.5 rounded-sm', item.swatch)} aria-hidden />
              {item.label}
            </li>
          ))}
        </ul>
      </div>

      {headline ? (
        <p className="text-small text-ink-muted">
          The current estimate for {headline.title.toLowerCase()} sits below break-even. Everything
          between {high}% and {threshold.thresholdValue}% is survivable but not sustainable.
        </p>
      ) : null}
    </div>
  );
}
