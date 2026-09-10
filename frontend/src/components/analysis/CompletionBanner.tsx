import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ArrowRight, CircleCheck, RotateCcw, TriangleAlert } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button, buttonClasses } from '@/components/ui/Button';
import { decisionPath } from '@/data/navigation';
import { cn } from '@/lib/cn';
import { DURATION, EASE_OUT } from '@/lib/motion';

export interface CompletionBannerProps {
  isComplete: boolean;
  hasFailed: boolean;
  decisionId: string;
  errorMessage?: string | null;
  onRetry?: () => void;
}

export function CompletionBanner({
  isComplete,
  hasFailed,
  decisionId,
  errorMessage,
  onRetry,
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
          className={cn(
            'flex flex-col gap-5 rounded-xl border p-6 md:flex-row md:items-center md:justify-between md:p-7',
            hasFailed
              ? 'border-danger-line bg-panel-danger'
              : 'border-success-line bg-panel-success',
          )}
        >
          <div className="flex min-w-0 gap-3.5">
            {hasFailed ? (
              <TriangleAlert className="mt-0.5 size-5 shrink-0 text-danger-ink" aria-hidden />
            ) : (
              <CircleCheck className="mt-0.5 size-5 shrink-0 text-success-ink" aria-hidden />
            )}
            <div className="min-w-0">
              <h2 className="text-section-title text-ink">
                {hasFailed ? 'Analysis could not be completed' : 'Stress test complete'}
              </h2>
              <p className="mt-1.5 text-small text-ink-secondary">
                {hasFailed
                  ? errorMessage ?? 'The analysis run failed. You can retry from the decision report.'
                  : 'Assumptions, uncertainties, thresholds and a recommended experiment are ready to review.'}
              </p>
            </div>
          </div>

          {hasFailed ? (
            onRetry ? (
              <Button
                variant="secondary"
                size="lg"
                leftIcon={RotateCcw}
                onClick={onRetry}
                className="shrink-0"
              >
                Retry analysis
              </Button>
            ) : null
          ) : (
            <Link
              to={decisionPath(decisionId)}
              className={cn(buttonClasses({ variant: 'primary', size: 'lg' }), 'shrink-0')}
            >
              View Decision Report
              <ArrowRight className="size-4.5" aria-hidden />
            </Link>
          )}
        </motion.section>
      ) : null}
    </AnimatePresence>
  );
}
