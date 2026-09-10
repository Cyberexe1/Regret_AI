import { Card, CardTitle } from '@/components/ui/Card';
import { Progress } from '@/components/ui/Progress';
import type { ApiAnalysisRunStatusResponse } from '@/api/types';
import { agentRunStatusLabel, stageLabel } from '@/lib/labels';
import { cn } from '@/lib/cn';

export interface AnalysisMetricsPanelProps {
  run: ApiAnalysisRunStatusResponse | null;
  isComplete: boolean;
}

const TERMINAL = new Set(['completed', 'failed', 'skipped', 'unavailable']);

/**
 * Real progress derived from the backend's own `stage_statuses` - the
 * fraction of the 9 pipeline stages that have reached a terminal status.
 * No fabricated counters (evidence checked, assumptions found, etc.) are
 * shown here anymore; those numbers now come from the real, persisted
 * entities once analysis completes (see the Decision Report).
 */
export function AnalysisMetricsPanel({ run, isComplete }: AnalysisMetricsPanelProps) {
  const stageEntries = Object.entries(run?.stage_statuses ?? {});
  const totalStages = 9;
  const completedStages = stageEntries.filter(([, status]) => status && TERMINAL.has(status)).length;
  const progress = totalStages > 0 ? Math.round((completedStages / totalStages) * 100) : 0;

  return (
    <Card className="lg:sticky lg:top-[calc(var(--header-offset)+0.75rem)]">
      <CardTitle>Analysis progress</CardTitle>

      <div className="mt-4 flex items-baseline gap-1.5">
        <span className="numeric text-page-title text-ink">{progress}</span>
        <span className="text-small text-ink-muted">%</span>
        <span
          className={cn(
            'ml-auto text-small',
            run?.status === 'failed'
              ? 'text-danger-ink'
              : isComplete
                ? 'text-success-ink'
                : 'text-accent-ink',
          )}
        >
          {run?.status === 'failed' ? 'Failed' : isComplete ? 'Complete' : 'Running'}
        </span>
      </div>

      <Progress
        className="mt-3"
        value={progress}
        tone={run?.status === 'failed' ? 'danger' : isComplete ? 'success' : 'accent'}
        size="md"
      />

      <ul className="mt-6 space-y-2.5 border-t border-hairline pt-5">
        {stageEntries.map(([stageId, status]) => (
          <li key={stageId} className="flex items-center justify-between gap-3">
            <span className="min-w-0 flex-1 truncate text-small text-ink-secondary">
              {stageLabel[stageId] ?? stageId}
            </span>
            <span className="shrink-0 text-micro text-ink-muted">
              {status ? agentRunStatusLabel[status] : 'Waiting'}
            </span>
          </li>
        ))}
      </ul>

      {run?.error_message ? (
        <p className="mt-5 border-t border-hairline pt-4 text-micro text-danger-ink">
          {run.error_message}
        </p>
      ) : (
        <p className="mt-5 border-t border-hairline pt-4 text-micro text-ink-muted">
          Live status from the analysis backend. No values shown here are estimated or simulated.
        </p>
      )}
    </Card>
  );
}
