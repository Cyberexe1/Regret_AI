import { FilterX, SquarePen } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button, buttonClasses } from '@/components/ui/Button';
import { ROUTES } from '@/data/navigation';
import { cn } from '@/lib/cn';

/** Nothing in the workspace yet. */
export function DecisionHistoryEmpty() {
  return (
    <div className="rounded-xl border border-hairline bg-surface px-6 py-16 text-center">
      <span className="mx-auto flex size-11 items-center justify-center rounded-lg border border-accent-line bg-accent-soft text-accent-ink">
        <SquarePen className="size-5" aria-hidden />
      </span>

      <h3 className="mt-5 text-section-title text-ink">
        Your first important decision starts here.
      </h3>
      <p className="mx-auto mt-3 max-w-md text-small text-ink-secondary">
        Describe a decision you are about to commit to, and the engine will find the assumptions it
        rests on and what would make it fail.
      </p>

      <Link
        to={ROUTES.newDecision}
        className={cn(buttonClasses({ variant: 'primary', size: 'md' }), 'mt-7')}
      >
        Stress-test a decision
      </Link>
    </div>
  );
}

export interface DecisionHistoryNoMatchesProps {
  onClear: () => void;
}

/** The workspace has decisions, but the current search or filter excludes them. */
export function DecisionHistoryNoMatches({ onClear }: DecisionHistoryNoMatchesProps) {
  return (
    <div className="rounded-xl border border-hairline bg-surface px-6 py-14 text-center">
      <span className="mx-auto flex size-10 items-center justify-center rounded-lg border border-hairline bg-surface-raised text-ink-muted">
        <FilterX className="size-4.5" aria-hidden />
      </span>

      <h3 className="mt-4 text-card-title text-ink">No decisions match this view</h3>
      <p className="mx-auto mt-2 max-w-sm text-small text-ink-secondary">
        Try a different risk band, or clear the search to see everything again.
      </p>

      <Button variant="secondary" size="sm" className="mt-6" onClick={onClear}>
        Clear filters
      </Button>
    </div>
  );
}
