import { useEffect, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '@/lib/cn';
import { useEscapeKey } from '@/hooks/useEscapeKey';
import { useLockBodyScroll } from '@/hooks/useLockBodyScroll';
import { Button } from './Button';

const SIZE = {
  sm: 'max-w-md',
  md: 'max-w-xl',
  lg: 'max-w-3xl',
} as const;

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  size?: keyof typeof SIZE;
  /** Right-aligned action row pinned below the content. */
  footer?: ReactNode;
  /** Set false for destructive flows that need an explicit choice. */
  dismissOnBackdrop?: boolean;
  children?: ReactNode;
}

export function Modal({
  open,
  onClose,
  title,
  description,
  size = 'md',
  footer,
  dismissOnBackdrop = true,
  children,
}: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEscapeKey(open, onClose);
  useLockBodyScroll(open);

  useEffect(() => {
    if (open) panelRef.current?.focus();
  }, [open]);

  return createPortal(
    <AnimatePresence>
      {open ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center">
          <motion.div
            className="absolute inset-0 bg-canvas/80 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={dismissOnBackdrop ? onClose : undefined}
          />

          <motion.div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-label={title}
            tabIndex={-1}
            className={cn(
              'relative z-10 w-full overflow-hidden rounded-2xl border border-hairline-strong bg-surface-overlay shadow-overlay outline-none',
              SIZE[size],
            )}
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="flex items-start justify-between gap-4 border-b border-hairline p-5">
              <div className="min-w-0 space-y-1">
                <h2 className="text-section-title text-ink">{title}</h2>
                {description ? (
                  <p className="text-small text-ink-secondary">{description}</p>
                ) : null}
              </div>
              <Button
                variant="ghost"
                size="sm"
                iconOnly
                leftIcon={X}
                onClick={onClose}
                aria-label="Close dialog"
              />
            </div>

            {children ? <div className="max-h-[60vh] overflow-y-auto p-5">{children}</div> : null}

            {footer ? (
              <div className="flex flex-wrap items-center justify-end gap-3 border-t border-hairline bg-surface-raised/60 p-4">
                {footer}
              </div>
            ) : null}
          </motion.div>
        </div>
      ) : null}
    </AnimatePresence>,
    document.body,
  );
}
