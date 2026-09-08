import type { ReactNode } from 'react';
import { Reveal } from '@/components/Reveal';
import { cn } from '@/lib/cn';

export interface SettingsSectionProps {
  title: string;
  description?: string;
  /** Set for the danger zone, which uses a warning-tinted shell. */
  tone?: 'default' | 'danger';
  children: ReactNode;
}

export function SettingsSection({
  title,
  description,
  tone = 'default',
  children,
}: SettingsSectionProps) {
  return (
    <Reveal>
      <section
        aria-label={title}
        className={cn(
          'overflow-hidden rounded-xl border',
          tone === 'danger' ? 'border-danger-line/60 bg-danger-soft/15' : 'border-hairline bg-surface',
        )}
      >
        <div className="border-b border-hairline px-5 py-4 md:px-6">
          <h3
            className={cn(
              'text-card-title',
              tone === 'danger' ? 'text-danger-ink' : 'text-ink',
            )}
          >
            {title}
          </h3>
          {description ? (
            <p className="mt-1 text-small text-ink-secondary">{description}</p>
          ) : null}
        </div>

        <div className="divide-y divide-hairline">{children}</div>
      </section>
    </Reveal>
  );
}

export interface SettingRowProps {
  label: string;
  description?: string;
  /** The control, right-aligned from `sm` upwards. */
  control: ReactNode;
  /** Stacks the control beneath the label, for wide inputs. */
  stacked?: boolean;
}

export function SettingRow({ label, description, control, stacked = false }: SettingRowProps) {
  return (
    <div
      className={cn(
        'gap-4 px-5 py-4 md:px-6',
        stacked ? 'flex flex-col' : 'flex flex-col sm:flex-row sm:items-center sm:justify-between',
      )}
    >
      <div className="min-w-0">
        <p className="text-small font-medium text-ink">{label}</p>
        {description ? (
          <p className="mt-1 max-w-md text-small text-ink-secondary">{description}</p>
        ) : null}
      </div>
      <div className={cn('shrink-0', stacked && 'w-full')}>{control}</div>
    </div>
  );
}
