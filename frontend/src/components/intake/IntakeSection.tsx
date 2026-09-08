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
  /** The opening section carries the largest heading. */
  emphasis?: boolean;
  delay?: number;
  children: ReactNode;
}

export function IntakeSection({
  id,
  phase,
  title,
  description,
  emphasis = false,
  delay = 0,
  children,
}: IntakeSectionProps) {
  return (
    <Reveal delay={delay}>
      <section
        id={id}
        aria-labelledby={`${id}-title`}
        className="scroll-mt-[calc(var(--topbar-height)+1.5rem)] rounded-xl border border-hairline bg-surface p-6 md:p-8"
      >
        <p className="eyebrow">{phase}</p>

        <h2
          id={`${id}-title`}
          className={cn(
            'mt-3 font-semibold tracking-[-0.015em] text-ink',
            emphasis ? 'text-[1.375rem] leading-snug' : 'text-[1.1875rem] leading-snug',
          )}
        >
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
