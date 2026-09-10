import { ArrowRight, CircleQuestionMark } from 'lucide-react';
import { Link } from 'react-router-dom';
import { buttonClasses } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { ROUTES } from '@/data/navigation';
import { cn } from '@/lib/cn';

export interface UncertaintyCardProps {
  /** Real decisions currently in the `needs_validation` state, if any. */
  needsValidationCount: number;
}

/**
 * The one card on the page that is deliberately not a plain surface: an
 * accent-tinted panel, because this is the thing the user should act on.
 * Shows a real count of decisions needing validation - never a fabricated
 * "top uncertainty" headline the backend doesn't compute.
 */
export function UncertaintyCard({ needsValidationCount }: UncertaintyCardProps) {
  return (
    <section className="flex h-full flex-col rounded-xl border border-accent-line bg-panel-accent p-6">
      <div className="flex items-center gap-2.5">
        <CircleQuestionMark className="size-4 shrink-0 text-accent-ink" aria-hidden />
        <p className="eyebrow">Needs validation</p>
      </div>

      {needsValidationCount > 0 ? (
        <>
          <h3 className="mt-4 text-section-title text-ink">
            {needsValidationCount} decision{needsValidationCount === 1 ? '' : 's'} awaiting validation
          </h3>
          <p className="mt-2.5 text-small text-ink-secondary">
            These decisions have a recommended experiment that hasn&apos;t been run yet.
          </p>
          <Link
            to={ROUTES.decisions}
            className={cn(buttonClasses({ variant: 'primary', size: 'sm' }), 'mt-6 self-start')}
          >
            Review
            <ArrowRight className="size-3.5" aria-hidden />
          </Link>
        </>
      ) : (
        <EmptyState
          size="inline"
          icon={CircleQuestionMark}
          title="Nothing needs validation"
          description="Every recommended experiment has been run, or none exist yet."
        />
      )}
    </section>
  );
}
