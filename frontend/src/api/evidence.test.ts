import { afterEach, describe, expect, it, vi } from 'vitest';
import { uploadEvidence } from './evidence';
import { mockFetchOnce } from '@/test/mockFetch';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('evidence API', () => {
  it('uploads via multipart/form-data with field name "file", never inline JSON', async () => {
    const mock = mockFetchOnce({
      status: 201,
      body: {
        id: 'evd-1',
        decision_id: 'dec-1',
        title: 'notes.txt',
        source_type: 'document',
        source_url: null,
        storage_key: 'abc.txt',
        filename: 'notes.txt',
        file_type: 'txt',
        size_bytes: 12,
        page_count: null,
        content_reference: 'hello world',
        content_truncated: false,
        credibility: null,
        created_at: '2026-01-01T00:00:00Z',
      },
    });

    const file = new File(['hello world'], 'notes.txt', { type: 'text/plain' });
    const result = await uploadEvidence('dec-1', file);

    expect(result.id).toBe('evd-1');
    const [, init] = mock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe('POST');
    // Body must be FormData, never a JSON string with inline file contents.
    expect(init.body).toBeInstanceOf(FormData);
    const form = init.body as FormData;
    expect(form.get('file')).toBe(file);
    // No Content-Type header set manually - the browser sets the correct
    // multipart boundary itself when a fetch body is FormData.
    expect((init.headers as Record<string, string> | undefined)?.['Content-Type']).toBeUndefined();
  });
});
