import { useId, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/cn';
import type { CriticalUncertainty } from '@/types/report';
import { DURATION, EASE_OUT } from '@/lib/motion';

export interface UncertaintyCardProps {
  uncertainty: CriticalUncertainty;
  /** The top-ranked card starts open, since it drives the decision. */
  defaultOpen?: boolean;
}

export function UncertaintyCard({ uncertainty, defaultOpen = false }: UncertaintyCardProps) {
  const [open, setOpen] = useState(defaultOpen);
  const reduceMotion = useReducedMotion();
  const panelId = useId();

  const hasDetail = Boolean(
    uncertainty.whyItMatters || uncertainty.failureConsequence || uncertainty.evidenceGap || uncertainty.reason,
  );

  return (
    <div className="overflow-hidden rounded-xl border border-hairline bg-surface">
      <button
        type="button"
        onClick={() => hasDetail && setOpen((value) => !value)}
        aria-expanded={hasDetail ? open : undefined}
        aria-controls={hasDetail ? panelId : undefined}
        className={cn(
          'w-full px-5 py-5 text-left transition-colors duration-150 md:px-6',
          hasDetail && 'hover:bg-surface-raised',
        )}
      >
        <div className="flex items-start gap-4">
          <span className="numeric mt-0.5 shrink-0 text-micro text-ink-muted">{uncertainty.rank}</span>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
              <p className="text-card-title text-ink">{uncertainty.title}</p>
              <Badge tone="neutral" size="sm" variant="outline">
                {uncertainty.kind === 'assumption' ? 'Assumption' : 'Blindspot'}
              </Badge>
              <Badge tone={uncertainty.importanceTone} size="sm">
                {uncertainty.importanceLabel} importance
              </Badge>
              <Badge tone={uncertainty.confidenceTone} size="sm" variant="outline">
                {uncertainty.confidenceLabel} confidence
              </Badge>
            </div>

            <div className="mt-3">
              <Badge tone={uncertainty.evidenceStatusTone} size="sm" dot>
                {uncertainty.evidenceStatusLabel}
              </Badge>
            </div>
          </div>

          {hasDetail ? (
            <ChevronDown
              className={cn(
                'mt-0.5 size-4 shrink-0 text-ink-muted transition-transform duration-200',
                open && 'rotate-180',
              )}
              aria-hidden
            />
          ) : null}
        </div>
      </button>

      <AnimatePresence initial={false}>
        {open && hasDetail ? (
          <motion.div
            id={panelId}
            initial={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            animate={reduceMotion ? undefined : { height: 'auto', opacity: 1 }}
            exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            transition={{ duration: DURATION.quick, ease: EASE_OUT }}
            className="overflow-hidden"
          >
            <div className="space-y-5 border-t border-hairline bg-surface-inset px-5 py-5 md:px-6">
              {uncertainty.whyItMatters ? (
                <div>
                  <p className="eyebrow">Why it matters</p>
                  <p className="mt-2 text-small text-ink-secondary">{uncertainty.whyItMatters}</p>
                </div>
              ) : null}

              {uncertainty.failureConsequence ? (
                <div>
                  <p className="eyebrow">If this assumption is wrong</p>
                  <p className="mt-2 text-small text-ink-secondary">{uncertainty.failureConsequence}</p>
                </div>
              ) : null}

              {uncertainty.evidenceGap ? (
                <div className="rounded-lg border border-warning-line bg-panel-warning px-4 py-3">
                  <p className="eyebrow">Evidence gap</p>
                  <p className="mt-2 text-small text-ink-secondary">{uncertainty.evidenceGap}</p>
                </div>
              ) : null}

              {uncertainty.reason ? (
                <div>
                  <p className="eyebrow">Basis</p>
                  <p className="mt-2 text-small text-ink-secondary">{uncertainty.reason}</p>
                </div>
              ) : null}
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
