import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ArrowRight, CircleCheck, Info } from 'lucide-react';
import { Link } from 'react-router-dom';
import { buttonClasses } from '@/components/ui/Button';
import { decisionPath } from '@/data/navigation';
import { DEMO_DECISION_ALIAS } from '@/data/decisions';
import { cn } from '@/lib/cn';
import { DURATION, EASE_OUT } from '@/lib/motion';

export interface CompletionBannerProps {
  isComplete: boolean;
  findingCount: number;
  /**
   * True when the decision text being analysed is the seeded sample (the
   * cloud kitchen decision), which is the only one with a hand-authored full
   * report and dependency graph. Everything else in this prototype has no
   * backend behind it, so the report link would otherwise land the user on
   * unrelated numbers for their own decision. When false, the CTA is
   * relabelled and captioned so that hand-off is honest rather than silent.
   */
  isSampleDecision: boolean;
}

export function CompletionBanner({
  isComplete,
  findingCount,
  isSampleDecision,
}: CompletionBannerProps) {
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
              {isSampleDecision ? null : (
                <p className="mt-2 flex items-start gap-1.5 text-small text-ink-muted">
                  <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                  This prototype has one fully worked example report. It walks through a
                  different decision (a cloud kitchen investment) so you can see the full
                  format the report would take for yours.
                </p>
              )}
            </div>
          </div>

          <Link
            to={decisionPath(DEMO_DECISION_ALIAS)}
            className={cn(buttonClasses({ variant: 'primary', size: 'lg' }), 'shrink-0')}
          >
            {isSampleDecision ? 'View Decision Report' : 'View Example Report'}
            <ArrowRight className="size-4.5" aria-hidden />
          </Link>
        </motion.section>
      ) : null}
    </AnimatePresence>
  );
}
