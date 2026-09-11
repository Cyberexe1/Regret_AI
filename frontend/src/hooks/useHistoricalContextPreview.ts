import { useEffect, useRef, useState } from 'react';
import { historicalContextApi } from '@/api';
import { isAbortError } from '@/api/client';
import type { ApiHistoricalContext } from '@/api/types';
import { buildHistoricalContext } from '@/lib/buildHistoricalContext';
import type { HistoricalContextSummary } from '@/types/report';

/** Below this, comparing against past decisions is too thin to be
 * useful - matches the backend's own minimum decision `description`
 * length (`min_length=1`) but adds a slightly higher bar so the preview
 * doesn't fire on a single keystroke. */
const MIN_DESCRIPTION_LENGTH = 15;
const DEBOUNCE_MS = 600;

export interface HistoricalContextPreviewState {
  isLoading: boolean;
  summary: HistoricalContextSummary | null;
}

/**
 * Debounced "Relevant from your past decisions" preview for the
 * new-decision intake page (REGRET ENGINE 2.0). Fires
 * `POST /decisions/historical-context/preview` only once the user has
 * typed enough decision text to make a comparison meaningful, and only
 * after `DEBOUNCE_MS` of no further typing - never on every keystroke.
 * Nothing is persisted server-side (see the backend route's own
 * docstring); this is read-only, best-effort context.
 */
export function useHistoricalContextPreview(decisionText: string): HistoricalContextPreviewState {
  const [summary, setSummary] = useState<HistoricalContextSummary | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const latestText = useRef(decisionText);
  latestText.current = decisionText;

  useEffect(() => {
    const trimmed = decisionText.trim();
    if (trimmed.length < MIN_DESCRIPTION_LENGTH) {
      setSummary(null);
      setIsLoading(false);
      return;
    }

    const controller = new AbortController();
    setIsLoading(true);

    const timeoutId = window.setTimeout(() => {
      historicalContextApi
        .previewHistoricalContext(
          { title: trimmed.slice(0, 200), description: trimmed },
          { signal: controller.signal },
        )
        .then((response: ApiHistoricalContext) => {
          if (controller.signal.aborted) return;
          setSummary(buildHistoricalContext(response));
        })
        .catch((error: unknown) => {
          if (isAbortError(error)) return;
          // A failed preview must never block the intake flow - it simply
          // shows nothing, exactly like "no similar decisions found".
          setSummary(null);
        })
        .finally(() => {
          if (!controller.signal.aborted) setIsLoading(false);
        });
    }, DEBOUNCE_MS);

    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [decisionText]);

  return { isLoading, summary };
}
