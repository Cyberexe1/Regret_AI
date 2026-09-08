import { Plus } from 'lucide-react';
import { Link } from 'react-router-dom';
import { buttonClasses } from '@/components/ui/Button';
import { ROUTES } from '@/data/navigation';
import { greeting } from '@/lib/format';

export interface DashboardHeaderProps {
  /** Injectable for deterministic rendering; defaults to now. */
  now?: Date;
}

export function DashboardHeader({ now }: DashboardHeaderProps) {
  return (
    <header className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
      <div className="min-w-0">
        <p className="text-small text-ink-muted">{greeting(now)}</p>
        <h2 className="mt-1.5 text-page-title text-ink">Your decisions</h2>
        <p className="mt-3 max-w-xl text-body text-ink-secondary">
          Stress-test important choices before they become expensive mistakes.
        </p>
      </div>

      <Link
        to={ROUTES.newDecision}
        className={buttonClasses({ variant: 'primary', size: 'md' })}
      >
        <Plus className="size-4" aria-hidden />
        New Decision
      </Link>
    </header>
  );
}
