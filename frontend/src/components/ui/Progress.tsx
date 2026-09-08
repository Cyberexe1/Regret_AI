import { cn } from '@/lib/cn';
import { clamp } from '@/lib/format';
import { toneFill } from '@/lib/tone';
import type { Size, Tone } from '@/types';

const TRACK_SIZE: Record<Size, string> = {
  sm: 'h-1',
  md: 'h-1.5',
  lg: 'h-2.5',
};

export interface ProgressProps {
  /** 0-100. Values outside the range are clamped. */
  value: number;
  tone?: Tone;
  size?: Size;
  label?: string;
  /** Prints the numeric value beside the label. */
  showValue?: boolean;
  /** Suffix for the printed value, e.g. "/100" or "%". */
  valueSuffix?: string;
  className?: string;
}

export function Progress({
  value,
  tone = 'accent',
  size = 'md',
  label,
  showValue = false,
  valueSuffix = '',
  className,
}: ProgressProps) {
  const pct = clamp(value);

  return (
    <div className={cn('space-y-1.5', className)}>
      {(label || showValue) && (
        <div className="flex items-baseline justify-between gap-3">
          {label ? <span className="text-small text-ink-secondary">{label}</span> : null}
          {showValue ? (
            <span className="numeric text-small font-medium text-ink">
              {Math.round(pct)}
              {valueSuffix}
            </span>
          ) : null}
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
        className={cn('w-full overflow-hidden rounded-full bg-hairline', TRACK_SIZE[size])}
      >
        <div
          className={cn('h-full rounded-full transition-[width] duration-500', toneFill[tone])}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
