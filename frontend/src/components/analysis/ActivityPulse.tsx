import { motion, useReducedMotion } from 'framer-motion';
import { cn } from '@/lib/cn';

export interface ActivityPulseProps {
  className?: string;
}

/** Three staggered dots: the only motion that says "working right now". */
export function ActivityPulse({ className }: ActivityPulseProps) {
  const reduceMotion = useReducedMotion();

  return (
    <span className={cn('inline-flex items-center gap-1', className)} aria-hidden>
      {[0, 1, 2].map((dot) => (
        <motion.span
          key={dot}
          className="size-1 rounded-full bg-accent-ink"
          animate={reduceMotion ? { opacity: 0.7 } : { opacity: [0.25, 1, 0.25] }}
          transition={
            reduceMotion
              ? undefined
              : { duration: 1.1, repeat: Infinity, delay: dot * 0.18, ease: 'easeInOut' }
          }
        />
      ))}
    </span>
  );
}
