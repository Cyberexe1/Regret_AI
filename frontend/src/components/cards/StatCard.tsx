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
  /**
   * Whether an upward move is a good outcome. Rising regret is bad, rising
   * validated experiments is good, so each metric declares its own polarity.
   */
  upIsGood: boolean;
}

export interface StatCardProps {
  label: string;
  value: string;
  /** Unit or denominator, e.g. "/100" or "decisions". */
  unit?: string;
  icon?: LucideIcon;
  tone?: Tone;
  /** Signed change versus the previous period. */
  delta?: StatDelta;
  /** Explanatory copy surfaced on hover over the label. */
  help?: string;
  footer?: ReactNode;
  className?: string;
}

/**
 * Compact metric tile. Kept presentational so dashboard, analysis and
 * experiment views can all reuse it without re-deriving layout.
 */
export function StatCard({
  label,
  value,
  unit,
  icon: Icon,
  tone = 'neutral',
  delta,
  help,
  footer,
  className,
}: StatCardProps) {
  const deltaIsGood = delta ? (delta.direction === 'up') === delta.upIsGood : false;
  const DeltaIcon = delta?.direction === 'up' ? ArrowUpRight : ArrowDownRight;

  const labelNode = <span className="eyebrow">{label}</span>;

  return (
    <Card className={cn('flex flex-col gap-3', className)}>
      <div className="flex items-center justify-between gap-3">
        {help ? <Tooltip content={help}>{labelNode}</Tooltip> : labelNode}
        {Icon ? (
          <span
            className={cn(
              'inline-flex size-7 items-center justify-center rounded-md border',
              toneSurface[tone],
            )}
          >
            <Icon className="size-3.5" aria-hidden />
          </span>
        ) : null}
      </div>

      <div className="flex items-baseline gap-1.5">
        <span className="numeric text-page-title text-ink">{value}</span>
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
