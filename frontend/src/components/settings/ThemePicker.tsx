import { Monitor, Moon, Sun } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/cn';
import type { ThemePreference } from '@/hooks/useWorkspaceSettings';

const OPTIONS: { value: ThemePreference; label: string; icon: LucideIcon }[] = [
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
  { value: 'light', label: 'Light', icon: Sun },
];

export interface ThemePickerProps {
  value: ThemePreference;
  onChange: (value: ThemePreference) => void;
}

export function ThemePicker({ value, onChange }: ThemePickerProps) {
  return (
    <div className="w-full space-y-3">
      <div
        role="radiogroup"
        aria-label="Theme"
        className="grid grid-cols-3 gap-2 sm:w-72 sm:justify-self-end"
      >
        {OPTIONS.map((option) => {
          const selected = option.value === value;

          return (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(option.value)}
              className={cn(
                'flex flex-col items-center gap-2 rounded-lg border px-3 py-3 transition-colors duration-150',
                selected
                  ? 'border-accent-line bg-accent-soft text-ink'
                  : 'border-hairline bg-surface-inset text-ink-secondary hover:border-hairline-strong hover:text-ink',
              )}
            >
              <option.icon
                className={cn('size-4', selected ? 'text-accent-ink' : 'text-ink-muted')}
                aria-hidden
              />
              <span className="text-small font-medium">{option.label}</span>
            </button>
          );
        })}
      </div>

      {value !== 'dark' ? (
        <p className="text-small text-warning-ink sm:text-right">
          Only the dark palette is built. The interface stays dark for now.
        </p>
      ) : null}
    </div>
  );
}
