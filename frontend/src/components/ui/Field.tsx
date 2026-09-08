import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

/** Shared control chrome so Input, Textarea and Select stay visually identical. */
export const CONTROL_BASE =
  'w-full rounded-md border bg-surface-inset text-body text-ink placeholder:text-ink-faint ' +
  'transition-[border-color,background-color] duration-150 ' +
  'hover:border-hairline-strong focus:border-accent focus:bg-surface ' +
  'disabled:cursor-not-allowed disabled:opacity-50';

export function controlBorder(invalid: boolean): string {
  return invalid ? 'border-danger-line focus:border-danger' : 'border-hairline';
}

export interface FieldProps {
  id: string;
  label?: string;
  /** Helper text shown under the control while there is no error. */
  hint?: string;
  error?: string;
  required?: boolean;
  /** Right-aligned annotation next to the label, e.g. "Optional". */
  labelAside?: ReactNode;
  className?: string;
  children: ReactNode;
}

export function Field({
  id,
  label,
  hint,
  error,
  required = false,
  labelAside,
  className,
  children,
}: FieldProps) {
  return (
    <div className={cn('space-y-1.5', className)}>
      {label ? (
        <div className="flex items-baseline justify-between gap-3">
          <label htmlFor={id} className="text-small font-medium text-ink">
            {label}
            {required ? (
              <span className="ml-1 text-danger-ink" aria-hidden>
                *
              </span>
            ) : null}
          </label>
          {labelAside ? <span className="text-micro text-ink-muted">{labelAside}</span> : null}
        </div>
      ) : null}

      {children}

      {error ? (
        <p id={`${id}-error`} className="text-small text-danger-ink">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-small text-ink-muted">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

/** Wires aria-describedby / aria-invalid consistently across controls. */
export function describedBy(id: string, hint?: string, error?: string): string | undefined {
  if (error) return `${id}-error`;
  if (hint) return `${id}-hint`;
  return undefined;
}
