import { Sparkles } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { decisionCategoryLabel, exampleDecisions, type ExampleDecision } from '@/data/decisionTypes';

export interface ExampleDecisionPickerProps {
  onSelect: (example: ExampleDecision) => void;
}

/**
 * "Explore example decisions" (Step 25 sections 13/15) - clicking a card
 * populates the real intake form with a realistic example spanning
 * career, education, financial, personal, business, and technology
 * decisions, so a judge (or any user) immediately sees REGRET is not
 * limited to business/investment scenarios. Not a separate demo mode -
 * this is the exact same form every other decision goes through.
 */
export function ExampleDecisionPicker({ onSelect }: ExampleDecisionPickerProps) {
  return (
    <div>
      <div className="flex items-center gap-2">
        <Sparkles className="size-3.5 shrink-0 text-ink-muted" aria-hidden />
        <p className="text-small font-medium text-ink">Explore example decisions</p>
      </div>
      <p className="mt-1 text-small text-ink-muted">
        Not sure where to start? Pick one to see how REGRET handles it.
      </p>

      <div className="mt-3 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
        {exampleDecisions.map((example) => (
          <button
            key={example.cardLabel}
            type="button"
            onClick={() => onSelect(example)}
            className="rounded-xl text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          >
            <Card variant="inset" padding="sm" interactive className="h-full">
              <p className="eyebrow">
                {example.categories.map((category) => decisionCategoryLabel(category)).join(' + ')}
              </p>
              <p className="mt-1.5 text-small text-ink">{example.cardLabel}</p>
            </Card>
          </button>
        ))}
      </div>
    </div>
  );
}
