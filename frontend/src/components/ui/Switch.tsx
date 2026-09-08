import { cn } from '@/lib/cn';

export interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  /** Accessible name. Pair with a visible label in the surrounding row. */
  label: string;
  disabled?: boolean;
  className?: string;
}

/** Binary preference control. Reports state through `role="switch"`. */
export function Switch({ checked, onChange, label, disabled = false, className }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative inline-flex h-5.5 w-10 shrink-0 items-center rounded-full border transition-colors duration-200',
        checked ? 'border-accent bg-accent' : 'border-hairline-strong bg-surface-inset',
        disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
        className,
      )}
    >
      <span
        className={cn(
          'absolute size-4 rounded-full bg-white shadow-soft transition-transform duration-200 ease-out',
          checked ? 'translate-x-[1.25rem]' : 'translate-x-0.5',
        )}
        aria-hidden
      />
    </button>
  );
}
