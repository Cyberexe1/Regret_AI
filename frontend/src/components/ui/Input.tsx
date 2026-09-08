import { useId, type ComponentPropsWithRef, type ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/cn';
import { CONTROL_BASE, controlBorder, describedBy, Field } from './Field';
import type { Size } from '@/types';

const SIZE: Record<Size, string> = {
  sm: 'h-8 px-2.5',
  md: 'h-9.5 px-3',
  lg: 'h-11 px-3.5',
};

export interface InputProps extends Omit<ComponentPropsWithRef<'input'>, 'size'> {
  label?: string;
  hint?: string;
  error?: string;
  inputSize?: Size;
  icon?: LucideIcon;
  labelAside?: ReactNode;
  /** Wrapper class; use `className` for the input element itself. */
  fieldClassName?: string;
}

export function Input({
  label,
  hint,
  error,
  inputSize = 'md',
  icon: Icon,
  labelAside,
  fieldClassName,
  className,
  id,
  required,
  ...rest
}: InputProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;

  return (
    <Field
      id={fieldId}
      label={label}
      hint={hint}
      error={error}
      required={required}
      labelAside={labelAside}
      className={fieldClassName}
    >
      <div className="relative">
        {Icon ? (
          <Icon
            className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-muted"
            aria-hidden
          />
        ) : null}
        <input
          id={fieldId}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(fieldId, hint, error)}
          className={cn(
            CONTROL_BASE,
            controlBorder(Boolean(error)),
            SIZE[inputSize],
            Icon && 'pl-9',
            className,
          )}
          {...rest}
        />
      </div>
    </Field>
  );
}
