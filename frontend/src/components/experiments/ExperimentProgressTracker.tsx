import { motion, useReducedMotion } from 'framer-motion';
import { Check } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { cn } from '@/lib/cn';
import type { ExperimentDetail } from '@/types';

export interface ExperimentProgressTrackerProps {
  detail: ExperimentDetail;
}

export function ExperimentProgressTracker({ detail }: ExperimentProgressTrackerProps) {
  const reduceMotion = useReducedMotion();
  const { currentDay, durationDays, progress, milestones } = detail;

  const positionOf = (day: number) => (day / durationDays) * 100;

  return (
    <Card>
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2">
        <div>
          <p className="eyebrow">Elapsed</p>
          <p className="mt-1.5 flex items-baseline gap-1.5">
            <span className="numeric text-xl font-semibold text-ink">Day {currentDay}</span>
            <span className="text-small text-ink-muted">of {durationDays}</span>
          </p>
        </div>
        <p className="numeric text-xl font-semibold text-accent-ink">{progress}%</p>
      </div>

      {/* Track. The current-day marker sits at the same scale as the fill. */}
      <div className="relative mt-8 mb-3">
        <motion.div
          className="absolute -top-7 z-10 -translate-x-1/2"
          initial={reduceMotion ? undefined : { left: '0%', opacity: 0 }}
          animate={{ left: `${progress}%`, opacity: 1 }}
          transition={{ duration: 0.9, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
        >
          <span className="numeric rounded-sm border border-accent-line bg-accent-soft px-1.5 py-0.5 text-micro text-accent-ink">
            Day {currentDay}
          </span>
        </motion.div>

        <div className="h-2 w-full overflow-hidden rounded-full bg-surface-inset">
          <motion.div
            className="h-full rounded-full bg-accent"
            initial={reduceMotion ? undefined : { width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.9, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          />
        </div>

        {milestones.map((day) => (
          <span
            key={day}
            className={cn(
              'absolute top-1/2 size-2 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-surface',
              day <= currentDay ? 'bg-accent-ink' : 'bg-ink-faint',
            )}
            style={{ left: `${positionOf(day)}%` }}
            aria-hidden
          />
        ))}
      </div>

      <ol className="mt-5 grid grid-cols-4 gap-2 border-t border-hairline pt-4">
        {milestones.map((day) => {
          const reached = day <= currentDay;

          return (
            <li key={day} className="flex items-center gap-1.5">
              {reached ? (
                <Check className="size-3.5 shrink-0 text-accent-ink" aria-hidden />
              ) : (
                <span className="size-1.5 shrink-0 rounded-full bg-ink-faint" aria-hidden />
              )}
              <span
                className={cn(
                  'numeric truncate text-small',
                  reached ? 'text-ink' : 'text-ink-muted',
                )}
              >
                Day {day}
              </span>
            </li>
          );
        })}
      </ol>
    </Card>
  );
}
