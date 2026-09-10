import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useAnalysisPolling } from './useAnalysisPolling';
import { mockFetchSequence } from '@/test/mockFetch';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function statusBody(overrides: Record<string, unknown> = {}) {
  return {
    analysis_run_id: 'run-1',
    decision_id: 'dec-1',
    status: 'running',
    current_stage: 'assumption_hunter',
    stage_statuses: { decision_analyzer: 'completed', assumption_hunter: 'running' },
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:01Z',
    error_message: null,
    ...overrides,
  };
}

describe('useAnalysisPolling', () => {
  it('stops polling once the run reaches a terminal status', async () => {
    mockFetchSequence([
      { status: 200, body: statusBody({ status: 'running' }) },
      {
        status: 200,
        body: statusBody({
          status: 'completed',
          current_stage: null,
          stage_statuses: { decision_analyzer: 'completed', assumption_hunter: 'completed' },
        }),
      },
    ]);

    const { result } = renderHook(() => useAnalysisPolling('dec-1', 'run-1'));

    await waitFor(() => expect(result.current.isComplete).toBe(true), { timeout: 5000 });

    expect(result.current.hasFailed).toBe(false);
    expect(result.current.run?.status).toBe('completed');
  });

  it('records real stage-completion events without fabricating any', async () => {
    mockFetchSequence([
      {
        status: 200,
        body: statusBody({
          status: 'completed',
          current_stage: null,
          stage_statuses: { decision_analyzer: 'completed', assumption_hunter: 'failed' },
        }),
      },
    ]);

    const { result } = renderHook(() => useAnalysisPolling('dec-1', 'run-1'));

    await waitFor(() => expect(result.current.isComplete).toBe(true));

    const stageIds = result.current.events.map((event) => event.stageId);
    expect(stageIds).toContain('decision_analyzer');
    expect(stageIds).toContain('assumption_hunter');
    expect(result.current.events.find((e) => e.stageId === 'assumption_hunter')?.status).toBe('failed');
  });

  it('surfaces a failed run as hasFailed=true', async () => {
    mockFetchSequence([
      {
        status: 200,
        body: statusBody({ status: 'failed', current_stage: null, error_message: 'The analysis failed.' }),
      },
    ]);

    const { result } = renderHook(() => useAnalysisPolling('dec-1', 'run-1'));

    await waitFor(() => expect(result.current.isComplete).toBe(true));
    expect(result.current.hasFailed).toBe(true);
    expect(result.current.run?.error_message).toBe('The analysis failed.');
  });
});
