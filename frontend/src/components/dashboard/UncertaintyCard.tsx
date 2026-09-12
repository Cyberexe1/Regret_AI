import { ArrowRight, ClipboardCheck } from 'lucide-react';
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
    <section className="flex h-full min-w-0 flex-col overflow-hidden rounded-xl border border-accent-line bg-panel-accent p-5 sm:p-6">
      <div className="flex min-w-0 items-center gap-2.5">
        <ClipboardCheck className="size-4 shrink-0 text-accent-ink" aria-hidden />
        <p className="eyebrow min-w-0 break-words">Needs validation</p>
      </div>

      {needsValidationCount > 0 ? (
        <>
          <h3 className="mt-4 break-words text-section-title text-ink">
            {needsValidationCount} decision{needsValidationCount === 1 ? '' : 's'} awaiting validation
          </h3>
          <p className="mt-2.5 break-words text-small text-ink-secondary">
            These decisions have a recommended experiment that hasn&apos;t been run yet.
          </p>
          <Link
            to={ROUTES.decisions}
            className={cn(
              buttonClasses({ variant: 'primary', size: 'sm' }),
              'mt-6 max-w-full self-start',
            )}
          >
            Review
            <ArrowRight className="size-3.5 shrink-0" aria-hidden />
          </Link>
        </>
      ) : (
        <EmptyState
          size="inline"
          icon={ClipboardCheck}
          title="Nothing needs validation"
          description="Every recommended experiment has been run, or none exist yet."
        />
      )}
    </section>
  );
}
