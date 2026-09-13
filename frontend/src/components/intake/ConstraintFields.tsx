import { CalendarDays, MapPin, Wallet } from 'lucide-react';
import { Input } from '@/components/ui/Input';
import { getContextFieldConfig } from '@/data/decisionTypes';
import { riskToleranceOptions } from '@/data/intake';
import { cn } from '@/lib/cn';
import type { DecisionCategory, RiskTolerance } from '@/types';

/**
 * One field per progressively-disclosed "core" chip (Step 26 - "Smart
 * Minimal Intake Experience"). None of these render by default anymore
 * - `SmartContextChips` mounts exactly the ones the user has selected,
 * so a career decision never shows an empty "Location" box it doesn't
 * need. Each field still adapts its label/placeholder to the decision's
 * selected categories via `getContextFieldConfig` (Step 25), unchanged.
 */

export interface FinancialCommitmentFieldProps {
  categories: DecisionCategory[];
  value: string;
  onChange: (value: string) => void;
}

export function FinancialCommitmentField({ categories, value, onChange }: FinancialCommitmentFieldProps) {
  const config = getContextFieldConfig(categories[0] ?? null);
  return (
    <Input
      label={config.financialLabel}
      labelAside="Optional"
      icon={Wallet}
      placeholder={config.financialPlaceholder}
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

export interface TimingFieldProps {
  value: string;
  onChange: (value: string) => void;
}

export function TimingField({ value, onChange }: TimingFieldProps) {
  return (
    <Input
      label="When does this decision need to be made?"
      labelAside="Optional"
      icon={CalendarDays}
      placeholder="By Friday, within 3 months, no fixed deadline..."
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

export interface LocationFieldProps {
  categories: DecisionCategory[];
  value: string;
  onChange: (value: string) => void;
}

export function LocationField({ categories, value, onChange }: LocationFieldProps) {
  const config = getContextFieldConfig(categories[0] ?? null);
  return (
    <Input
      label="Location"
      labelAside="Optional"
      icon={MapPin}
      placeholder={config.locationPlaceholder}
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

export interface CommitmentFieldProps {
  value: string;
  onChange: (value: string) => void;
}

export function CommitmentField({ value, onChange }: CommitmentFieldProps) {
  return (
    <Input
      label="What are you putting at stake?"
      labelAside="Optional"
      placeholder="Money, time, career opportunity, reputation, relationships, resources, etc."
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

export interface RiskToleranceFieldProps {
  value: RiskTolerance;
  onChange: (value: RiskTolerance) => void;
}

export function RiskToleranceField({ value, onChange }: RiskToleranceFieldProps) {
  return (
    <fieldset>
      <legend className="text-small font-medium text-ink">
        How much downside are you willing to accept?
      </legend>

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
