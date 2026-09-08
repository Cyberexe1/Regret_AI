import type { ReactNode } from 'react';
import { Reveal } from '@/components/Reveal';
import { cn } from '@/lib/cn';

export interface ReportSectionProps {
  /** Ordinal shown before the title, e.g. "02". */
  index?: string;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
  children: ReactNode;
}

/** Consistent heading block for each numbered part of the report. */
export function ReportSection({
  index,
  title,
  description,
  action,
  className,
  children,
}: ReportSectionProps) {
  return (
    <Reveal>
      <section className={cn('scroll-mt-24', className)}>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2.5">
              {index ? <span className="numeric text-micro text-ink-faint">{index}</span> : null}
              <h3 className="text-[1.1875rem] leading-snug font-semibold tracking-[-0.015em] text-ink">
                {title}
              </h3>
            </div>
            {description ? (
              <p className="mt-2 max-w-2xl text-small text-ink-secondary">{description}</p>
            ) : null}
          </div>
          {action ? <div className="shrink-0">{action}</div> : null}
        </div>

        <div className="mt-5">{children}</div>
      </section>
    </Reveal>
  );
}
