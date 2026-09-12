import { useEffect, useRef, type RefObject } from 'react';

/**
 * Calls `onOutside` when a pointer goes down outside `containerRef` while
 * `active`.
 *
 * Uses `pointerdown` rather than `click` for two reasons: it covers mouse, pen
 * and touch with one listener, and it dismisses on press instead of waiting for
 * release, which is what makes a popover feel like it belongs to the platform.
 */
export function useOutsidePointerDown(
  active: boolean,
  containerRef: RefObject<HTMLElement | null>,
  onOutside: () => void,
): void {
  const handler = useRef(onOutside);

  useEffect(() => {
    handler.current = onOutside;
  }, [onOutside]);

  useEffect(() => {
    if (!active) return;

    const onPointerDown = (event: PointerEvent) => {
      const container = containerRef.current;
      if (!container) return;
      if (!container.contains(event.target as Node)) handler.current();
    };

    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  }, [active, containerRef]);
}
