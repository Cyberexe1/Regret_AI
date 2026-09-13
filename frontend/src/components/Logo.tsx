import { cn } from '@/lib/cn';

export interface LogoMarkProps {
  className?: string;
}

/**
 * Brand mark: renders `public/favicon.svg` directly as an image, so the
 * logo is identical everywhere it appears (navbar, footer, sidebar,
 * illustrations, 404) and always stays in sync with the favicon file.
 */
export function LogoMark({ className }: LogoMarkProps) {
  return (
    <img
      src="/favicon.svg"
      alt="REGRET ENGINE"
      className={cn('size-8', className)}
    />
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
          <span className="text-small font-semibold tracking-[0.14em] text-ink uppercase">
            Regret
          </span>
          <span className="text-small font-semibold tracking-[0.14em] text-ink-muted uppercase">
            Engine
          </span>
        </span>
      )}
    </span>
  );
}
