import { motion, useReducedMotion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button, buttonClasses } from '@/components/ui/Button';
import { ROUTES } from '@/data/navigation';
import { cn } from '@/lib/cn';
import { DURATION, EASE_OUT } from '@/lib/motion';

export interface IntakeActionBarProps {
  id: string;
  canSubmit: boolean;
  onSubmit: () => void;
  /** True while the decision is being created / evidence is uploading. */
  submitting?: boolean;
}

/**
 * Pinned to the bottom of the viewport while the form is in view, so the commit
 * action is always reachable without hunting for it.
 */
export function IntakeActionBar({ id, canSubmit, onSubmit, submitting = false }: IntakeActionBarProps) {
  const reduceMotion = useReducedMotion();

  return (
    <div
      id={id}
      className="glass sticky bottom-0 z-10 -mx-[var(--page-gutter)] scroll-mt-[calc(var(--header-offset)+0.75rem)] border-t border-hairline px-[var(--page-gutter)] py-4"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="order-2 text-small text-ink-muted sm:order-1">
          {submitting
            ? 'Submitting your decision…'
            : canSubmit
              ? 'Ready. Everything else can be added after the first pass.'
              : 'Describe the decision to begin the stress test.'}
        </p>

        <div className="order-1 flex items-center gap-3 sm:order-2">
          <Link
            to={ROUTES.dashboard}
            className={cn(buttonClasses({ variant: 'ghost', size: 'md' }), 'shrink-0')}
          >
            Cancel
          </Link>

          <motion.div
            animate={reduceMotion ? undefined : { opacity: canSubmit ? 1 : 0.55 }}
            transition={{ duration: DURATION.quick, ease: EASE_OUT }}
            className="flex-1 sm:flex-none"
          >
            <Button
              variant="primary"
              size="md"
              fullWidth
              rightIcon={submitting ? undefined : ArrowRight}
              loading={submitting}
              disabled={!canSubmit}
              onClick={onSubmit}
            >
              Start Stress Test
            </Button>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
