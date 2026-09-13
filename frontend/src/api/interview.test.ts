import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  completeInterview,
  getInterview,
  respondToInterview,
  skipInterview,
  startInterview,
} from './interview';
import { mockFetchOnce } from '@/test/mockFetch';

afterEach(() => {
  vi.unstubAllGlobals();
});

const STATE_BODY = {
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

describe('interview API', () => {
  it('starts an interview via POST /decisions/{id}/interview/start with the exact backend contract', async () => {
    const mock = mockFetchOnce({
      status: 200,
      body: { interview_id: 'int-1', first_question: 'What would make this decision successful?', state: STATE_BODY },
    });

    const result = await startInterview('dec-1', { selected_categories: ['career'] });

    expect(result.interview_id).toBe('int-1');
    const [url, init] = mock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/decisions/dec-1/interview/start');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({ selected_categories: ['career'] });
  });

  it('submits an answer via POST /interviews/{id}/respond, including the idempotency guard', async () => {
    const mock = mockFetchOnce({
      status: 200,
      body: {
        response: 'What could realistically limit this decision?',
        extracted_fields: {
          desired_outcome: 'A calmer life',
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
        },
        current_state: { ...STATE_BODY, turn_number: 1 },
        next_question: 'What could realistically limit this decision?',
        readiness: 'early',
        turn_number: 1,
        suggested_chips: [],
        agent_available: true,
      },
    });

    const result = await respondToInterview('int-1', {
      message: 'A calmer life',
      expected_turn_number: 0,
    });

    expect(result.turn_number).toBe(1);
    const [url, init] = mock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/interviews/int-1/respond');
    expect(JSON.parse(init.body as string)).toEqual({
      message: 'A calmer life',
      expected_turn_number: 0,
    });
  });

  it('fetches the current interview state via GET /interviews/{id}', async () => {
    mockFetchOnce({ status: 200, body: STATE_BODY });

    const result = await getInterview('int-1');

    expect(result.interview_id).toBe('int-1');
    expect(result.status).toBe('awaiting_answer');
  });

  it('completes an interview via POST /interviews/{id}/complete and returns a DecisionSnapshot', async () => {
    const mock = mockFetchOnce({
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
          interview_summary: 'Interview covered 1 topic(s) over 2 turn(s).',
        },
        readiness: 'enough',
        missing_information: [],
      },
    });

    const result = await completeInterview('int-1');

    expect(result.readiness).toBe('enough');
    const [url, init] = mock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/interviews/int-1/complete');
    expect(init.method).toBe('POST');
  });

  it('skips an interview via POST /interviews/{id}/skip and still returns a DecisionSnapshot', async () => {
    mockFetchOnce({
      status: 200,
      body: {
        snapshot: {
          decision: 'Should I move cities?',
          goal: null,
          constraints: [],
          commitments: [],
          beliefs: [],
          uncertainties: [],
          alternatives: [],
          evidence: [],
          important_variables: [],
          stakeholders: [],
          decision_criteria: [],
          missing_information: ['constraint', 'belief'],
          interview_summary: 'Interview covered 0 topic(s) over 0 turn(s).',
        },
        readiness: 'early',
        missing_information: ['constraint', 'belief'],
      },
    });

    const result = await skipInterview('int-1');

    expect(result.missing_information).toEqual(['constraint', 'belief']);
  });
});
