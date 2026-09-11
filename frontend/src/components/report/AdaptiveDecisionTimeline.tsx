import { CheckCircle2, CircleDashed, FlaskConical, OctagonPause, TriangleAlert } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { cn } from '@/lib/cn';
import { toneSurface } from '@/lib/tone';
import type { AdaptiveCycleRow } from '@/types/report';

export interface AdaptiveDecisionTimelineProps {
  cycles: AdaptiveCycleRow[];
}

function iconFor(row: AdaptiveCycleRow): LucideIcon {
  if (row.statusLabel === 'Stopped') return OctagonPause;
  if (row.statusTone === 'success') return CheckCircle2;
  if (row.statusTone === 'warning') return TriangleAlert;
  if (row.currentExperimentId) return FlaskConical;
  return CircleDashed;
}

/**
 * The full validation-journey history for a decision, oldest first:
 * Cycle 1 (Experiment A) -> Cycle 2 (Experiment B) -> ... -> concluded.
 * Reuses the exact connector-line `<ol>` layout already established by
 * `MemoryTimeline`/`components/dashboard/ActivityTimeline.tsx`, driven
 * here by the real `AdaptiveExperimentState` history
 * (`GET /decisions/{id}/adaptive/history`) rather than a second,
 * separately-tracked activity log.
 */
export function AdaptiveDecisionTimeline({ cycles }: AdaptiveDecisionTimelineProps) {
  if (cycles.length === 0) {
    return (
      <EmptyState
        icon={FlaskConical}
        title="No validation cycles yet"
        description="Start the adaptive loop to begin tracking this decision's testing history."
      />
    );
  }

  const lastIndex = cycles.length - 1;

  return (
    <ol>
      {cycles.map((row, index) => {
        const Icon = iconFor(row);
        const isLast = index === lastIndex;

        return (
          <li key={row.stateId} className="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-x-4">
            <div className="flex flex-col items-center">
              <span
                className={cn(
                  'inline-flex size-7 shrink-0 items-center justify-center rounded-md border',
                  toneSurface[row.statusTone],
                )}
              >
                <Icon className="size-3.5" aria-hidden />
              </span>
              {isLast ? null : <span className="mt-1.5 w-px flex-1 bg-hairline" aria-hidden />}
            </div>

            <div className={cn('min-w-0', isLast ? 'pb-0' : 'pb-6')}>
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <p className="text-card-title text-ink">
                  Cycle {row.cycleNumber} · <Badge tone={row.statusTone} size="sm">{row.statusLabel}</Badge>
                </p>
                <span className="numeric shrink-0 text-micro text-ink-muted">{row.createdAtLabel}</span>
              </div>
              <p className="mt-1 text-small text-ink-secondary">{row.nextAction}</p>
              <p className="mt-1 text-micro text-ink-muted">
                Assessment at this point: {row.currentAssessmentLabel}
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
