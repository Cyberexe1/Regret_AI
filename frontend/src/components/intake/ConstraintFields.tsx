import { CalendarDays, MapPin, Wallet } from 'lucide-react';
import { Input } from '@/components/ui/Input';
import { riskToleranceOptions } from '@/data/intake';
import { cn } from '@/lib/cn';
import type { DecisionDraft, RiskTolerance } from '@/types';

export interface ConstraintFieldsProps {
  constraints: DecisionDraft['constraints'];
  onChange: <K extends keyof DecisionDraft['constraints']>(
    key: K,
    value: DecisionDraft['constraints'][K],
  ) => void;
}

function RiskToleranceField({
  value,
  onChange,
}: {
  value: RiskTolerance;
  onChange: (value: RiskTolerance) => void;
}) {
  return (
    <fieldset>
      <legend className="text-small font-medium text-ink">Risk tolerance</legend>
      <p className="mt-1 text-small text-ink-muted">
        Sets how hard the engine argues against the downside.
      </p>

      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        {riskToleranceOptions.map((option) => {
          const selected = option.value === value;

          return (
            <label
              key={option.value}
              className={cn(
                'cursor-pointer rounded-lg border p-4 transition-colors duration-150',
                'has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-focus',
                selected
                  ? 'border-accent-line bg-panel-accent'
                  : 'border-hairline bg-surface-inset hover:border-hairline-strong hover:bg-surface-raised',
              )}
            >
              <input
                type="radio"
                name="risk-tolerance"
                value={option.value}
                checked={selected}
                onChange={() => onChange(option.value)}
                className="sr-only"
              />

              <span className="flex items-center gap-2.5">
                <span
                  className={cn(
                    'flex size-4 shrink-0 items-center justify-center rounded-full border transition-colors',
                    selected ? 'border-accent' : 'border-hairline-strong',
                  )}
                  aria-hidden
                >
                  {selected ? <span className="size-2 rounded-full bg-accent" /> : null}
                </span>
                <span className="text-card-title text-ink">{option.label}</span>
              </span>

              <span className="mt-2 block text-small text-ink-secondary">
                {option.description}
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

export function ConstraintFields({ constraints, onChange }: ConstraintFieldsProps) {
  return (
    <div className="space-y-6">
      <div className="grid gap-5 sm:grid-cols-2">
        <Input
          label="Budget"
          icon={Wallet}
          placeholder="₹5,00,000 upfront, ₹40,000 a month"
          value={constraints.budget}
          onChange={(event) => onChange('budget', event.target.value)}
        />
        <Input
          label="Timeline"
          icon={CalendarDays}
          placeholder="Decide by 30 September, launch in November"
          value={constraints.timeline}
          onChange={(event) => onChange('timeline', event.target.value)}
        />
        <Input
          label="Location"
          icon={MapPin}
          placeholder="Andheri West, Mumbai"
          value={constraints.location}
          onChange={(event) => onChange('location', event.target.value)}
          fieldClassName="sm:col-span-2"
        />
      </div>

      <RiskToleranceField
        value={constraints.riskTolerance}
        onChange={(value) => onChange('riskTolerance', value)}
      />
    </div>
  );
}
