import { useEffect, useRef, useState } from 'react';
import { analysisApi } from '@/api';
import { describeApiError, isNotFoundError } from '@/lib/apiError';
import { useAnalysisPolling } from './useAnalysisPolling';

export type AnalysisTriggerState = 'checking' | 'starting' | 'polling' | 'trigger-failed';

export interface AnalysisRunState {
  triggerState: AnalysisTriggerState;
  triggerError: { message: string; requestId: string | null } | null;
}

/**
 * Ensures a decision has an analysis run, then hands off to
 * `useAnalysisPolling` to track its live progress.
 *
 * On mount:
 *   1. Check whether the decision already has a run at all
 *      (`GET /analysis/latest`).
 *   2. If none exists yet, trigger one (`POST /analyze`) - fire-and-track,
 *      never awaited by rendering, since the backend call is synchronous
 *      and can take up to its configured `ANALYSIS_MAX_DURATION_SECONDS`
 *      (10 minutes by default); the concurrent polling loop is what
 *      actually surfaces live progress while that request is in flight.
 *   3. If a run already exists (active or terminal), never start a
 *      second one - revisiting this page must not silently re-run the
 *      whole pipeline. The backend's own idempotency
 *      (`AnalysisOrchestrator.run_analysis`) would prevent a duplicate
 *      pipeline anyway, but this hook avoids even making that redundant
 *      call.
 */
export function useAnalysisRun(decisionId: string | undefined) {
  const [trigger, setTrigger] = useState<AnalysisRunState>({
    triggerState: 'checking',
    triggerError: null,
  });
  const startedRef = useRef(false);

  useEffect(() => {
    if (!decisionId) return;
    startedRef.current = false;
    setTrigger({ triggerState: 'checking', triggerError: null });

    let cancelled = false;

    async function ensureRunExists() {
      try {
        await analysisApi.getLatestAnalysisStatus(decisionId!);
        if (cancelled) return;
        setTrigger({ triggerState: 'polling', triggerError: null });
      } catch (error) {
        if (cancelled) return;
        if (!isNotFoundError(error)) {
          // Some other failure checking for an existing run (network,
          // 500, etc.) - still attempt to poll; useAnalysisPolling
          // surfaces its own error state if that also fails.
          setTrigger({ triggerState: 'polling', triggerError: null });
          return;
        }

        // No run exists yet for this decision - start one.
        if (startedRef.current) return;
        startedRef.current = true;
        setTrigger({ triggerState: 'starting', triggerError: null });

        try {
          await analysisApi.startAnalysis(decisionId!);
          // The polling hook picks up the now-existing run via /latest;
          // nothing further to do here on success.
        } catch (startError) {
          if (cancelled) return;
          setTrigger({ triggerState: 'trigger-failed', triggerError: describeApiError(startError) });
          return;
        }
        if (!cancelled) setTrigger({ triggerState: 'polling', triggerError: null });
      }
    }

    void ensureRunExists();

    return () => {
      cancelled = true;
    };
  }, [decisionId]);

  const polling = useAnalysisPolling(
    decisionId,
    // Always resolve via "latest" - the run id isn't known until the
    // trigger above (or a prior visit) has created one.
    undefined,
  );

  return { ...trigger, ...polling };
}
