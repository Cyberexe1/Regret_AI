import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { NewDecisionPage } from './NewDecisionPage';
import { mockFetchOnce, mockFetchSequence, type MockResponseSpec } from '@/test/mockFetch';

const navigateSpy = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigateSpy };
});

afterEach(() => {
  vi.unstubAllGlobals();
  navigateSpy.mockClear();
});

/**
 * `useCrossDecisionPatterns` fires `GET /learning/patterns` on every
 * mount of this page - stub it to an empty list so every test below is
 * isolated from that concern (the historical-context preview debounces
 * 600ms and never fires for text under the page's minimum length, so it
 * needs no stub for these short example decisions).
 */
function renderNewDecisionPage() {
  mockFetchOnce({ status: 200, body: { patterns: [] } });
  return render(
    <MemoryRouter>
      <NewDecisionPage />
    </MemoryRouter>,
  );
}

const CREATED_DECISION = {
  id: 'dec-1',
  title: 'Should I move to another city?',
  description: 'Should I move to another city?',
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
};

const INTERVIEW_STATE = {
  interview_id: 'int-1',
  decision_id: 'dec-1',
  user_id: 'user-1',
  status: 'awaiting_answer',
  turn_number: 0,
  max_turns: 7,
  decision_text: 'Should I move to another city?',
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

function enterDecisionAndStartInterview(extraMocks: MockResponseSpec[] = []) {
  mockFetchSequence([
    { status: 201, body: CREATED_DECISION },
    {
      status: 200,
      body: { interview_id: 'int-1', first_question: INTERVIEW_STATE.current_question, state: INTERVIEW_STATE },
    },
    ...extraMocks,
  ]);

  fireEvent.change(
    screen.getByPlaceholderText('Should I accept the software engineering offer from Company A?'),
    { target: { value: 'Should I move to another city?' } },
  );
  fireEvent.click(screen.getByRole('button', { name: 'Start interview' }));
}

describe('NewDecisionPage - decision + category entry', () => {
  it('opens with a neutral, category-agnostic placeholder - never the cloud-kitchen scenario', () => {
    renderNewDecisionPage();

    const decisionField = screen.getByPlaceholderText(
      'Should I accept the software engineering offer from Company A?',
    );
    expect(decisionField).toHaveValue('');
    expect(screen.queryByText(/cloud kitchen/i)).not.toBeInTheDocument();
  });

  it('shows every universal decision category as a selectable option, including "Other"', () => {
    renderNewDecisionPage();

    for (const label of ['Career', 'Education', 'Personal', 'Financial', 'Business', 'Technology', 'Other']) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument();
    }
  });

  it('allows selecting more than one category at once (e.g. Career + Personal)', () => {
    renderNewDecisionPage();

    fireEvent.click(screen.getByRole('button', { name: 'Career' }));
    fireEvent.click(screen.getByRole('button', { name: 'Personal' }));

    expect(screen.getByRole('button', { name: 'Career' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Personal' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('keeps the "Start interview" button disabled until a decision is entered', () => {
    renderNewDecisionPage();

    expect(screen.getByRole('button', { name: 'Start interview' })).toBeDisabled();

    fireEvent.change(screen.getByPlaceholderText('Should I accept the software engineering offer from Company A?'), {
      target: { value: 'Should I move to another city?' },
    });

    expect(screen.getByRole('button', { name: 'Start interview' })).not.toBeDisabled();
  });

  it('populates the decision and categories when an example decision card is clicked', async () => {
    renderNewDecisionPage();

    fireEvent.click(screen.getByText('Accept a new job?'));

    await waitFor(() =>
      expect(
        screen.getByPlaceholderText('Should I accept the software engineering offer from Company A?'),
      ).toHaveValue('Should I accept a software engineering offer that pays more but requires relocating?'),
    );
    expect(screen.getByRole('button', { name: 'Career' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Personal' })).toHaveAttribute('aria-pressed', 'true');
  });
});

describe('NewDecisionPage - starting the interview', () => {
  it('creates the decision and starts the interview when "Start interview" is clicked', async () => {
    renderNewDecisionPage();
    enterDecisionAndStartInterview();

    await waitFor(() => expect(screen.getByTestId('interview-console')).toBeInTheDocument());
    expect(screen.getByText('What would make this decision successful?')).toBeInTheDocument();
    // The decision statement can no longer be edited once the interview has begun.
    expect(
      screen.getByPlaceholderText('Should I accept the software engineering offer from Company A?'),
    ).toBeDisabled();
  });

  it('shows a loading state while the decision is being created and the interview is starting', async () => {
    renderNewDecisionPage();

    mockFetchSequence([
      { status: 201, body: CREATED_DECISION },
      {
        status: 200,
        body: { interview_id: 'int-1', first_question: INTERVIEW_STATE.current_question, state: INTERVIEW_STATE },
      },
    ]);

    fireEvent.change(
      screen.getByPlaceholderText('Should I accept the software engineering offer from Company A?'),
      { target: { value: 'Should I move to another city?' } },
    );
    fireEvent.click(screen.getByRole('button', { name: 'Start interview' }));

    expect(screen.getByRole('button', { name: 'Start interview' })).toHaveAttribute('aria-busy', 'true');
    await waitFor(() => expect(screen.getByTestId('interview-console')).toBeInTheDocument());
  });

  it('shows an error and lets the user continue without the interview if starting it fails', async () => {
    renderNewDecisionPage();

    mockFetchSequence([
      {
        status: 500,
        body: { error: { code: 'INTERNAL_ERROR', message: 'REGRET is unavailable.', request_id: 'r1' }, detail: 'REGRET is unavailable.' },
      },
    ]);

    fireEvent.change(
      screen.getByPlaceholderText('Should I accept the software engineering offer from Company A?'),
      { target: { value: 'Should I move to another city?' } },
    );
    fireEvent.click(screen.getByRole('button', { name: 'Start interview' }));

    await waitFor(() => expect(screen.getByText('REGRET is unavailable.')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });
});

describe('NewDecisionPage - the conversation', () => {
  it('renders the growing conversation as the user answers, and updates the live decision model', async () => {
    renderNewDecisionPage();
    enterDecisionAndStartInterview([
      {
        status: 200,
        body: {
          response: 'What could realistically limit this decision?',
          extracted_fields: { ...EMPTY_EXTRACTED, desired_outcome: 'A calmer life' },
          current_state: { ...INTERVIEW_STATE, turn_number: 1, desired_outcome: 'A calmer life' },
          next_question: 'What could realistically limit this decision?',
          readiness: 'early',
          turn_number: 1,
          suggested_chips: [],
          agent_available: true,
        },
      },
    ]);

    await waitFor(() => expect(screen.getByTestId('interview-console')).toBeInTheDocument());

    const console_ = screen.getByTestId('interview-console');
    fireEvent.change(within(console_).getByLabelText('Your answer'), {
      target: { value: 'A calmer life.' },
    });
    fireEvent.click(within(console_).getByRole('button', { name: 'Send' }));

    await waitFor(() =>
      expect(within(console_).getByText('What could realistically limit this decision?')).toBeInTheDocument(),
    );
    expect(within(console_).getByText('A calmer life.')).toBeInTheDocument();
    // Live "decision model" side panel now reflects the newly-extracted goal.
    expect(within(console_).getByText('A calmer life')).toBeInTheDocument();
  });

  it('sends a suggested quick-response chip as the answer', async () => {
    renderNewDecisionPage();
    enterDecisionAndStartInterview([
      {
        status: 200,
        body: {
          response: 'Got it.',
          extracted_fields: EMPTY_EXTRACTED,
          current_state: { ...INTERVIEW_STATE, turn_number: 1 },
          next_question: 'Anything else that matters?',
          readiness: 'early',
          turn_number: 1,
          suggested_chips: ['Compensation'],
          agent_available: true,
        },
      },
    ]);

    await waitFor(() => expect(screen.getByTestId('interview-console')).toBeInTheDocument());
    const console_ = screen.getByTestId('interview-console');
    fireEvent.change(within(console_).getByLabelText('Your answer'), { target: { value: 'placeholder' } });
    fireEvent.click(within(console_).getByRole('button', { name: 'Send' }));

    await waitFor(() => expect(within(console_).getByRole('button', { name: 'Compensation' })).toBeInTheDocument());
    fireEvent.click(within(console_).getByRole('button', { name: 'Compensation' }));

    // Sent as the user's own message, distinct from the still-visible chip button.
    expect(within(console_).getAllByText('Compensation')).toHaveLength(2);
  });

  it('supports answering with the Enter key for keyboard-only use', async () => {
    renderNewDecisionPage();
    enterDecisionAndStartInterview();

    await waitFor(() => expect(screen.getByTestId('interview-console')).toBeInTheDocument());
    const console_ = screen.getByTestId('interview-console');
    const textarea = within(console_).getByLabelText('Your answer');
    fireEvent.change(textarea, { target: { value: 'A calmer life.' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

    await waitFor(() => expect(within(console_).getByText('A calmer life.')).toBeInTheDocument());
  });
});

describe('NewDecisionPage - skipping and finishing the interview', () => {
  it('lets the user skip straight to the stress test and still shows a snapshot', async () => {
    renderNewDecisionPage();
    enterDecisionAndStartInterview([
      {
        status: 200,
        body: {
          snapshot: {
            decision: 'Should I move to another city?',
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
            missing_information: ['goal', 'constraint'],
            interview_summary: 'Interview covered 0 topic(s) over 0 turn(s).',
          },
          readiness: 'early',
          missing_information: ['goal', 'constraint'],
        },
      },
    ]);

    await waitFor(() => expect(screen.getByTestId('interview-console')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: 'Skip to stress test' }));

    await waitFor(() => expect(screen.getByText('What REGRET understood')).toBeInTheDocument());
    expect(screen.getByText("We're still understanding the decision.")).toBeInTheDocument();
  });

  it('shows the final DecisionSnapshot once the interview reaches readiness and is completed', async () => {
    renderNewDecisionPage();
    enterDecisionAndStartInterview([
      {
        status: 200,
        body: {
          response: "I've identified the main uncertainties worth testing.",
          extracted_fields: EMPTY_EXTRACTED,
          current_state: { ...INTERVIEW_STATE, turn_number: 5, status: 'ready', current_question: null },
          next_question: null,
          readiness: 'ready',
          turn_number: 5,
          suggested_chips: [],
          agent_available: true,
        },
      },
      {
        status: 200,
        body: {
          snapshot: {
            decision: 'Should I move to another city?',
            goal: 'A calmer life',
            constraints: [],
            commitments: [],
            beliefs: [],
            uncertainties: ['Whether the new city has good schools'],
            alternatives: [],
            evidence: [],
            important_variables: [],
            stakeholders: [],
            decision_criteria: [],
            missing_information: [],
            interview_summary: 'Interview covered 5 topic(s) over 5 turn(s).',
          },
          readiness: 'ready',
          missing_information: [],
        },
      },
    ]);

    await waitFor(() => expect(screen.getByTestId('interview-console')).toBeInTheDocument());
    const console_ = screen.getByTestId('interview-console');
    fireEvent.change(within(console_).getByLabelText('Your answer'), { target: { value: 'That covers it.' } });
    fireEvent.click(within(console_).getByRole('button', { name: 'Send' }));

    await waitFor(() => expect(within(console_).getByRole('button', { name: /Stress Test This Decision/i })).toBeInTheDocument());
    fireEvent.click(within(console_).getByRole('button', { name: /Stress Test This Decision/i }));

    await waitFor(() => expect(screen.getByText('What REGRET understood')).toBeInTheDocument());
    expect(screen.getByText('A calmer life')).toBeInTheDocument();
    expect(screen.getByText('Whether the new city has good schools')).toBeInTheDocument();
    // The "Start Stress Test" button at the bottom of the page is now enabled.
    expect(screen.getByRole('button', { name: /Start Stress Test/i })).not.toBeDisabled();
  });

  it('lets the user edit the snapshot notes before starting the stress test', async () => {
    renderNewDecisionPage();
    enterDecisionAndStartInterview([
      {
        status: 200,
        body: {
          snapshot: {
            decision: 'Should I move to another city?',
            goal: null,
            constraints: [],
            commitments: [],
            beliefs: ['I believe a smaller city fits better'],
            uncertainties: [],
            alternatives: [],
            evidence: [],
            important_variables: [],
            stakeholders: [],
            decision_criteria: [],
            missing_information: [],
            interview_summary: 'Interview covered 0 topic(s) over 0 turn(s).',
          },
          readiness: 'early',
          missing_information: [],
        },
      },
    ]);

    await waitFor(() => expect(screen.getByTestId('interview-console')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: 'Skip to stress test' }));
    await waitFor(() => expect(screen.getByText('What REGRET understood')).toBeInTheDocument());

    mockFetchOnce({ status: 200, body: { ...CREATED_DECISION, beliefs: 'One more consideration.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
    fireEvent.change(screen.getByLabelText('Notes for REGRET'), { target: { value: 'One more consideration.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => expect(screen.queryByLabelText('Notes for REGRET')).not.toBeInTheDocument());
    expect(screen.getByText('One more consideration.')).toBeInTheDocument();
  });

  it('navigates to the analysis workspace for the SAME decision after completing intake', async () => {
    renderNewDecisionPage();
    enterDecisionAndStartInterview([
      {
        status: 200,
        body: {
          snapshot: {
            decision: 'Should I move to another city?',
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
            missing_information: [],
            interview_summary: 'Interview covered 0 topic(s) over 0 turn(s).',
          },
          readiness: 'early',
          missing_information: [],
        },
      },
    ]);

    await waitFor(() => expect(screen.getByTestId('interview-console')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: 'Skip to stress test' }));
    await waitFor(() => expect(screen.getByText('What REGRET understood')).toBeInTheDocument());

    // `useAnalysisRun` and `useAnalysisPolling` both call
    // `GET /analysis/latest` concurrently on mount, so a strict
    // call-order sequence would be flaky - route by URL instead. The
    // "latest" endpoint reports `completed` from its SECOND call onward,
    // simulating the real pipeline finishing between polls.
    let latestCallCount = 0;
    const fetchMock = vi.fn(async (url: string) => {
      if (url.includes('/analysis/latest')) {
        latestCallCount += 1;
        if (latestCallCount === 1) {
          return new Response(
            JSON.stringify({
              error: { code: 'NOT_FOUND', message: 'No run yet.', request_id: 'r1' },
              detail: 'No run yet.',
            }),
            { status: 404, headers: { 'Content-Type': 'application/json' } },
          );
        }
        return new Response(
          JSON.stringify({
            analysis_run_id: 'run-1',
            decision_id: 'dec-1',
            status: 'completed',
            current_stage: null,
            stage_statuses: { decision_analyzer: 'completed' },
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:01Z',
            error_message: null,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.includes('/analyze')) {
        return new Response(
          JSON.stringify({ analysis_run_id: 'run-1', decision_id: 'dec-1', status: 'running' }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    const submitButton = screen.getByRole('button', { name: /Start Stress Test/i });
    expect(submitButton).not.toBeDisabled();
    fireEvent.click(submitButton);

    // No evidence attached, so `submit()` resolves immediately with the
    // SAME decision id the interview already created - no second
    // `POST /decisions` call is ever made. A progress popup opens and
    // runs the real backend pipeline; navigation only happens once that
    // pipeline actually reports "completed".
    await waitFor(() => expect(screen.getByText('Stress-testing your decision')).toBeInTheDocument());
    await waitFor(() => expect(navigateSpy).toHaveBeenCalledWith('/decision/dec-1/analysis'), {
      timeout: 10000,
    });
  });
});

describe('NewDecisionPage - accessibility', () => {
  it('associates the answer textarea with its own accessible label inside the console', async () => {
    renderNewDecisionPage();
    enterDecisionAndStartInterview();

    await waitFor(() => expect(screen.getByTestId('interview-console')).toBeInTheDocument());
    expect(within(screen.getByTestId('interview-console')).getByLabelText('Your answer')).toBeInTheDocument();
  });

  it('keeps the step indicator labels universal (Decision / Context / Evidence / Stress Test)', () => {
    renderNewDecisionPage();

    for (const label of ['Decision', 'Context', 'Evidence', 'Stress Test']) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
  });
});
