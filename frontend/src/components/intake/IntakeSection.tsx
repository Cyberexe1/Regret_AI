import type { ReactNode } from 'react';
import { Reveal } from '@/components/Reveal';
import { cn } from '@/lib/cn';

export interface IntakeSectionProps {
  /** Scroll target for the progress rail. */
  id: string;
  /** Phase tag, e.g. "01 · Decision". */
  phase: string;
  title: string;
  description?: ReactNode;
  delay?: number;
  /** Extra classes on the outer `<section>` - layout concerns only
   * (e.g. horizontal inset), never a re-styling escape hatch. */
  className?: string;
  children: ReactNode;
}

export function IntakeSection({
  id,
  phase,
  title,
  description,
  delay = 0,
  className,
  children,
}: IntakeSectionProps) {
  return (
    <Reveal delay={delay}>
      <section
        id={id}
        aria-labelledby={`${id}-title`}
        className={cn(
          'scroll-mt-[calc(var(--header-offset)+0.75rem)] rounded-xl border border-hairline bg-surface p-6 md:p-8',
          className,
        )}
      >
        <p className="eyebrow">{phase}</p>

        <h2 id={`${id}-title`} className="mt-3 text-subsection text-ink">
          {title}
        </h2>

        {description ? (
          <p className="mt-2.5 max-w-2xl text-small text-ink-secondary">{description}</p>
        ) : null}

        <div className="mt-6">{children}</div>
      </section>
    </Reveal>
  );
}
