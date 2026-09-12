import type { ReactNode } from 'react';
import { ArrowDownRight, ArrowUpRight, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/cn';
import { toneSurface, toneText } from '@/lib/tone';
import type { Tone } from '@/types';
import { Card } from '@/components/ui/Card';
import { Tooltip } from '@/components/ui/Tooltip';

export interface StatDelta {
  /** Pre-formatted change, e.g. "12%" or "3". */
  value: string;
  direction: 'up' | 'down';
  /** Whether an upward move is a good outcome. */
  upIsGood: boolean;
}

const VALUE_SIZE = {
  compact: 'text-metric',
  large: 'text-page-title',
} as const;

export interface StatCardProps {
  label: string;
  value: string;
  unit?: string;
  icon?: LucideIcon;
  tone?: Tone;
  valueSize?: keyof typeof VALUE_SIZE;
  delta?: StatDelta;
  help?: string;
  footer?: ReactNode;
  className?: string;
}

/** Compact, presentational metric tile shared across product views. */
export function StatCard({
  label,
  value,
  unit,
  icon: Icon,
  tone = 'neutral',
  valueSize = 'compact',
  delta,
  help,
  footer,
  className,
}: StatCardProps) {
  const deltaIsGood = delta ? (delta.direction === 'up') === delta.upIsGood : false;
  const DeltaIcon = delta?.direction === 'up' ? ArrowUpRight : ArrowDownRight;
  const labelNode = <span className="eyebrow break-words">{label}</span>;

  return (
    <Card className={cn('relative flex min-h-31 flex-col gap-4 overflow-visible', className)}>
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">{help ? <Tooltip content={help}>{labelNode}</Tooltip> : labelNode}</div>
        {Icon ? (
          <span
            className={cn(
              'inline-flex size-8 shrink-0 items-center justify-center rounded-lg border',
              toneSurface[tone],
            )}
          >
            <Icon className="size-4" aria-hidden />
          </span>
        ) : null}
      </div>

      <div className="mt-auto flex min-w-0 flex-wrap items-baseline gap-x-1.5 gap-y-2">
        <span className={cn('numeric min-w-0 break-words text-ink', VALUE_SIZE[valueSize])}>
          {value}
        </span>
        {unit ? <span className="text-small text-ink-muted">{unit}</span> : null}
        {delta ? (
          <span
            className={cn(
              'ml-auto inline-flex items-center gap-0.5 text-small font-medium',
              deltaIsGood ? toneText.success : toneText.danger,
            )}
          >
            <DeltaIcon className="size-3.5" aria-hidden />
            <span className="numeric">{delta.value}</span>
          </span>
        ) : null}
      </div>

      {footer ? <div className="text-small text-ink-secondary">{footer}</div> : null}
    </Card>
  );
}
