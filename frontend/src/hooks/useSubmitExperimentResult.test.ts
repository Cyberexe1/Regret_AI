import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { useSubmitExperimentResult } from './useSubmitExperimentResult';
import { mockFetchOnce } from '@/test/mockFetch';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('useSubmitExperimentResult', () => {
  it('submits a result and returns the response on success', async () => {
    mockFetchOnce({
      status: 201,
      body: {
        experiment_id: 'exp-1',
        result_id: 'res-1',
        reevaluation_id: 'reval-1',
        status: 'completed',
        decision_assessment: 'weakened',
        key_learning: 'Repeat rate came in below threshold.',
        next_step: 'Do not commit yet.',
      },
    });

    const { result } = renderHook(() => useSubmitExperimentResult());

    let response;
    await act(async () => {
      response = await result.current.submit('exp-1', { outcome: 'failure', summary: 'Test' });
    });

    expect(response).toMatchObject({ reevaluation_id: 'reval-1', decision_assessment: 'weakened' });
    await waitFor(() => expect(result.current.response?.reevaluation_id).toBe('reval-1'));
  });

  it('translates a 409 duplicate-submission response into a clear, specific message', async () => {
    mockFetchOnce({
      status: 409,
      body: {
        error: {
          code: 'CONFLICT',
          message: 'This experiment already has a submitted result and cannot be completed again.',
          request_id: 'req-789',
        },
        detail: 'This experiment already has a submitted result and cannot be completed again.',
      },
    });

    const { result } = renderHook(() => useSubmitExperimentResult());

    await act(async () => {
      await result.current.submit('exp-1', { outcome: 'success', summary: 'Test' });
    });

    expect(result.current.error?.isDuplicate).toBe(true);
    expect(result.current.error?.message).toBe('Results for this experiment have already been submitted.');
    // Never shows the raw API error message/JSON to the user.
    expect(result.current.error?.message).not.toContain('CONFLICT');
  });
});
