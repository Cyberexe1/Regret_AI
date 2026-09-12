import { useCallback, useId, useRef, useState, type FocusEvent, type ReactNode } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useEscapeKey } from '@/hooks/useEscapeKey';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import { useOutsidePointerDown } from '@/hooks/useOutsidePointerDown';
import { cn } from '@/lib/cn';
import { DURATION, EASE_OUT } from '@/lib/motion';

export interface TopbarMenuProps {
  icon: LucideIcon;
  /** Accessible name for the trigger. */
  label: string;
  /** Heading inside the panel. */
  title: string;
  className?: string;
  children: ReactNode;
}

/**
 * Small anchored panel used by the topbar icon buttons.
 *
 * Deliberately non-modal: it does not lock scroll or trap Tab, because it is a
 * peripheral panel rather than a task the user must finish. Instead it closes on
 * Escape, on a pointer press outside, and when focus moves past it, and focus
 * returns to the trigger every time so keyboard users are never dropped at the
 * top of the document.
 */
export function TopbarMenu({ icon, label, title, className, children }: TopbarMenuProps) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const reduceMotion = useReducedMotion();
  const panelId = useId();
  const titleId = `${panelId}-title`;

  const close = useCallback(() => setOpen(false), []);

  useEscapeKey(open, close);
  useOutsidePointerDown(open, wrapperRef, close);
  // Moves focus into the panel on open and back to the trigger on close.
  useFocusTrap(open, panelRef, { trapTab: false });

  /** Tabbing past the last control in the panel should dismiss it. */
  const onBlurCapture = (event: FocusEvent<HTMLDivElement>) => {
    const next = event.relatedTarget;
    if (next instanceof Node && wrapperRef.current?.contains(next)) return;
    // A null `relatedTarget` means focus left for the page background or
    // another window; neither should leave an open panel behind.
    setOpen(false);
  };

  return (
    <div ref={wrapperRef} className="relative" onBlurCapture={onBlurCapture}>
      <Button
        variant="ghost"
        size="sm"
        iconOnly
        leftIcon={icon}
        aria-label={label}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen((value) => !value)}
      />

      <AnimatePresence>
        {open ? (
          <motion.div
            ref={panelRef}
            id={panelId}
            role="dialog"
            aria-labelledby={titleId}
            tabIndex={-1}
            className={cn(
              'absolute top-full right-0 z-40 mt-2 max-h-[min(26rem,calc(100dvh-var(--header-offset)-1rem))] w-[min(18rem,calc(100vw-2rem))] overflow-y-auto overscroll-contain rounded-xl border border-hairline-strong bg-surface-overlay shadow-overlay outline-none',
              className,
            )}
            initial={reduceMotion ? undefined : { opacity: 0, y: -6, scale: 0.98 }}
            animate={reduceMotion ? undefined : { opacity: 1, y: 0, scale: 1 }}
            exit={reduceMotion ? undefined : { opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: DURATION.micro, ease: EASE_OUT }}
          >
            <div className="border-b border-hairline px-4 py-3">
              <p id={titleId} className="text-card-title text-ink">
                {title}
              </p>
            </div>
            <div className="p-4">{children}</div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
