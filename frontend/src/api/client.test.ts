import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiClient, ApiError } from './client';
import { mockFetchOnce } from '@/test/mockFetch';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('apiClient', () => {
  it('parses a successful JSON response', async () => {
    mockFetchOnce({ status: 200, body: { id: 'dec-1', title: 'Test decision' } });

    const result = await apiClient.get<{ id: string; title: string }>('/decisions/dec-1');

    expect(result).toEqual({ id: 'dec-1', title: 'Test decision' });
  });

  it('throws an ApiError with the backend standardized error envelope', async () => {
    mockFetchOnce({
      status: 404,
      body: {
        error: { code: 'NOT_FOUND', message: 'Decision not found.', request_id: 'req-123' },
        detail: 'Decision not found.',
      },
    });

    await expect(apiClient.get('/decisions/unknown')).rejects.toMatchObject({
      message: 'Decision not found.',
      code: 'NOT_FOUND',
      requestId: 'req-123',
      status: 404,
    });
  });

  it('throws an ApiError instance specifically, not a generic Error', async () => {
    mockFetchOnce({
      status: 409,
      body: {
        error: { code: 'CONFLICT', message: 'Already submitted.', request_id: 'req-456' },
        detail: 'Already submitted.',
      },
    });

    await expect(apiClient.post('/experiments/exp-1/results', {})).rejects.toBeInstanceOf(ApiError);
  });

  it('never leaks a stack trace or raw exception text to the caller', async () => {
    mockFetchOnce({ status: 500, body: { not: 'the expected envelope shape' } });

    try {
      await apiClient.get('/decisions');
      expect.fail('should have thrown');
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).message).not.toContain('at ');
      expect((error as ApiError).message).not.toContain('.ts:');
    }
  });

  it('surfaces a network failure as an ApiError with isNetworkError=true', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    await expect(apiClient.get('/decisions')).rejects.toMatchObject({
      isNetworkError: true,
      code: 'NETWORK_ERROR',
    });
  });
});
