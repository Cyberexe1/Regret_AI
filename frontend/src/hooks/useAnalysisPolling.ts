import { useEffect, useRef, useState } from 'react';
import { analysisApi } from '@/api';
import type { AgentRunStatus, ApiAnalysisRunStatusResponse } from '@/api/types';
import { isAbortError } from '@/api/client';
import { describeApiError } from '@/lib/apiError';
import { stageLabel } from '@/lib/labels';

const POLL_INTERVAL_MS = 1500;
/** Stop retrying after this many consecutive failed polls, rather than
 * polling forever against a backend that's genuinely unreachable. */
const MAX_CONSECUTIVE_ERRORS = 5;

const TERMINAL_RUN_STATUSES = new Set(['completed', 'failed']);
const TERMINAL_STAGE_STATUSES = new Set<AgentRunStatus>(['completed', 'failed', 'skipped', 'unavailable']);

export interface StageEvent {
  id: string;
  stageId: string;
  label: string;
  status: AgentRunStatus;
  /** When this transition was first observed by the client (client clock, for display ordering only). */
  observedAt: number;
}

export interface AnalysisPollingState {
  /** Null until the first successful poll. */
  run: ApiAnalysisRunStatusResponse | null;
  isComplete: boolean;
  /** True once the run reaches a terminal status via `run.status`. */
  hasFailed: boolean;
  /** Real stage-completion events, in the order they were actually observed - never fabricated. */
  events: StageEvent[];
  error: { message: string; requestId: string | null } | null;
  isLoading: boolean;
  /** True once polling has given up after repeated consecutive failures. */
  isStalled: boolean;
}

/**
 * Polls a real analysis run's status every ~1.5s until it reaches a
 * terminal status (`completed`/`failed`), then stops. Replaces the old
 * scripted local simulation entirely - every value here comes from the
 * backend's actual `AnalysisRunStatusResponse`
 * (`GET /decisions/{id}/analysis/{runId}` or `/analysis/latest`).
 *
 * `events` is built by diffing consecutive polls: when a stage's status
 * changes, a new event is appended. This is a real observation of what
 * the backend reported, not a fabricated "finding" - REGRET ENGINE never
 * shows chain-of-thought or invents progress that didn't happen.
 */
export function useAnalysisPolling(
  decisionId: string | undefined,
  analysisRunId: string | undefined,
): AnalysisPollingState & { retry: () => void } {
  const [state, setState] = useState<AnalysisPollingState>({
    run: null,
    isComplete: false,
    hasFailed: false,
    events: [],
    error: null,
    isLoading: true,
    isStalled: false,
  });
  const [retryToken, setRetryToken] = useState(0);

  const previousStatuses = useRef<Partial<Record<string, AgentRunStatus>>>({});
  const eventsRef = useRef<StageEvent[]>([]);

  useEffect(() => {
    if (!decisionId) return;

    previousStatuses.current = {};
    eventsRef.current = [];
    let cancelled = false;
    let timeoutId: number | undefined;
    let consecutiveErrors = 0;
    const controller = new AbortController();

    async function poll() {
      try {
        const run = analysisRunId
          ? await analysisApi.getAnalysisStatus(decisionId!, analysisRunId, { signal: controller.signal })
          : await analysisApi.getLatestAnalysisStatus(decisionId!, { signal: controller.signal });

        if (cancelled) return;
        consecutiveErrors = 0;

        for (const [stageId, status] of Object.entries(run.stage_statuses)) {
          if (!status) continue;
          const prior = previousStatuses.current[stageId];
          if (prior !== status && TERMINAL_STAGE_STATUSES.has(status)) {
            eventsRef.current = [
              ...eventsRef.current,
              {
                id: `${stageId}-${status}-${eventsRef.current.length}`,
                stageId,
                label: stageLabel[stageId] ?? stageId,
                status,
                observedAt: Date.now(),
              },
            ];
          }
          previousStatuses.current[stageId] = status;
        }

        const isComplete = TERMINAL_RUN_STATUSES.has(run.status);
        setState({
          run,
          isComplete,
          hasFailed: run.status === 'failed',
          events: eventsRef.current,
          error: null,
          isLoading: false,
          isStalled: false,
        });

        if (!isComplete && !cancelled) {
          timeoutId = window.setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (error) {
        if (cancelled || isAbortError(error)) return;
        consecutiveErrors += 1;
        const stalled = consecutiveErrors >= MAX_CONSECUTIVE_ERRORS;
        setState((current) => ({
          ...current,
          error: describeApiError(error),
          isLoading: false,
          isStalled: stalled,
        }));
        // Retry a bounded number of times on a transient failure - a single
        // dropped request must not strand the user, but a backend that's
        // genuinely unreachable must eventually stop and say so rather than
        // polling forever.
        if (!stalled) timeoutId = window.setTimeout(poll, POLL_INTERVAL_MS);
      }
    }

    void poll();

    return () => {
      cancelled = true;
      controller.abort();
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
    };
  }, [decisionId, analysisRunId, retryToken]);

  return { ...state, retry: () => setRetryToken((token) => token + 1) };
}
