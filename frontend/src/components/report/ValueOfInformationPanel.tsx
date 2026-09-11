import { useId, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ChevronDown, Compass } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { cn } from '@/lib/cn';
import { toneFill } from '@/lib/tone';
import { DURATION, EASE_OUT } from '@/lib/motion';
import type { ValueOfInformationRow, ValueOfInformationSummary } from '@/types/report';

export interface ValueOfInformationPanelProps {
  summary: ValueOfInformationSummary;
  isLoading?: boolean;
}

/**
 * REGRET ENGINE 2.0's Value-of-Information Engine (Step 20): "WHAT
 * SHOULD YOU TEST FIRST?" - the ranked list of uncertainties, ordered by
 * practical value to resolve BEFORE committing, not by raw risk. This is
 * deliberately one of the most visually prominent parts of the report,
 * per the spec's own framing.
 *
 * Every row's bar length reflects only its own qualitative
 * `practical_value` band (see `buildValueOfInformation.ts`'s fixed,
 * documented percentage mapping) - never a fabricated precise score.
 * `confidencePercent`, when shown, is always labelled as "how much of
 * this score rests on real inputs," never a probability of success.
 */
export function ValueOfInformationPanel({ summary, isLoading = false }: ValueOfInformationPanelProps) {
  if (isLoading) {
    return (
      <EmptyState
        icon={Compass}
        title="Ranking uncertainties…"
        description="Working out which uncertainty is most worth resolving before you commit."
      />
    );
  }

  if (!summary.found || summary.ranked.length === 0) {
    return (
      <EmptyState
        icon={Compass}
        title="Nothing to prioritize yet"
        description="Once assumptions and blindspots have been identified for this decision, REGRET ENGINE will rank which one is most worth resolving first."
      />
    );
  }

  return (
    <div className="space-y-6">
      {summary.summary ? <p className="text-body text-ink-secondary">{summary.summary}</p> : null}

      <UncertaintyRankingBars rows={summary.ranked} />

      <div className="space-y-3">
        {summary.ranked.map((row, index) => (
          <ValueOfInformationRowCard
            key={row.uncertaintyId}
            row={row}
            isPrimary={row.uncertaintyId === summary.primaryUncertaintyId}
            defaultOpen={index === 0}
          />
        ))}
      </div>
    </div>
  );
}

/**
 * "WHAT MATTERS MOST?" - a compact, at-a-glance ranked bar list, kept
 * separate from the detailed cards below it so the prioritization order
 * is legible in a single glance before reading any rationale. Bar length
 * is the same fixed, documented `barPercent` mapping the detailed cards
 * use - never a second, inconsistent scale.
 */
function UncertaintyRankingBars({ rows }: { rows: ValueOfInformationRow[] }) {
  return (
    <div className="rounded-xl border border-hairline bg-surface-inset px-5 py-4 md:px-6">
      <p className="eyebrow">What matters most</p>
      <ul className="mt-3 space-y-2.5">
        {rows.map((row) => (
          <li key={row.uncertaintyId} className="flex items-center gap-3">
            <span className="numeric w-5 shrink-0 text-micro text-ink-muted">{row.rank}</span>
            <span className="w-40 shrink-0 truncate text-small text-ink sm:w-56">{row.title}</span>
            <div className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-hairline">
              <div
                className={cn('h-full rounded-full', toneFill[row.practicalValueTone])}
                style={{ width: `${row.barPercent}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ValueOfInformationRowCard({
  row,
  isPrimary,
  defaultOpen,
}: {
  row: ValueOfInformationRow;
  isPrimary: boolean;
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const reduceMotion = useReducedMotion();
  const panelId = useId();

  return (
    <Card
      variant={isPrimary ? 'raised' : 'default'}
      padding="none"
      className={cn('overflow-hidden', isPrimary && 'border-accent-line')}
    >
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls={panelId}
        className="w-full px-5 py-5 text-left transition-colors duration-150 hover:bg-surface-raised md:px-6"
      >
        <div className="flex items-start gap-4">
          <span className="numeric mt-0.5 shrink-0 text-micro text-ink-muted">{row.rank}</span>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
              <p className="text-card-title text-ink">{row.title}</p>
              {isPrimary ? (
                <Badge tone="accent" size="sm">
                  Test this first
                </Badge>
              ) : null}
              <Badge tone={row.practicalValueTone} size="sm">
                {row.practicalValueLabel} practical value
              </Badge>
            </div>

            <div className="mt-3">
              <div className="h-2 w-full overflow-hidden rounded-full bg-hairline">
                <div
                  className={cn('h-full rounded-full transition-[width] duration-500', toneFill[row.practicalValueTone])}
                  style={{ width: `${row.barPercent}%` }}
                />
              </div>
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
            transition={{ duration: DURATION.quick, ease: EASE_OUT }}
            className="overflow-hidden"
          >
            <div className="space-y-4 border-t border-hairline bg-surface-inset px-5 py-5 md:px-6">
              <div>
                <p className="eyebrow">Why it matters</p>
                <p className="mt-2 text-small text-ink-secondary">{row.rationale}</p>
              </div>

              <div>
                <p className="eyebrow">Required threshold</p>
                <p className="mt-2 text-small text-ink-secondary">{row.thresholdStatusLabel}</p>
              </div>

              <dl className="grid grid-cols-2 gap-3 border-t border-hairline pt-4 sm:grid-cols-4">
                <div>
                  <dt className="text-micro text-ink-muted">Cost to learn</dt>
                  <dd className="mt-1 text-small font-medium text-ink">{row.costLabel}</dd>
                </div>
                <div>
                  <dt className="text-micro text-ink-muted">Test duration</dt>
                  <dd className="mt-1 text-small font-medium text-ink">{row.durationLabel ?? 'Unknown'}</dd>
                </div>
                <div>
                  <dt className="text-micro text-ink-muted">Feasibility</dt>
                  <dd className="mt-1 text-small font-medium text-ink">{row.feasibilityLabel}</dd>
                </div>
                <div>
                  <dt className="text-micro text-ink-muted">Reversibility</dt>
                  <dd className="mt-1 text-small font-medium text-ink">{row.reversibilityLabel}</dd>
                </div>
              </dl>

              {row.historicalRelevanceLabel ? (
                <p className="border-t border-hairline pt-3 text-micro text-ink-muted">
                  {row.historicalRelevanceLabel}
                </p>
              ) : null}

              {row.crossDecisionSignalLabel ? (
                <p className="border-t border-hairline pt-3 text-micro text-ink-muted">
                  Recurring pattern: {row.crossDecisionSignalLabel}
                </p>
              ) : null}

              <p className="text-micro text-ink-muted">
                Confidence in this score: {row.confidencePercent}% (how much of it rests on real,
                recorded inputs - not a probability of a favorable outcome)
              </p>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </Card>
  );
}
