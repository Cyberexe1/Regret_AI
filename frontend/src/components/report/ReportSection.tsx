import { useId, useState, type ReactNode } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { cn } from '@/lib/cn';
import { DURATION, EASE_OUT } from '@/lib/motion';

export interface ReportSectionProps {
  /** Scroll target for the report's jump-nav - see `ReportNav`. Optional
   * only because a handful of report blocks (e.g. the actions bar) never
   * need to be a jump target. */
  id?: string;
  /** Ordinal shown before the title, e.g. "02". */
  index?: string;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
  /** Starts expanded when true. Defaults to false so the report reads
   * as a scannable list of section titles first - a long decision
   * report used to render all 13 sections fully expanded at once, which
   * is what made it hard to grab onto. Callers still decide per-section
   * (e.g. the cheap "Decision snapshot" metrics stay open by default). */
  defaultOpen?: boolean;
  children: ReactNode;
}

/** Consistent, collapsible heading block for each numbered part of the
 * report. The header (index/title/description/action) is always
 * visible; only `children` collapses, so a user can always see WHAT a
 * section is about before deciding whether to open it. */
export function ReportSection({
  id,
  index,
  title,
  description,
  action,
  className,
  defaultOpen = false,
  children,
}: ReportSectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  const reduceMotion = useReducedMotion();
  const panelId = useId();

  return (
    <Reveal>
      <section id={id} className={cn('scroll-mt-[calc(var(--header-offset)+0.75rem)]', className)}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            aria-controls={panelId}
            className="group flex min-w-0 flex-1 items-start gap-3 rounded-sm text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          >
            <ChevronDown
              className={cn(
                'mt-1.5 size-4 shrink-0 text-ink-muted transition-transform duration-200 group-hover:text-ink-secondary',
                open && 'rotate-180',
              )}
              aria-hidden
            />
            <div className="min-w-0">
              <div className="flex items-center gap-2.5">
                {index ? <span className="numeric text-micro text-ink-muted">{index}</span> : null}
                <h3 className="text-subsection text-ink">{title}</h3>
              </div>
              {description ? (
                <p className="mt-2 max-w-2xl text-small text-ink-secondary">{description}</p>
              ) : null}
            </div>
          </button>

          {action ? <div className="shrink-0">{action}</div> : null}
        </div>

        <AnimatePresence initial={false}>
          {open ? (
            <motion.div
              id={panelId}
              initial={reduceMotion ? undefined : { height: 0, opacity: 0 }}
              animate={reduceMotion ? undefined : { height: 'auto', opacity: 1 }}
              exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
              transition={{ duration: DURATION.quick, ease: EASE_OUT }}
              className="overflow-hidden"
            >
              <div className="mt-5">{children}</div>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </section>
    </Reveal>
  );
}
