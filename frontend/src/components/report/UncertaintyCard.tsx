import { useId, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/cn';
import { confidenceLabel, confidenceTone, riskLabel, riskTone } from '@/lib/tone';
import type { CriticalUncertainty } from '@/types';

export interface UncertaintyCardProps {
  uncertainty: CriticalUncertainty;
  /** The top-ranked card starts open, since it drives the decision. */
  defaultOpen?: boolean;
}

function ValuePair({ label, value, emphasis }: { label: string; value: string; emphasis?: boolean }) {
  return (
    <div>
      <p className="eyebrow">{label}</p>
      <p
        className={cn(
          'numeric mt-1.5 text-card-title',
          emphasis ? 'text-accent-ink' : 'text-ink',
        )}
      >
        {value}
      </p>
    </div>
  );
}

export function UncertaintyCard({ uncertainty, defaultOpen = false }: UncertaintyCardProps) {
  const [open, setOpen] = useState(defaultOpen);
  const reduceMotion = useReducedMotion();
  const panelId = useId();

  return (
    <div className="overflow-hidden rounded-xl border border-hairline bg-surface">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls={panelId}
        className="w-full px-5 py-5 text-left transition-colors duration-150 hover:bg-surface-raised md:px-6"
      >
        <div className="flex items-start gap-4">
          <span className="numeric mt-0.5 shrink-0 text-micro text-ink-faint">
            {uncertainty.rank}
          </span>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
              <p className="text-card-title text-ink">{uncertainty.title}</p>
              <Badge tone={riskTone[uncertainty.impact]} size="sm">
                {riskLabel[uncertainty.impact]} impact
              </Badge>
              <Badge tone={confidenceTone[uncertainty.confidence]} size="sm" variant="outline">
                {confidenceLabel[uncertainty.confidence]} confidence
              </Badge>
            </div>

            <p className="mt-2 text-small text-ink-secondary">{uncertainty.summary}</p>

            <div className="mt-4 grid grid-cols-2 gap-4 sm:max-w-md">
              <ValuePair
                label={uncertainty.current.label}
                value={uncertainty.current.value}
              />
              <ValuePair
                label={uncertainty.threshold.label}
                value={uncertainty.threshold.value}
                emphasis
              />
            </div>
          </div>

          <ChevronDown
            className={cn(
              'mt-0.5 size-4 shrink-0 text-ink-muted transition-transform duration-200',
              open && 'rotate-180',
            )}
            aria-hidden
          />
        </div>
      </button>

      <AnimatePresence initial={false}>
        {open ? (
          <motion.div
            id={panelId}
            initial={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            animate={reduceMotion ? undefined : { height: 'auto', opacity: 1 }}
            exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="space-y-5 border-t border-hairline bg-surface-inset px-5 py-5 md:px-6">
              <div>
                <p className="eyebrow">Why it matters</p>
                <p className="mt-2 text-small text-ink-secondary">
                  {uncertainty.detail.whyItMatters}
                </p>
              </div>

              <div>
                <p className="eyebrow">Evidence on file</p>
                <ul className="mt-2 space-y-2">
                  {uncertainty.detail.evidence.map((line) => (
                    <li key={line} className="flex gap-2.5 text-small text-ink-secondary">
                      <span
                        className="mt-1.5 size-1.5 shrink-0 rounded-full bg-ink-faint"
                        aria-hidden
                      />
                      {line}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-lg border border-accent-line/60 bg-accent-soft/30 px-4 py-3">
                <p className="eyebrow">How to resolve it</p>
                <p className="mt-2 text-small text-ink-secondary">
                  {uncertainty.detail.howToResolve}
                </p>
              </div>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
