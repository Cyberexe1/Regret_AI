import { useState } from 'react';
import { Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { decisionCategoryLabel, exampleDecisions, type ExampleDecision } from '@/data/decisionTypes';

export interface ExampleDecisionPickerProps {
  onSelect: (example: ExampleDecision) => void;
}

/** Shown collapsed by default - "Load more" reveals the rest so this
 * never pushes the actual decision field further down the page than
 * it needs to. */
const INITIAL_VISIBLE_COUNT = 3;

/**
 * "Explore example decisions" (Step 25 sections 13/15) - clicking a card
 * populates the real intake form with a realistic example spanning
 * career, education, financial, personal, business, and technology
 * decisions, so a judge (or any user) immediately sees REGRET is not
 * limited to business/investment scenarios. Not a separate demo mode -
 * this is the exact same form every other decision goes through.
 */
export function ExampleDecisionPicker({ onSelect }: ExampleDecisionPickerProps) {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? exampleDecisions : exampleDecisions.slice(0, INITIAL_VISIBLE_COUNT);

  return (
    <div>
      <div className="flex items-center gap-2">
        <Sparkles className="size-3.5 shrink-0 text-ink-muted" aria-hidden />
        <p className="text-small font-medium text-ink">Explore example decisions</p>
      </div>
      <p className="mt-1 text-small text-ink-muted">
        Not sure where to start? Pick one to see how REGRET handles it.
      </p>

      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {visible.map((example) => (
          <button
            key={example.cardLabel}
            type="button"
            onClick={() => onSelect(example)}
            className="rounded-lg text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          >
            <Card variant="inset" padding="none" interactive className="h-full px-3 py-2">
              <p className="eyebrow">
                {example.categories.map((category) => decisionCategoryLabel(category)).join(' + ')}
              </p>
              <p className="mt-1 text-small text-ink">{example.cardLabel}</p>
            </Card>
          </button>
        ))}
      </div>

      {!expanded && exampleDecisions.length > INITIAL_VISIBLE_COUNT ? (
        <Button variant="ghost" size="sm" className="mt-2.5" onClick={() => setExpanded(true)}>
          Load more
        </Button>
      ) : null}
    </div>
  );
}
