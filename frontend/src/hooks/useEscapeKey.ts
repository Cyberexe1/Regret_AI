import { useEffect, useRef } from 'react';

/**
 * Calls `onEscape` while `active`, used by overlays for dismissal.
 *
 * The callback is held in a ref, so an inline arrow function from the caller
 * does not rebind the listener on every render. Only toggling `active`
 * subscribes or unsubscribes.
 */
export function useEscapeKey(active: boolean, onEscape: () => void): void {
  const handler = useRef(onEscape);

  useEffect(() => {
    handler.current = onEscape;
  }, [onEscape]);

  useEffect(() => {
    if (!active) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') handler.current();
    };

    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [active]);
}
