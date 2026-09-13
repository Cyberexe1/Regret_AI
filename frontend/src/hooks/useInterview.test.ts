import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { useInterview } from './useInterview';
import { mockFetchSequence } from '@/test/mockFetch';

afterEach(() => {
  vi.unstubAllGlobals();
});

const BASE_STATE = {
  interview_id: 'int-1',
  decision_id: 'dec-1',
  user_id: 'user-1',
  status: 'awaiting_answer',
  turn_number: 0,
  max_turns: 7,
  decision_text: 'Should I move cities?',
  decision_type: null,
  selected_categories: [],
  desired_outcome: null,
  constraints: [],
  beliefs: [],
  uncertainties: [],
  alternatives: [],
  commitments: [],
  stakeholders: [],
  important_variables: [],
  evidence_summary: [],
  discovered_assumptions: [],
  discovered_unknowns: [],
  questions_asked: ['goal'],
  answers: [],
  current_question: 'What would make this decision successful?',
  readiness: 'early',
  readiness_reason: '',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const EMPTY_EXTRACTED = {
  desired_outcome: null,
  constraints: [],
  beliefs: [],
  uncertainties: [],
  alternatives: [],
  commitments: [],
  stakeholders: [],
  important_variables: [],
  evidence_mentions: [],
  discovered_assumptions: [],
  discovered_unknowns: [],
};

describe('useInterview', () => {
  it('starts the interview and records the first question as a REGRET message', async () => {
    mockFetchSequence([
      {
        status: 200,
        body: { interview_id: 'int-1', first_question: BASE_STATE.current_question, state: BASE_STATE },
      },
    ]);

    const { result } = renderHook(() => useInterview());

    await act(async () => {
      await result.current.start('dec-1', ['career']);
    });

    expect(result.current.stage).toBe('awaiting-answer');
    expect(result.current.interviewId).toBe('int-1');
    expect(result.current.messages).toEqual([
      { id: expect.any(String), role: 'regret', text: BASE_STATE.current_question },
    ]);
  });

  it('sends an answer and appends both the user message and the next question', async () => {
    mockFetchSequence([
      {
        status: 200,
        body: { interview_id: 'int-1', first_question: BASE_STATE.current_question, state: BASE_STATE },
      },
      {
        status: 200,
        body: {
          response: 'What could realistically limit this decision?',
          extracted_fields: { ...EMPTY_EXTRACTED, desired_outcome: 'A calmer life' },
          current_state: { ...BASE_STATE, turn_number: 1, desired_outcome: 'A calmer life' },
          next_question: 'What could realistically limit this decision?',
          readiness: 'early',
          turn_number: 1,
          suggested_chips: [],
          agent_available: true,
        },
      },
    ]);

    const { result } = renderHook(() => useInterview());

    await act(async () => {
      await result.current.start('dec-1', []);
    });
    await act(async () => {
      await result.current.respond('A calmer life');
    });

    expect(result.current.stage).toBe('awaiting-answer');
    expect(result.current.messages.map((m) => m.role)).toEqual(['regret', 'user', 'regret']);
    expect(result.current.messages.at(-1)?.text).toBe('What could realistically limit this decision?');
    expect(result.current.state?.desired_outcome).toBe('A calmer life');
  });

  it('moves to the "ready" stage once the backend returns no next question', async () => {
    mockFetchSequence([
      {
        status: 200,
        body: { interview_id: 'int-1', first_question: BASE_STATE.current_question, state: BASE_STATE },
      },
      {
        status: 200,
        body: {
          response: "I've identified the main uncertainties worth testing.",
          extracted_fields: EMPTY_EXTRACTED,
          current_state: { ...BASE_STATE, turn_number: 5, status: 'ready', current_question: null },
          next_question: null,
          readiness: 'ready',
          turn_number: 5,
          suggested_chips: [],
          agent_available: true,
        },
      },
    ]);

    const { result } = renderHook(() => useInterview());

    await act(async () => {
      await result.current.start('dec-1', []);
    });
    await act(async () => {
      await result.current.respond('That covers it.');
    });

    expect(result.current.stage).toBe('ready');
    expect(result.current.readiness).toBe('ready');
  });

  it('shows the fallback-agent notice when a turn falls back to a deterministic question', async () => {
    mockFetchSequence([
      {
        status: 200,
        body: { interview_id: 'int-1', first_question: BASE_STATE.current_question, state: BASE_STATE },
      },
      {
        status: 200,
        body: {
          response: 'What could realistically limit this decision?',
          extracted_fields: EMPTY_EXTRACTED,
          current_state: { ...BASE_STATE, turn_number: 1 },
          next_question: 'What could realistically limit this decision?',
          readiness: 'early',
          turn_number: 1,
          suggested_chips: [],
          agent_available: false,
        },
      },
    ]);

    const { result } = renderHook(() => useInterview());

    await act(async () => {
      await result.current.start('dec-1', []);
    });
    await act(async () => {
      await result.current.respond('A calmer life');
    });

    expect(result.current.agentAvailable).toBe(false);
  });

  it('completes the interview and stores the returned DecisionSnapshot', async () => {
    mockFetchSequence([
      {
        status: 200,
        body: { interview_id: 'int-1', first_question: BASE_STATE.current_question, state: BASE_STATE },
      },
      {
        status: 200,
        body: {
          snapshot: {
            decision: 'Should I move cities?',
            goal: 'A calmer life',
            constraints: [],
            commitments: [],
            beliefs: [],
            uncertainties: [],
            alternatives: [],
            evidence: [],
            important_variables: [],
            stakeholders: [],
            decision_criteria: [],
            missing_information: [],
            interview_summary: 'Interview covered 1 topic(s) over 1 turn(s).',
          },
          readiness: 'enough',
          missing_information: [],
        },
      },
    ]);

    const { result } = renderHook(() => useInterview());

    await act(async () => {
      await result.current.start('dec-1', []);
    });
    await act(async () => {
      await result.current.complete();
    });

    await waitFor(() => expect(result.current.stage).toBe('completed'));
    expect(result.current.snapshot?.goal).toBe('A calmer life');
  });

  it('surfaces a network/API error without losing the conversation so far', async () => {
    mockFetchSequence([
      {
        status: 200,
        body: { interview_id: 'int-1', first_question: BASE_STATE.current_question, state: BASE_STATE },
      },
      { status: 500, body: { error: { code: 'INTERNAL_ERROR', message: 'Something broke.', request_id: 'r1' }, detail: 'Something broke.' } },
    ]);

    const { result } = renderHook(() => useInterview());

    await act(async () => {
      await result.current.start('dec-1', []);
    });
    await act(async () => {
      await result.current.respond('A calmer life');
    });

    expect(result.current.error?.message).toBe('Something broke.');
    // The user's own message is still shown, even though the request failed.
    expect(result.current.messages.some((m) => m.role === 'user' && m.text === 'A calmer life')).toBe(true);
  });
});
