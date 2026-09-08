import { useId, type ComponentPropsWithRef, type ReactNode } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/cn';
import { CONTROL_BASE, controlBorder, describedBy, Field } from './Field';
import type { Size } from '@/types';

const SIZE: Record<Size, string> = {
  sm: 'h-8 pl-2.5 pr-8',
  md: 'h-9.5 pl-3 pr-9',
  lg: 'h-11 pl-3.5 pr-10',
};

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends ComponentPropsWithRef<'select'> {
  label?: string;
  hint?: string;
  error?: string;
  selectSize?: Size;
  options: SelectOption[];
  /** Non-selectable leading option, e.g. "All domains". */
  placeholder?: string;
  labelAside?: ReactNode;
  fieldClassName?: string;
}

export function Select({
  label,
  hint,
  error,
  selectSize = 'md',
  options,
  placeholder,
  labelAside,
  fieldClassName,
  className,
  id,
  required,
  ...rest
}: SelectProps) {
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
        <select
          id={fieldId}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(fieldId, hint, error)}
          className={cn(
            CONTROL_BASE,
            controlBorder(Boolean(error)),
            SIZE[selectSize],
            'cursor-pointer appearance-none',
            className,
          )}
          {...rest}
        >
          {placeholder ? (
            <option value="" disabled>
              {placeholder}
            </option>
          ) : null}
          {options.map((option) => (
            <option key={option.value} value={option.value} disabled={option.disabled}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown
          className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-ink-muted"
          aria-hidden
        />
      </div>
    </Field>
  );
}
