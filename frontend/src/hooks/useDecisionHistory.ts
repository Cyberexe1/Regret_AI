import { useCallback, useEffect, useRef, useState } from 'react';
import { decisionsApi } from '@/api';
import type { ApiDecision } from '@/api/types';
import { isAbortError } from '@/api/client';
import { describeApiError } from '@/lib/apiError';

/** Mirrors the backend's real `DecisionStatus` enum, plus "all". */
export const DECISION_FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'draft', label: 'Draft' },
  { id: 'analyzing', label: 'Analyzing' },
  { id: 'completed', label: 'Analysis complete' },
  { id: 'needs_validation', label: 'Needs validation' },
  { id: 'archived', label: 'Archived' },
] as const;

export type DecisionFilterId = (typeof DECISION_FILTERS)[number]['id'];

export interface DecisionHistoryOptions {
  query: string;
  filter: DecisionFilterId;
}

export interface DecisionHistory {
  /** Rows after client-side search/filter, applied to whatever pages have
   * been fetched so far via the backend's cursor pagination. */
  rows: ApiDecision[];
  /** Total decisions loaded so far, ignoring search/filter. */
  loadedCount: number;
  isWorkspaceEmpty: boolean;
  isLoading: boolean;
  error: { message: string; requestId: string | null } | null;
  /** True if the backend reported a `next_cursor` - there are more pages
   * beyond what's currently loaded. */
  hasMore: boolean;
  isLoadingMore: boolean;
  loadMore: () => void;
  retry: () => void;
}

const PAGE_SIZE = 20;

/**
 * Loads decisions from the backend's real cursor-paginated
 * `GET /decisions` endpoint - never offset pagination, since the backend
 * doesn't support it (see `DecisionListResponse.next_cursor`). Search and
 * status filtering are applied client-side to whatever pages have been
 * loaded so far; each `loadMore()` call fetches exactly one more page
 * using the backend's own opaque cursor, never re-deriving one.
 */
export function useDecisionHistory({ query, filter }: DecisionHistoryOptions): DecisionHistory {
  const [allDecisions, setAllDecisions] = useState<ApiDecision[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<{ message: string; requestId: string | null } | null>(null);
  const [retryToken, setRetryToken] = useState(0);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    controllerRef.current = controller;
    setIsLoading(true);
    setError(null);

    decisionsApi
      .listDecisions({ limit: PAGE_SIZE }, { signal: controller.signal })
      .then((response) => {
        setAllDecisions(response.items);
        setCursor(response.next_cursor);
        setHasMore(Boolean(response.next_cursor));
        setIsLoading(false);
      })
      .catch((fetchError: unknown) => {
        if (isAbortError(fetchError)) return;
        setError(describeApiError(fetchError));
        setIsLoading(false);
      });

    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [retryToken]);

  const loadMore = useCallback(() => {
    if (!cursor || isLoadingMore) return;
    setIsLoadingMore(true);

    decisionsApi
      .listDecisions({ limit: PAGE_SIZE, cursor })
      .then((response) => {
        setAllDecisions((current) => [...current, ...response.items]);
        setCursor(response.next_cursor);
        setHasMore(Boolean(response.next_cursor));
        setIsLoadingMore(false);
      })
      .catch((fetchError: unknown) => {
        setError(describeApiError(fetchError));
        setIsLoadingMore(false);
      });
  }, [cursor, isLoadingMore]);

  const needle = query.trim().toLowerCase();
  const rows = allDecisions
    .filter((decision) => filter === 'all' || decision.status === filter)
    .filter((decision) => {
      if (!needle) return true;
      return (
        decision.title.toLowerCase().includes(needle) ||
        decision.description.toLowerCase().includes(needle) ||
        decision.id.toLowerCase().includes(needle)
      );
    })
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at));

  return {
    rows,
    loadedCount: allDecisions.length,
    isWorkspaceEmpty: !isLoading && allDecisions.length === 0,
    isLoading,
    error,
    hasMore,
    isLoadingMore,
    loadMore,
    retry: () => setRetryToken((token) => token + 1),
  };
}
