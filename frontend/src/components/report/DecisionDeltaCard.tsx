import { ArrowRight, Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { cn } from '@/lib/cn';
import { toneText } from '@/lib/tone';
import type { EvolutionEventRow } from '@/types/report';

export interface DecisionDeltaCardProps {
  event: EvolutionEventRow;
}

/**
 * "WHAT CHANGED?" - the reusable card answering exactly that question
 * for one specific evolution event: before, after, the trigger, and the
 * evidence behind it. Every field is copied straight from the real
 * `DecisionEvolutionEvent` this card was built from - nothing here is a
 * second, re-derived narrative.
 *
 * Renders nothing meaningful (returns `null`) for an event with no real
 * before/after transition - "What changed?" is only shown when
 * something genuinely did.
 */
export function DecisionDeltaCard({ event }: DecisionDeltaCardProps) {
  if (event.previousStateLabel === null || event.newStateLabel === null) {
    return null;
  }

  return (
    <Card variant="raised" className="border-accent-line">
      <div className="flex items-center gap-2.5">
        <Sparkles className="size-4 shrink-0 text-accent-ink" aria-hidden />
        <p className="eyebrow">What changed?</p>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="text-micro text-ink-muted">Before</p>
          <p className="mt-1 text-card-title text-ink-secondary line-through">
            {event.previousStateLabel}
          </p>
        </div>
        <div>
          <p className="text-micro text-ink-muted">After</p>
          <p className={cn('mt-1 text-card-title font-semibold', toneText.accent)}>
            {event.newStateLabel}
          </p>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-center gap-2 text-ink-muted sm:hidden">
        <ArrowRight className="size-4" aria-hidden />
      </div>

      <div className="mt-4 border-t border-hairline pt-4">
        <p className="text-micro text-ink-muted">Trigger</p>
        <p className="mt-1 text-small text-ink">{event.title}</p>
      </div>

      {event.reason ? (
        <div className="mt-3">
          <p className="text-micro text-ink-muted">Evidence</p>
          <p className="mt-1 text-small text-ink-secondary">{event.reason}</p>
        </div>
      ) : null}

      {event.affectedThresholdIds.length > 0 || event.affectedAssumptionIds.length > 0 ? (
        <div className="mt-4 flex flex-wrap gap-2 border-t border-hairline pt-3">
          {event.affectedThresholdIds.length > 0 ? (
            <Badge tone="neutral" size="sm" variant="outline">
              {event.affectedThresholdIds.length} threshold(s) affected
            </Badge>
          ) : null}
          {event.affectedAssumptionIds.length > 0 ? (
            <Badge tone="neutral" size="sm" variant="outline">
              {event.affectedAssumptionIds.length} assumption(s) affected
            </Badge>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}
