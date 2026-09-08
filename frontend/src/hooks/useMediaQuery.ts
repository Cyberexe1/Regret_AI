import { useEffect, useState } from 'react';

/** Subscribes to a CSS media query. Used to switch the sidebar to a drawer. */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    const list = window.matchMedia(query);
    const onChange = (event: MediaQueryListEvent) => setMatches(event.matches);

    setMatches(list.matches);
    list.addEventListener('change', onChange);
    return () => list.removeEventListener('change', onChange);
  }, [query]);

  return matches;
}

/** Matches the Tailwind `lg` breakpoint, where the sidebar becomes permanent. */
export function useIsDesktop(): boolean {
  return useMediaQuery('(min-width: 1024px)');
}
