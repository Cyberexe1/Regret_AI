import { ArrowRight } from 'lucide-react';
import { cn } from '@/lib/cn';
import type { Tone } from '@/types';

interface JourneyStep {
  eyebrow: string;
  value: string;
  caption: string;
  tone: Tone;
}

export interface ThresholdJourneyProps {
  currentValue: string;
  thresholdValue: string;
  experimentValue: string;
  experimentCaption: string;
}

const TONE_SHELL: Record<Tone, string> = {
  neutral: 'border-hairline bg-surface-inset',
  accent: 'border-accent-line/70 bg-accent-soft/40',
  success: 'border-success-line/70 bg-success-soft/30',
  warning: 'border-warning-line/70 bg-warning-soft/30',
  danger: 'border-danger-line/70 bg-danger-soft/30',
  info: 'border-info-line/70 bg-info-soft/30',
};

const TONE_VALUE: Record<Tone, string> = {
  neutral: 'text-ink',
  accent: 'text-accent-ink',
  success: 'text-success-ink',
  warning: 'text-warning-ink',
  danger: 'text-danger-ink',
  info: 'text-info-ink',
};

/**
 * The spine of the report: where the decision stands now, the value at which it
 * breaks, and the cheapest way to find out which side of the line it lands on.
 */
export function ThresholdJourney({
  currentValue,
  thresholdValue,
  experimentValue,
  experimentCaption,
}: ThresholdJourneyProps) {
  const steps: JourneyStep[] = [
    {
      eyebrow: 'Current condition',
      value: currentValue,
      caption: 'Best available estimate, unverified',
      tone: 'warning',
    },
    {
      eyebrow: 'Breaking threshold',
      value: thresholdValue,
      caption: 'Below this the model stops working',
      tone: 'danger',
    },
    {
      eyebrow: 'Experiment',
      value: experimentValue,
      caption: experimentCaption,
      tone: 'accent',
    },
  ];

  return (
    <div className="flex flex-col items-stretch gap-3 md:flex-row md:items-center">
      {steps.map((step, index) => (
        <div key={step.eyebrow} className="flex flex-1 flex-col items-stretch gap-3 md:flex-row md:items-center">
          <div className={cn('flex-1 rounded-xl border px-5 py-4', TONE_SHELL[step.tone])}>
            <p className="eyebrow">{step.eyebrow}</p>
            <p
              className={cn(
                'numeric mt-2 text-[1.5rem] leading-none font-semibold tracking-[-0.02em]',
                TONE_VALUE[step.tone],
              )}
            >
              {step.value}
            </p>
            <p className="mt-2.5 text-small text-ink-muted">{step.caption}</p>
          </div>

          {index < steps.length - 1 ? (
            <ArrowRight
              className="mx-auto size-4 shrink-0 rotate-90 text-ink-faint md:rotate-0"
              aria-hidden
            />
          ) : null}
        </div>
      ))}
    </div>
  );
}
