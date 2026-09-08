import type { ReactNode } from 'react';
import { TriangleAlert } from 'lucide-react';
import { cn } from '@/lib/cn';

export interface ErrorStateProps {
  title: string;
  description?: string;
  /** Technical detail, shown small and muted. Omit for expected failures. */
  detail?: string;
  action?: ReactNode;
  size?: 'inline' | 'panel';
  className?: string;
}

/**
 * Shown when something failed rather than merely being absent. Kept visually
 * distinct from `EmptyState` so the two are never confused.
 */
export function ErrorState({
  title,
  description,
  detail,
  action,
  size = 'panel',
  className,
}: ErrorStateProps) {
  const isPanel = size === 'panel';

  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-center text-center',
        isPanel ? 'rounded-xl border border-danger-line bg-panel-danger px-6 py-12' : 'px-4 py-8',
        className,
      )}
    >
      <span className="flex size-10 items-center justify-center rounded-lg border border-danger-line bg-danger-soft text-danger-ink">
        <TriangleAlert className="size-4.5" aria-hidden />
      </span>

      <h3 className={cn('mt-4 text-ink', isPanel ? 'text-section-title' : 'text-card-title')}>
        {title}
      </h3>

      {description ? (
        <p className="mt-2 max-w-md text-small text-ink-secondary">{description}</p>
      ) : null}

      {detail ? (
        <p className="numeric mt-3 max-w-md truncate text-micro text-ink-muted">{detail}</p>
      ) : null}

      {action ? <div className="mt-6">{action}</div> : null}
    </div>
  );
}
