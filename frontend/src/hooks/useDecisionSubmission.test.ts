import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { useDecisionSubmission } from './useDecisionSubmission';
import { mockFetchSequence } from '@/test/mockFetch';
import { emptyDecisionDraft } from '@/lib/decisionDraft';
import type { DecisionDraftWithFiles } from './useDecisionIntake';

function draft(overrides: Partial<DecisionDraftWithFiles> = {}): DecisionDraftWithFiles {
  return { ...emptyDecisionDraft, decision: 'Should I open a bakery?', evidence: [], ...overrides };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('useDecisionSubmission', () => {
  it('creates the decision and uploads every attached evidence file', async () => {
    const file = new File(['evidence'], 'notes.txt', { type: 'text/plain' });
    mockFetchSequence([
      {
        status: 201,
        body: {
          id: 'dec-1',
          title: 'Should I open a bakery?',
          description: 'Should I open a bakery?',
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
      },
      {
        status: 201,
        body: {
          id: 'evd-1',
          decision_id: 'dec-1',
          title: 'notes.txt',
          source_type: 'document',
          source_url: null,
          storage_key: 'k1',
          filename: 'notes.txt',
          file_type: 'txt',
          size_bytes: 8,
          page_count: null,
          content_reference: 'evidence',
          content_truncated: false,
          credibility: null,
          created_at: '2026-01-01T00:00:00Z',
        },
      },
    ]);

    const { result } = renderHook(() => useDecisionSubmission());

    let decisionId: string | null = null;
    await act(async () => {
      decisionId = await result.current.submit(
        draft({ evidence: [{ id: 'f1', name: 'notes.txt', size: 8, mimeType: 'text/plain', file }] }),
      );
    });

    expect(decisionId).toBe('dec-1');
    await waitFor(() => expect(result.current.stage).toBe('done'));
    expect(result.current.evidenceOutcomes).toEqual([{ fileName: 'notes.txt', ok: true }]);
  });

  it('never loses the created decision when an evidence upload fails', async () => {
    const file = new File(['evidence'], 'bad.exe', { type: 'application/octet-stream' });
    mockFetchSequence([
      {
        status: 201,
        body: {
          id: 'dec-2',
          title: 'Should I open a bakery?',
          description: 'Should I open a bakery?',
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
      },
      {
        status: 415,
        body: {
          error: { code: 'UNSUPPORTED_MEDIA_TYPE', message: "File type '.exe' is not supported.", request_id: 'r1' },
          detail: "File type '.exe' is not supported.",
        },
      },
    ]);

    const { result } = renderHook(() => useDecisionSubmission());

    let decisionId: string | null = null;
    await act(async () => {
      decisionId = await result.current.submit(
        draft({ evidence: [{ id: 'f1', name: 'bad.exe', size: 8, mimeType: 'application/octet-stream', file }] }),
      );
    });

    // The decision id is still returned - a failed upload never discards it.
    expect(decisionId).toBe('dec-2');
    await waitFor(() => expect(result.current.stage).toBe('done'));
    expect(result.current.evidenceOutcomes[0]?.ok).toBe(false);
  });
});
