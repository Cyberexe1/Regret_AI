import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/cn';

export type EmptyStateSize = 'inline' | 'panel';

export interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  /** Action row, usually a single button or link. */
  action?: ReactNode;
  /**
   * `inline` sits inside an existing card; `panel` draws its own bordered
   * surface for a whole-page or whole-section vacancy.
   */
  size?: EmptyStateSize;
  className?: string;
}

/**
 * One empty state for the product. Every vacancy reads the same way: what is
 * missing, why, and the single thing you can do about it.
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  size = 'panel',
  className,
}: EmptyStateProps) {
  const isPanel = size === 'panel';

  return (
    <div
      className={cn(
        'flex flex-col items-center text-center',
        isPanel ? 'rounded-xl border border-hairline bg-surface px-6 py-14' : 'px-4 py-10',
        className,
      )}
    >
      <span
        className={cn(
          'flex items-center justify-center rounded-lg border border-hairline bg-surface-raised text-ink-muted',
          isPanel ? 'size-11' : 'size-9',
        )}
      >
        <Icon className={isPanel ? 'size-5' : 'size-4'} aria-hidden />
      </span>

      <h3 className={cn('mt-4 text-ink', isPanel ? 'text-section-title' : 'text-card-title')}>
        {title}
      </h3>

      {description ? (
        <p className="mt-2 max-w-md text-small text-ink-secondary">{description}</p>
      ) : null}

      {action ? <div className="mt-6">{action}</div> : null}
    </div>
  );
}
