import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

export interface KbdProps {
  children: ReactNode;
  className?: string;
}

/** Keyboard hint chip, e.g. the ⌘ K shortcut beside the command trigger. */
export function Kbd({ children, className }: KbdProps) {
  return (
    <kbd
      className={cn(
        'inline-flex h-5 min-w-5 items-center justify-center gap-0.5 rounded-sm border border-hairline-strong bg-surface-raised px-1.5 font-sans text-micro tracking-normal text-ink-muted',
        className,
      )}
    >
      {children}
    </kbd>
  );
}
