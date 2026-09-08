import { Card, CardTitle } from '@/components/ui/Card';
import { activityEvents } from '@/data/dashboard';
import { cn } from '@/lib/cn';
import { toneSurface } from '@/lib/tone';

/** Recent events across the workspace, newest first. */
export function ActivityTimeline() {
  const lastIndex = activityEvents.length - 1;

  return (
    <Card variant="inset" padding="none" className="overflow-hidden">
      <div className="border-b border-hairline px-5 py-4 md:px-6">
        <CardTitle>Decision activity</CardTitle>
        <p className="mt-0.5 text-small text-ink-muted">Last five events in this workspace</p>
      </div>

      <ol className="px-5 py-5">
        {activityEvents.map((event, index) => {
          const Icon = event.icon;
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
                    {event.timestamp}
                  </span>
                </div>
                <p className="mt-1 text-small text-ink-secondary">{event.detail}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </Card>
  );
}
