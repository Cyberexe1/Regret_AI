import {
  useCallback,
  useLayoutEffect,
  useId,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { useEscapeKey } from '@/hooks/useEscapeKey';
import { useOutsidePointerDown } from '@/hooks/useOutsidePointerDown';
import { cn } from '@/lib/cn';
import { DURATION } from '@/lib/motion';

export type TooltipSide = 'top' | 'bottom' | 'left' | 'right';

/** Entry/exit travel per side, so the bubble drifts away from its trigger. */
const OFFSET: Record<TooltipSide, { x: number; y: number }> = {
  top: { x: 0, y: 4 },
  bottom: { x: 0, y: -4 },
  left: { x: 4, y: 0 },
  right: { x: -4, y: 0 },
};

const VIEWPORT_GUTTER = 12;
const TRIGGER_GAP = 8;

/** Off-screen until measured, so a first paint never lands in the wrong place. */
const UNMEASURED: TooltipPosition = {
  side: 'top',
  style: { left: 0, top: 0, visibility: 'hidden' },
};

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

/**
 * Describes its trigger on hover, focus and touch.
 *
 * Rendered into `document.body` so an ancestor with `overflow: hidden` cannot
 * clip it, then positioned against the live trigger rect and flipped to the
 * opposite side when the preferred one would leave the viewport.
 */
export function Tooltip({ content, side = 'top', children, className }: TooltipProps) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<TooltipPosition>(UNMEASURED);
  const wrapperRef = useRef<HTMLSpanElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const tooltipRef = useRef<HTMLSpanElement>(null);
  const reduceMotion = useReducedMotion();
  const id = useId();

  const close = useCallback(() => setOpen(false), []);

  const updatePosition = useCallback(() => {
    const trigger = triggerRef.current?.getBoundingClientRect();
    const tooltip = tooltipRef.current?.getBoundingClientRect();
    if (!trigger || !tooltip) return;

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    let resolvedSide = side;

    // Flip to the opposite side when the preferred one has no room.
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

    // Then keep the whole bubble inside the viewport on the cross axis.
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

  useEscapeKey(open, close);
  // Touch has no pointer-leave, so a tap elsewhere is what dismisses it.
  useOutsidePointerDown(open, wrapperRef, close);

  /**
   * Measured in a layout effect rather than an animation frame: the bubble
   * mounts in the same commit that opens it, so this runs before paint and the
   * user never sees it at a stale position from the previous opening.
   */
  useLayoutEffect(() => {
    if (!open) {
      setPosition((current) => (current === UNMEASURED ? current : UNMEASURED));
      return;
    }

    updatePosition();

    // `true` captures scrolls in any ancestor, not just the document.
    window.addEventListener('resize', updatePosition);
    window.addEventListener('scroll', updatePosition, true);

    return () => {
      window.removeEventListener('resize', updatePosition);
      window.removeEventListener('scroll', updatePosition, true);
    };
  }, [open, updatePosition]);

  /** Touch and pen have no hover, so pressing the trigger toggles instead. */
  const onPointerDown = (event: ReactPointerEvent<HTMLButtonElement>) => {
    if (event.pointerType === 'mouse') return;
    setOpen((value) => !value);
  };

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
      ref={wrapperRef}
      className={cn('inline-flex', className)}
      onPointerEnter={(event) => {
        if (event.pointerType === 'mouse') setOpen(true);
      }}
      onPointerLeave={(event) => {
        if (event.pointerType === 'mouse') setOpen(false);
      }}
    >
      <button
        ref={triggerRef}
        type="button"
        // A tooltip is a description, not a disclosure: `aria-describedby` is
        // the whole contract, and `aria-expanded` would misreport the trigger
        // as an expandable widget.
        aria-describedby={open ? id : undefined}
        className="inline-flex min-w-0 cursor-help items-center rounded-sm text-left"
        onFocus={() => setOpen(true)}
        onBlur={close}
        onPointerDown={onPointerDown}
      >
        {children}
      </button>

      {typeof document === 'undefined' ? null : createPortal(tooltip, document.body)}
    </span>
  );
}
