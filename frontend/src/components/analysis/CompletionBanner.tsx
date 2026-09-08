import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ArrowRight, CircleCheck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { buttonClasses } from '@/components/ui/Button';
import { decisionPath } from '@/data/navigation';
import { DEMO_DECISION_ALIAS } from '@/data/decisions';
import { cn } from '@/lib/cn';
import { DURATION, EASE_OUT } from '@/lib/motion';

export interface CompletionBannerProps {
  isComplete: boolean;
  findingCount: number;
}

export function CompletionBanner({ isComplete, findingCount }: CompletionBannerProps) {
  const reduceMotion = useReducedMotion();

  return (
    <AnimatePresence>
      {isComplete ? (
        <motion.section
          initial={reduceMotion ? undefined : { opacity: 0, y: 12 }}
          animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
          exit={reduceMotion ? undefined : { opacity: 0 }}
          transition={{ duration: DURATION.entrance, ease: EASE_OUT }}
          className="flex flex-col gap-5 rounded-xl border border-success-line bg-panel-success p-6 md:flex-row md:items-center md:justify-between md:p-7"
        >
          <div className="flex min-w-0 gap-3.5">
            <CircleCheck className="mt-0.5 size-5 shrink-0 text-success-ink" aria-hidden />
            <div className="min-w-0">
              <h2 className="text-section-title text-ink">Stress test complete</h2>
              <p className="mt-1.5 text-small text-ink-secondary">
                {findingCount} findings, one failure threshold and a recommended experiment are
                ready to review.
              </p>
            </div>
          </div>

          <Link
            to={decisionPath(DEMO_DECISION_ALIAS)}
            className={cn(buttonClasses({ variant: 'primary', size: 'lg' }), 'shrink-0')}
          >
            View Decision Report
            <ArrowRight className="size-4.5" aria-hidden />
          </Link>
        </motion.section>
      ) : null}
    </AnimatePresence>
  );
}
