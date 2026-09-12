import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { cn } from '@/lib/cn';
import { DURATION } from '@/lib/motion';

export type TooltipSide = 'top' | 'bottom' | 'left' | 'right';

const OFFSET: Record<TooltipSide, { x: number; y: number }> = {
  top: { x: 0, y: 4 },
  bottom: { x: 0, y: -4 },
  left: { x: 4, y: 0 },
  right: { x: -4, y: 0 },
};

const VIEWPORT_GUTTER = 12;
const TRIGGER_GAP = 8;

export interface TooltipProps {
  content: ReactNode;
  side?: TooltipSide;
  /** Trigger content is wrapped in a focusable control for keyboard and touch access. */
  children: ReactNode;
  className?: string;
}

interface TooltipPosition {
  side: TooltipSide;
  style: CSSProperties;
}

export function Tooltip({ content, side = 'top', children, className }: TooltipProps) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<TooltipPosition>({
    side,
    style: { left: 0, top: 0, visibility: 'hidden' },
  });
  const triggerRef = useRef<HTMLButtonElement>(null);
  const tooltipRef = useRef<HTMLSpanElement>(null);
  const reduceMotion = useReducedMotion();
  const id = useId();

  const updatePosition = useCallback(() => {
    const trigger = triggerRef.current?.getBoundingClientRect();
    const tooltip = tooltipRef.current?.getBoundingClientRect();
    if (!trigger || !tooltip) return;

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    let resolvedSide = side;

    if (side === 'top' && trigger.top - tooltip.height - TRIGGER_GAP < VIEWPORT_GUTTER) {
      resolvedSide = 'bottom';
    } else if (
      side === 'bottom' &&
      trigger.bottom + tooltip.height + TRIGGER_GAP > viewportHeight - VIEWPORT_GUTTER
    ) {
      resolvedSide = 'top';
    } else if (side === 'left' && trigger.left - tooltip.width - TRIGGER_GAP < VIEWPORT_GUTTER) {
      resolvedSide = 'right';
    } else if (
      side === 'right' &&
      trigger.right + tooltip.width + TRIGGER_GAP > viewportWidth - VIEWPORT_GUTTER
    ) {
      resolvedSide = 'left';
    }

    let left = trigger.left + trigger.width / 2 - tooltip.width / 2;
    let top = trigger.top + trigger.height / 2 - tooltip.height / 2;

    if (resolvedSide === 'top') top = trigger.top - tooltip.height - TRIGGER_GAP;
    if (resolvedSide === 'bottom') top = trigger.bottom + TRIGGER_GAP;
    if (resolvedSide === 'left') left = trigger.left - tooltip.width - TRIGGER_GAP;
    if (resolvedSide === 'right') left = trigger.right + TRIGGER_GAP;

    left = Math.min(
      Math.max(left, VIEWPORT_GUTTER),
      Math.max(VIEWPORT_GUTTER, viewportWidth - tooltip.width - VIEWPORT_GUTTER),
    );
    top = Math.min(
      Math.max(top, VIEWPORT_GUTTER),
      Math.max(VIEWPORT_GUTTER, viewportHeight - tooltip.height - VIEWPORT_GUTTER),
    );

    setPosition({ side: resolvedSide, style: { left, top, visibility: 'visible' } });
  }, [side]);

  useEffect(() => {
    if (!open) return;

    const frame = window.requestAnimationFrame(updatePosition);
    const closeOnOutsidePointer = (event: PointerEvent) => {
      if (!triggerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };

    window.addEventListener('resize', updatePosition);
    window.addEventListener('scroll', updatePosition, true);
    document.addEventListener('pointerdown', closeOnOutsidePointer);
    document.addEventListener('keydown', closeOnEscape);

    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener('resize', updatePosition);
      window.removeEventListener('scroll', updatePosition, true);
      document.removeEventListener('pointerdown', closeOnOutsidePointer);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [open, updatePosition]);

  const tooltip = (
    <AnimatePresence>
      {open ? (
        <motion.span
          ref={tooltipRef}
          id={id}
          role="tooltip"
          className="pointer-events-none fixed z-70 w-max max-w-[min(16rem,calc(100vw-1.5rem))] rounded-md border border-hairline-strong bg-surface-overlay px-2.5 py-1.5 text-left text-small text-ink-secondary shadow-overlay"
          style={position.style}
          initial={reduceMotion ? false : { opacity: 0, ...OFFSET[position.side] }}
          animate={{ opacity: 1, x: 0, y: 0 }}
          exit={reduceMotion ? undefined : { opacity: 0, ...OFFSET[position.side] }}
          transition={{ duration: reduceMotion ? 0 : DURATION.micro }}
        >
          {content}
        </motion.span>
      ) : null}
    </AnimatePresence>
  );

  return (
    <span
      className={cn('inline-flex', className)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        ref={triggerRef}
        type="button"
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
        className="inline-flex min-w-0 cursor-help items-center rounded-sm text-left"
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen(true)}
      >
        {children}
      </button>

      {typeof document === 'undefined' ? null : createPortal(tooltip, document.body)}
    </span>
  );
}
