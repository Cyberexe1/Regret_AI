import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';
import { Reveal } from './Reveal';

/** Shared horizontal container for every landing band, including nav and footer. */
export const LANDING_CONTAINER = 'mx-auto w-full max-w-[76rem] px-[var(--page-gutter)]';

export interface LandingSectionProps {
  /** Anchor target for the navigation. */
  id?: string;
  eyebrow?: string;
  title?: string;
  lead?: string;
  align?: 'left' | 'center';
  /** Adds a hairline above the section to separate bands. */
  bordered?: boolean;
  className?: string;
  children?: ReactNode;
}

export function LandingSection({
  id,
  eyebrow,
  title,
  lead,
  align = 'left',
  bordered = false,
  className,
  children,
}: LandingSectionProps) {
  const hasHeader = Boolean(eyebrow || title || lead);
  const centered = align === 'center';

  return (
    <section
      id={id}
      className={cn(
        'scroll-mt-[calc(var(--topbar-height)+1rem)] py-20 md:py-28',
        bordered && 'border-t border-hairline',
        className,
      )}
    >
      <div className={LANDING_CONTAINER}>
        {hasHeader ? (
          <Reveal className={cn('mb-12 md:mb-16', centered && 'text-center')}>
            {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
            {title ? (
              <h2
                className={cn(
                  'mt-4 text-page-title text-ink',
                  centered ? 'mx-auto max-w-3xl' : 'max-w-3xl',
                )}
              >
                {title}
              </h2>
            ) : null}
            {lead ? (
              <p
                className={cn(
                  'mt-4 text-body text-ink-secondary',
                  centered ? 'mx-auto max-w-2xl' : 'max-w-2xl',
                )}
              >
                {lead}
              </p>
            ) : null}
          </Reveal>
        ) : null}

        {children}
      </div>
    </section>
  );
}
