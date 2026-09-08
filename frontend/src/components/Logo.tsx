import { cn } from '@/lib/cn';

export interface LogoMarkProps {
  className?: string;
}

/**
 * Geometric brand mark: a single decision point branching into two futures.
 * Drawn with tokens so it inherits the accent colour.
 */
export function LogoMark({ className }: LogoMarkProps) {
  return (
    <svg
      viewBox="0 0 32 32"
      role="img"
      aria-label="REGRET ENGINE"
      className={cn('size-8', className)}
    >
      <rect
        x="0.75"
        y="0.75"
        width="30.5"
        height="30.5"
        rx="8"
        fill="var(--color-accent-soft)"
        stroke="var(--color-accent-line)"
        strokeWidth="1.5"
      />
      <path
        d="M16 25V17.5"
        stroke="var(--color-accent)"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M16 17.5L9.5 10.5"
        stroke="var(--color-accent)"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M16 17.5L22.5 10.5"
        stroke="var(--color-ink-faint)"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="16" cy="17.5" r="2.25" fill="var(--color-canvas)" stroke="var(--color-accent)" strokeWidth="1.75" />
      <circle cx="9.5" cy="9.5" r="1.75" fill="var(--color-accent)" />
      <circle cx="22.5" cy="9.5" r="1.75" fill="var(--color-ink-faint)" />
    </svg>
  );
}

export interface LogoProps {
  /** Hides the wordmark, leaving only the mark. */
  markOnly?: boolean;
  className?: string;
}

export function Logo({ markOnly = false, className }: LogoProps) {
  return (
    <span className={cn('inline-flex items-center gap-2.5', className)}>
      <LogoMark className="size-7 shrink-0" />
      {markOnly ? null : (
        <span className="flex flex-col leading-none">
          <span className="text-[0.8125rem] font-semibold tracking-[0.14em] text-ink uppercase">
            Regret
          </span>
          <span className="text-[0.8125rem] font-semibold tracking-[0.14em] text-ink-muted uppercase">
            Engine
          </span>
        </span>
      )}
    </span>
  );
}
