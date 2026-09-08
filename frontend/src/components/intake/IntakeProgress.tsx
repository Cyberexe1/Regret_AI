import { Check } from 'lucide-react';
import type { ResolvedIntakeStep } from '@/data/intake';
import { cn } from '@/lib/cn';

const BAR: Record<ResolvedIntakeStep['status'], string> = {
  complete: 'bg-accent',
  current: 'bg-accent-muted',
  upcoming: 'bg-hairline',
};

const LABEL: Record<ResolvedIntakeStep['status'], string> = {
  complete: 'text-ink-secondary',
  current: 'text-ink',
  upcoming: 'text-ink-muted',
};

export interface IntakeProgressProps {
  steps: ResolvedIntakeStep[];
}

/**
 * Four phases on one page. Each item scrolls to the section it represents, so
 * the form reads as a sequence without splitting into separate routes.
 */
export function IntakeProgress({ steps }: IntakeProgressProps) {
  const scrollToSection = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <ol className="grid grid-cols-2 gap-x-4 gap-y-5 sm:grid-cols-4 sm:gap-x-5">
      {steps.map((step) => (
        <li key={step.index}>
          <button
            type="button"
            onClick={() => scrollToSection(step.target)}
            aria-current={step.status === 'current' ? 'step' : undefined}
            className="w-full rounded-sm text-left"
          >
            <span
              className={cn(
                'block h-0.5 w-full rounded-full transition-colors duration-300',
                BAR[step.status],
              )}
              aria-hidden
            />
            <span className="mt-3 flex items-center gap-2">
              {step.status === 'complete' ? (
                <Check className="size-3.5 shrink-0 text-accent-ink" aria-hidden />
              ) : (
                <span className="numeric text-micro text-ink-muted">{step.index}</span>
              )}
              <span className={cn('truncate text-small font-medium', LABEL[step.status])}>
                {step.label}
              </span>
            </span>
          </button>
        </li>
      ))}
    </ol>
  );
}
