import { afterEach, describe, expect, it, vi } from 'vitest';
import { createDecision, listDecisions } from './decisions';
import { mockFetchOnce } from '@/test/mockFetch';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('decisions API', () => {
  it('creates a decision via POST /decisions with the exact backend contract', async () => {
    const mock = mockFetchOnce({
      status: 201,
      body: {
        id: 'dec-1',
        title: 'Open a bakery',
        description: 'Should I open a second bakery location?',
        desired_outcome: null,
        budget: null,
        currency: null,
        timeline: null,
        location: null,
        risk_tolerance: null,
        beliefs: null,
        status: 'draft',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    });

    const result = await createDecision({
      title: 'Open a bakery',
      description: 'Should I open a second bakery location?',
    });

    expect(result.id).toBe('dec-1');
    expect(result.status).toBe('draft');
    const [, init] = mock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toMatchObject({ title: 'Open a bakery' });
  });

  it('lists decisions with cursor pagination fields intact', async () => {
    mockFetchOnce({
      status: 200,
      body: { items: [{ id: 'dec-1' }], next_cursor: 'abc123' },
    });

    const result = await listDecisions({ limit: 20 });

    expect(result.items).toHaveLength(1);
    expect(result.next_cursor).toBe('abc123');
  });
});
