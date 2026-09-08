import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

export type PageWidth = 'default' | 'narrow' | 'wide';

const WIDTH: Record<PageWidth, string> = {
  narrow: 'max-w-3xl',
  default: 'max-w-[var(--page-max-width)]',
  wide: 'max-w-none',
};

export interface PageContainerProps {
  /** Small uppercase label above the page title. */
  eyebrow?: string;
  title?: string;
  description?: string;
  /** Right-aligned actions for the page header. */
  actions?: ReactNode;
  width?: PageWidth;
  className?: string;
  children?: ReactNode;
}

/**
 * Owns page gutters, max width and the title block, so pages only supply
 * content and never re-implement layout spacing.
 */
export function PageContainer({
  eyebrow,
  title,
  description,
  actions,
  width = 'default',
  className,
  children,
}: PageContainerProps) {
  const hasHeader = Boolean(eyebrow || title || description || actions);

  return (
    <div className={cn('mx-auto w-full px-[var(--page-gutter)] py-6 md:py-8', WIDTH[width], className)}>
      {hasHeader ? (
        <header className="mb-6 flex flex-col gap-4 md:mb-8 md:flex-row md:items-end md:justify-between">
          <div className="min-w-0 space-y-2">
            {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
            {title ? <h2 className="text-page-title text-ink">{title}</h2> : null}
            {description ? (
              <p className="max-w-2xl text-body text-ink-secondary">{description}</p>
            ) : null}
          </div>
          {actions ? <div className="flex shrink-0 flex-wrap items-center gap-3">{actions}</div> : null}
        </header>
      ) : null}

      {children}
    </div>
  );
}
