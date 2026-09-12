import { Plus } from 'lucide-react';
import { Link } from 'react-router-dom';
import { buttonClasses } from '@/components/ui/Button';
import { ROUTES } from '@/data/navigation';
import { cn } from '@/lib/cn';
import { greeting } from '@/lib/format';

export interface DashboardHeaderProps {
  /** Injectable for deterministic rendering; defaults to now. */
  now?: Date;
}

export function DashboardHeader({ now }: DashboardHeaderProps) {
  return (
    <header className="flex min-w-0 flex-col gap-5 md:flex-row md:items-end md:justify-between md:gap-8">
      <div className="min-w-0">
        <p className="text-small text-ink-muted">{greeting(now)}</p>
        <h2 className="mt-1.5 break-words text-page-title text-ink">Your decisions</h2>
        <p className="mt-2.5 max-w-xl break-words text-body text-ink-secondary sm:mt-3">
          Stress-test important choices before they become expensive mistakes.
        </p>
      </div>

      <Link
        to={ROUTES.newDecision}
        className={cn(
          buttonClasses({ variant: 'primary', size: 'md' }),
          'w-full justify-center sm:w-auto sm:self-start md:shrink-0 md:self-auto',
        )}
      >
        <Plus className="size-4" aria-hidden />
        New Decision
      </Link>
    </header>
  );
}
