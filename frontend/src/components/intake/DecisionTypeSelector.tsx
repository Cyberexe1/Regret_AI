import { decisionCategories } from '@/data/decisionTypes';
import { cn } from '@/lib/cn';
import type { DecisionCategory } from '@/types';

export interface DecisionTypeSelectorProps {
  /** Zero or more - a decision can genuinely span more than one
   * category (Step 26 section 2), e.g. "accept a higher-paying job
   * that requires relocating" is Career + Personal. */
  value: DecisionCategory[];
  onChange: (value: DecisionCategory[]) => void;
  /** Shown when nothing is selected yet and inference has a guess -
   * purely informational, never auto-applied without the user's own
   * confirmation. */
  inferredCategory?: DecisionCategory | null;
}

/**
 * "What kind of decision is this?" (Step 25 section 1, extended in Step
 * 26 section 2 to allow multiple) - a multi-select chip group over
 * `decisionCategories`. Never a hard requirement: REGRET works
 * identically for "Other," and the AI's own classification during
 * analysis remains the source of truth (see `@/data/decisionTypes`'s
 * module docstring). Clicking a selected chip deselects just that one.
 */
export function DecisionTypeSelector({
  value,
  onChange,
  inferredCategory,
}: DecisionTypeSelectorProps) {
  const toggle = (category: DecisionCategory) => {
    if (value.includes(category)) {
      onChange(value.filter((c) => c !== category));
    } else {
      onChange([...value, category]);
    }
  };

  return (
    <fieldset>
      <legend className="text-small font-medium text-ink">What kind of decision is this?</legend>

      <div
        className="mt-3 flex flex-wrap gap-2"
        role="group"
        aria-label="What kind of decision is this?"
      >
        {decisionCategories.map((option) => {
          const selected = value.includes(option.value);
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={selected}
              onClick={() => toggle(option.value)}
              className={cn(
                'rounded-full border px-3.5 py-1.5 text-small font-medium transition-colors duration-150',
                'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
                selected
                  ? 'border-accent-line bg-panel-accent text-accent-ink'
                  : 'border-hairline bg-surface-inset text-ink-secondary hover:border-hairline-strong hover:bg-surface-raised',
              )}
            >
              {option.label}
            </button>
          );
        })}
      </div>

      <p className="mt-2.5 text-small text-ink-muted">
        Not sure? REGRET will infer the decision type. You can select more than one if it applies.
        {inferredCategory && value.length === 0 ? (
          <>
            {' '}
            Looks like a{' '}
            <span className="font-medium text-ink-secondary">
              {decisionCategories.find((c) => c.value === inferredCategory)?.label}
            </span>{' '}
            decision.
          </>
        ) : null}
      </p>
    </fieldset>
  );
}
