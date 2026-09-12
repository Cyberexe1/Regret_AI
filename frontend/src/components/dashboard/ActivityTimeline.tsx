import { Activity } from 'lucide-react';
import { Card, CardTitle } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import type { ActivityEvent } from '@/lib/buildDashboard';
import { cn } from '@/lib/cn';
import { toneSurface } from '@/lib/tone';

export interface ActivityTimelineProps {
  events: ActivityEvent[];
}

/** Recent events across the workspace, newest first. */
export function ActivityTimeline({ events }: ActivityTimelineProps) {
  const lastIndex = events.length - 1;

  return (
    <Card variant="inset" padding="none" className="min-w-0 overflow-hidden">
      <div className="border-b border-hairline px-4 py-4 sm:px-5 md:px-6">
        <CardTitle>Decision activity</CardTitle>
        <p className="mt-0.5 break-words text-small text-ink-muted">Most recent events in this workspace</p>
      </div>

      {events.length === 0 ? (
        <EmptyState
          size="inline"
          icon={Activity}
          title="No activity yet"
          description="Create your first decision to see activity here."
        />
      ) : (
        <ol className="min-w-0 px-4 py-5 sm:px-5">
          {events.map((event, index) => {
            const Icon = event.icon;
            const isLast = index === lastIndex;

            return (
              <li key={event.id} className="grid min-w-0 grid-cols-[1.75rem_minmax(0,1fr)] gap-x-3 sm:gap-x-4">
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
                  <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                    <p className="min-w-0 break-words text-card-title text-ink">{event.label}</p>
                    <span className="numeric max-w-full break-words text-micro text-ink-muted sm:text-right">
                      {event.timestamp}
                    </span>
                  </div>
                  <p className="mt-1 break-words text-small text-ink-secondary">{event.detail}</p>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </Card>
  );
}
