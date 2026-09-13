import { Textarea } from '@/components/ui/Textarea';

export interface ContextFieldProps {
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  rows?: number;
  required?: boolean;
  /** Helper text under the field, properly wired via aria-describedby -
   * used for the category-adaptive "constraints" guidance. */
  hint?: string;
}

/**
 * One universal, decision-neutral context field (Step 25 section 3) -
 * a thin, reusable wrapper over `Textarea` so every "Context" question
 * (desired outcome, constraints, beliefs, uncertainties, commitment,
 * alternatives) renders identically instead of six near-duplicate
 * blocks of JSX. All of these are optional except the decision
 * statement itself - `required` defaults to false.
 */
export function ContextField({
  label,
  placeholder,
  value,
  onChange,
  rows = 3,
  required = false,
  hint,
}: ContextFieldProps) {
  return (
    <Textarea
      label={label}
      hint={hint}
      labelAside={required ? undefined : 'Optional'}
      required={required}
      rows={rows}
      placeholder={placeholder}
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
