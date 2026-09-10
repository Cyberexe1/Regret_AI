import { useCallback, useEffect, useRef, useState } from 'react';
import { isAbortError } from '@/api/client';
import { describeApiError } from '@/lib/apiError';

export type AsyncStatus = 'idle' | 'loading' | 'success' | 'error';

export interface AsyncState<T> {
  status: AsyncStatus;
  data: T | null;
  error: { message: string; requestId: string | null } | null;
  isLoading: boolean;
}

/**
 * Small, shared data-fetching primitive used by every page-level hook in
 * this app instead of introducing a fetching library. Handles the three
 * things every API-backed page needs: loading/error/success state,
 * cancellation on unmount (so a slow request can never set state on an
 * unmounted component), and re-fetching on demand via `refetch`.
 *
 * Deliberately minimal - no caching, no request de-duplication, no
 * background refetch. If those become necessary later, that is the point
 * to reach for a real library rather than growing this further.
 */
export function useAsync<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: React.DependencyList,
): AsyncState<T> & { refetch: () => void } {
  const [state, setState] = useState<AsyncState<T>>({
    status: 'idle',
    data: null,
    error: null,
    isLoading: true,
  });
  const [refetchToken, setRefetchToken] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    setState((current) => ({ ...current, status: 'loading', isLoading: true, error: null }));

    fetcherRef
      .current(controller.signal)
      .then((data) => {
        if (!active) return;
        setState({ status: 'success', data, error: null, isLoading: false });
      })
      .catch((error: unknown) => {
        if (!active || isAbortError(error)) return;
        setState({ status: 'error', data: null, error: describeApiError(error), isLoading: false });
      });

    return () => {
      active = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, refetchToken]);

  const refetch = useCallback(() => setRefetchToken((token) => token + 1), []);

  return { ...state, refetch };
}
