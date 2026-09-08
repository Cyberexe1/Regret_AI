import { useId, type ComponentPropsWithRef, type ReactNode } from 'react';
import { cn } from '@/lib/cn';
import { CONTROL_BASE, controlBorder, describedBy, Field } from './Field';

export interface TextareaProps extends ComponentPropsWithRef<'textarea'> {
  label?: string;
  hint?: string;
  error?: string;
  labelAside?: ReactNode;
  /** Shows a live "used / maxLength" counter beside the label. */
  showCount?: boolean;
  fieldClassName?: string;
}

export function Textarea({
  label,
  hint,
  error,
  labelAside,
  showCount = false,
  fieldClassName,
  className,
  id,
  required,
  rows = 5,
  maxLength,
  value,
  ...rest
}: TextareaProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;

  const used = typeof value === 'string' ? value.length : 0;
  const aside =
    showCount && maxLength ? (
      <span className="numeric">
        {used} / {maxLength}
      </span>
    ) : (
      labelAside
    );

  return (
    <Field
      id={fieldId}
      label={label}
      hint={hint}
      error={error}
      required={required}
      labelAside={aside}
      className={fieldClassName}
    >
      <textarea
        id={fieldId}
        rows={rows}
        required={required}
        maxLength={maxLength}
        value={value}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(fieldId, hint, error)}
        className={cn(
          CONTROL_BASE,
          controlBorder(Boolean(error)),
          'resize-y px-3 py-2.5 leading-relaxed',
          className,
        )}
        {...rest}
      />
    </Field>
  );
}
