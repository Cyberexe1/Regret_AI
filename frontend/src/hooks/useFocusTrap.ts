import { useEffect, type RefObject } from 'react';

/**
 * Elements that can receive focus. `[tabindex="-1"]` is excluded on purpose:
 * those are programmatic focus targets (like an overlay container), not stops
 * in the Tab order.
 */
const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

/** Tab stops inside `container`, in document order, skipping hidden ones. */
function tabStops(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (element) => element.offsetParent !== null || element === document.activeElement,
  );
}

export interface FocusTrapOptions {
  /**
   * Keep Tab inside the container. True for modal surfaces (the mobile
   * navigation drawer), false for non-modal popovers, which should let Tab
   * move on and close themselves instead.
   */
  trapTab?: boolean;
}

/**
 * Focus management for an overlay that mounts while `active`.
 *
 * On activation focus moves to the first tab stop, or to the container itself
 * when it holds none. On deactivation focus returns to whatever was focused
 * beforehand, so dismissing an overlay never dumps the user back at the top of
 * the document. Optionally cycles Tab within the container.
 *
 * The container must be focusable as a fallback: give it `tabIndex={-1}`.
 */
export function useFocusTrap(
  active: boolean,
  containerRef: RefObject<HTMLElement | null>,
  { trapTab = true }: FocusTrapOptions = {},
): void {
  useEffect(() => {
    if (!active) return;

    const container = containerRef.current;
    if (!container) return;

    const previouslyFocused =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;

    // Deferred by a frame so entry animations and portalled children have
    // mounted before we decide what the first tab stop is.
    const frame = window.requestAnimationFrame(() => {
      if (container.contains(document.activeElement)) return;
      (tabStops(container)[0] ?? container).focus();
    });

    const onKeyDown = (event: KeyboardEvent) => {
      if (!trapTab || event.key !== 'Tab') return;

      const stops = tabStops(container);
      if (stops.length === 0) {
        // Nothing to move to, so Tab would otherwise escape the overlay.
        event.preventDefault();
        return;
      }

      const first = stops[0];
      const last = stops[stops.length - 1];

      if (!container.contains(document.activeElement)) {
        event.preventDefault();
        first.focus();
        return;
      }

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', onKeyDown);

    return () => {
      window.cancelAnimationFrame(frame);
      document.removeEventListener('keydown', onKeyDown);

      // A detached node ignores `focus()`, so a element that unmounted with the
      // overlay (a drawer link, say) is handled without a guard.
      previouslyFocused?.focus();
    };
  }, [active, containerRef, trapTab]);
}
