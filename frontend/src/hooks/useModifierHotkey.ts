import { useEffect } from 'react';

/**
 * Fires `handler` on Cmd+<key> (macOS) or Ctrl+<key> (Windows and Linux).
 * Pass a stable `handler` (e.g. from `useCallback`) to avoid re-binding.
 */
export function useModifierHotkey(key: string, handler: () => void): void {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() !== key.toLowerCase()) return;
      if (!event.metaKey && !event.ctrlKey) return;

      event.preventDefault();
      handler();
    };

    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [key, handler]);
}
