import { Card, CardTitle } from '@/components/ui/Card';
import { Progress } from '@/components/ui/Progress';
import { cn } from '@/lib/cn';
import { toneFill } from '@/lib/tone';
import type { ResolvedAnalysisMetric } from '@/hooks/useAnalysisSimulation';

export interface AnalysisMetricsPanelProps {
  progress: number;
  isComplete: boolean;
  metrics: ResolvedAnalysisMetric[];
}

export function AnalysisMetricsPanel({
  progress,
  isComplete,
  metrics,
}: AnalysisMetricsPanelProps) {
  return (
    <Card className="lg:sticky lg:top-[calc(var(--header-offset)+0.75rem)]">
      <CardTitle>Analysis progress</CardTitle>

      <div className="mt-4 flex items-baseline gap-1.5">
        <span className="numeric text-page-title text-ink">{progress}</span>
        <span className="text-small text-ink-muted">%</span>
        <span
          className={cn(
            'ml-auto text-small',
            isComplete ? 'text-success-ink' : 'text-accent-ink',
          )}
        >
          {isComplete ? 'Complete' : 'Running'}
        </span>
      </div>

      <Progress
        className="mt-3"
        value={progress}
        tone={isComplete ? 'success' : 'accent'}
        size="md"
      />

      <ul className="mt-6 space-y-3 border-t border-hairline pt-5">
        {metrics.map((metric) => (
          <li key={metric.id} className="flex items-center gap-3">
            <span
              className={cn(
                'size-2 shrink-0 rounded-full transition-opacity duration-500',
                toneFill[metric.tone],
                metric.settled ? 'opacity-100' : 'opacity-40',
              )}
              aria-hidden
            />
            <span className="flex-1 text-small text-ink-secondary">{metric.label}</span>
            <span className="numeric text-small font-medium text-ink">
              {metric.value}
              {metric.unit ? <span className="ml-1 font-normal text-ink-muted">{metric.unit}</span> : null}
            </span>
          </li>
        ))}
      </ul>

      <p className="mt-5 border-t border-hairline pt-4 text-micro text-ink-muted">
        Simulated values for this prototype. No external sources are being read yet.
      </p>
    </Card>
  );
}
