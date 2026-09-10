import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { Hourglass } from 'lucide-react';
import { Card, CardTitle } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import type { StageEvent } from '@/hooks/useAnalysisPolling';
import { cn } from '@/lib/cn';
import { toneFill } from '@/lib/tone';
import type { Tone } from '@/types';
import { DURATION, EASE_OUT } from '@/lib/motion';

const STATUS_TONE: Record<StageEvent['status'], Tone> = {
  completed: 'success',
  failed: 'danger',
  skipped: 'neutral',
  unavailable: 'neutral',
  pending: 'neutral',
  running: 'accent',
};

const STATUS_TEXT: Record<StageEvent['status'], string> = {
  completed: 'completed',
  failed: 'failed',
  skipped: 'skipped',
  unavailable: 'unavailable',
  pending: 'waiting',
  running: 'running',
};

export interface LiveFindingsProps {
  events: StageEvent[];
  isComplete: boolean;
}

/**
 * Real stage-completion events, as actually reported by the backend - each
 * entry is "this specialist finished (or failed/was skipped)", attributed
 * to the real agent, never a fabricated finding or a trace of model
 * reasoning.
 */
export function LiveFindings({ events, isComplete }: LiveFindingsProps) {
  const reduceMotion = useReducedMotion();

  return (
    <Card padding="none" className="overflow-hidden">
      <div className="flex items-center justify-between gap-4 border-b border-hairline px-5 py-4 md:px-6">
        <div>
          <CardTitle>Pipeline activity</CardTitle>
          <p className="mt-0.5 text-small text-ink-muted">
            {isComplete ? `${events.length} stages reported` : 'Updated as each specialist finishes'}
          </p>
        </div>
        <span className="numeric text-small text-ink-muted">{events.length}</span>
      </div>

      <div className="px-5 py-5 md:px-6">
        {events.length === 0 ? (
          <EmptyState
            size="inline"
            icon={Hourglass}
            title="Waiting on the first specialist"
            description="Stage updates appear here as each agent reports its status."
          />
        ) : (
          <ul className="space-y-3">
            <AnimatePresence initial={false}>
              {events.map((event) => (
                <motion.li
                  key={event.id}
                  layout={!reduceMotion}
                  initial={reduceMotion ? undefined : { opacity: 0, y: 8 }}
                  animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
                  transition={{ duration: DURATION.entrance, ease: EASE_OUT }}
                  className="flex gap-3 rounded-lg border border-hairline bg-surface-raised px-4 py-3"
                >
                  <span
                    className={cn('mt-1.5 size-2 shrink-0 rounded-full', toneFill[STATUS_TONE[event.status]])}
                    aria-hidden
                  />
                  <div className="min-w-0">
                    <p className="text-small text-ink">
                      {event.label} {STATUS_TEXT[event.status]}
                    </p>
                  </div>
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        )}
      </div>
    </Card>
  );
}
