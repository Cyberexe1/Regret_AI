import { CheckCircle2, Circle, FlaskConical, Gauge, RefreshCw, ScanSearch, SquarePen } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { EmptyState } from '@/components/ui/EmptyState';
import { cn } from '@/lib/cn';
import { toneSurface } from '@/lib/tone';
import type { MemoryTimelineEvent } from '@/types/report';

export interface MemoryTimelineProps {
  events: MemoryTimelineEvent[];
}

/** Icon per timeline step, keyed by the event id's stable prefix - purely
 * presentational, matches no backend field. */
function iconFor(eventId: string): LucideIcon {
  if (eventId === 'decision-created') return SquarePen;
  if (eventId === 'analysis-completed') return ScanSearch;
  if (eventId === 'threshold-identified') return Gauge;
  if (eventId.startsWith('experiment-started')) return FlaskConical;
  if (eventId.startsWith('experiment-completed')) return CheckCircle2;
  if (eventId.startsWith('reevaluated')) return RefreshCw;
  return Circle;
}

/**
 * The learning timeline: Decision Created -> Analysis Completed ->
 * Critical Threshold Identified -> Experiment Started -> Experiment
 * Completed -> Decision Re-evaluated -> Learning Recorded. Reuses the
 * exact connector-line `<ol>` layout already established by
 * `components/dashboard/ActivityTimeline.tsx`, driven here by real
 * decision/analysis/experiment/re-evaluation timestamps instead of
 * generic workspace activity.
 */
export function MemoryTimeline({ events }: MemoryTimelineProps) {
  if (events.length === 0) {
    return (
      <EmptyState
        icon={ScanSearch}
        title="No timeline yet"
        description="This decision has not been analyzed yet."
      />
    );
  }

  const lastIndex = events.length - 1;

  return (
    <ol>
      {events.map((event, index) => {
        const Icon = iconFor(event.id);
        const isLast = index === lastIndex;

        return (
          <li key={event.id} className="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-x-4">
            <div className="flex flex-col items-center">
              <span
                className={cn(
                  'inline-flex size-7 shrink-0 items-center justify-center rounded-md border',
                  toneSurface[event.tone],
                )}
              >
                <Icon className="size-3.5" aria-hidden />
              </span>
              {isLast ? null : <span className="mt-1.5 w-px flex-1 bg-hairline" aria-hidden />}
            </div>

            <div className={cn('min-w-0', isLast ? 'pb-0' : 'pb-6')}>
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <p className="text-card-title text-ink">{event.label}</p>
                <span className="numeric shrink-0 text-micro text-ink-muted">
                  {event.timestampLabel}
                </span>
              </div>
              <p className="mt-1 text-small text-ink-secondary">{event.detail}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
