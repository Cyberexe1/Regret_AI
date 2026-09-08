import { useEffect, useRef, useState, type ReactNode } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useEscapeKey } from '@/hooks/useEscapeKey';
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
 * Small anchored panel used by the topbar icon buttons. Closes on Escape and on
 * any click outside itself.
 */
export function TopbarMenu({ icon, label, title, className, children }: TopbarMenuProps) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const reduceMotion = useReducedMotion();

  useEscapeKey(open, () => setOpen(false));

  useEffect(() => {
    if (!open) return;

    const onPointerDown = (event: MouseEvent) => {
      if (!wrapperRef.current?.contains(event.target as Node)) setOpen(false);
    };

    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [open]);

  return (
    <div ref={wrapperRef} className="relative">
      <Button
        variant="ghost"
        size="sm"
        iconOnly
        leftIcon={icon}
        aria-label={label}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      />

      <AnimatePresence>
        {open ? (
          <motion.div
            role="dialog"
            aria-label={title}
            className={cn(
              'absolute top-full right-0 z-40 mt-2 w-72 overflow-hidden rounded-xl border border-hairline-strong bg-surface-overlay shadow-overlay',
              className,
            )}
            initial={reduceMotion ? undefined : { opacity: 0, y: -6, scale: 0.98 }}
            animate={reduceMotion ? undefined : { opacity: 1, y: 0, scale: 1 }}
            exit={reduceMotion ? undefined : { opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: DURATION.micro, ease: EASE_OUT }}
          >
            <div className="border-b border-hairline px-4 py-3">
              <p className="text-card-title text-ink">{title}</p>
            </div>
            <div className="p-4">{children}</div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
