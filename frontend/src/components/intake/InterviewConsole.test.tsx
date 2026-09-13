import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { InterviewConsole } from './InterviewConsole';
import type { InterviewState } from '@/hooks/useInterview';

function baseInterview(overrides: Partial<InterviewState> = {}): InterviewState {
  return {
    stage: 'awaiting-answer',
    interviewId: 'int-1',
    state: {
      interview_id: 'int-1',
      decision_id: 'dec-1',
      user_id: 'user-1',
      status: 'awaiting_answer',
      turn_number: 1,
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
    },
    messages: [{ id: 'm1', role: 'regret', text: 'What would make this decision successful?' }],
    currentQuestion: 'What would make this decision successful?',
    readiness: 'early',
    suggestedChips: [],
    snapshot: null,
    agentAvailable: true,
    error: null,
    ...overrides,
  };
}

describe('InterviewConsole', () => {
  it('renders the conversation so far, oldest first', () => {
    const interview = baseInterview({
      messages: [
        { id: 'm1', role: 'regret', text: 'What would make this decision successful?' },
        { id: 'm2', role: 'user', text: 'A calmer life.' },
      ],
    });

    render(
      <InterviewConsole interview={interview} onSend={vi.fn()} onSkip={vi.fn()} onContinueToStressTest={vi.fn()} />,
    );

    const bubbles = screen.getAllByText(/What would make this decision successful\?|A calmer life\./);
    expect(bubbles).toHaveLength(2);
  });

  it('sends the typed answer and clears the input', () => {
    const onSend = vi.fn();
    render(
      <InterviewConsole interview={baseInterview()} onSend={onSend} onSkip={vi.fn()} onContinueToStressTest={vi.fn()} />,
    );

    const textarea = screen.getByLabelText('Your answer');
    fireEvent.change(textarea, { target: { value: 'A calmer life.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));

    expect(onSend).toHaveBeenCalledWith('A calmer life.');
    expect(textarea).toHaveValue('');
  });

  it('sends a suggested chip as the answer without requiring typed text', () => {
    const onSend = vi.fn();
    const interview = baseInterview({ suggestedChips: ['Career growth', 'Compensation'] });

    render(
      <InterviewConsole interview={interview} onSend={onSend} onSkip={vi.fn()} onContinueToStressTest={vi.fn()} />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Career growth' }));
    expect(onSend).toHaveBeenCalledWith('Career growth');
  });

  it('calls onSkip when "Skip to stress test" is clicked', () => {
    const onSkip = vi.fn();
    render(
      <InterviewConsole interview={baseInterview()} onSend={vi.fn()} onSkip={onSkip} onContinueToStressTest={vi.fn()} />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Skip to stress test' }));
    expect(onSkip).toHaveBeenCalledTimes(1);
  });

  it('shows the readiness message and the stress-test CTA once the interview is ready', () => {
    const onContinue = vi.fn();
    const interview = baseInterview({
      stage: 'ready',
      readiness: 'enough',
      currentQuestion: null,
    });

    render(
      <InterviewConsole interview={interview} onSend={vi.fn()} onSkip={vi.fn()} onContinueToStressTest={onContinue} />,
    );

    expect(screen.getByText('I have enough context to stress-test this decision.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Stress Test This Decision/i }));
    expect(onContinue).toHaveBeenCalledTimes(1);
  });

  it('never shows the answer input once the interview is ready', () => {
    const interview = baseInterview({ stage: 'ready', currentQuestion: null });

    render(
      <InterviewConsole interview={interview} onSend={vi.fn()} onSkip={vi.fn()} onContinueToStressTest={vi.fn()} />,
    );

    expect(screen.queryByLabelText('Your answer')).not.toBeInTheDocument();
  });

  it("shows REGRET's fallback notice when the agent was unavailable this turn, without blocking the conversation", () => {
    const interview = baseInterview({ agentAvailable: false });

    render(
      <InterviewConsole interview={interview} onSend={vi.fn()} onSkip={vi.fn()} onContinueToStressTest={vi.fn()} />,
    );

    expect(
      screen.getByText(
        "REGRET couldn't continue the interview, but you can continue with the information you've already provided.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Your answer')).toBeInTheDocument();
  });

  it('reflects known/assumed/uncertain fields in the live decision-model side panel', () => {
    const interview = baseInterview();
    interview.state = {
      ...interview.state!,
      desired_outcome: 'A calmer life',
      constraints: ['Must stay within budget'],
      uncertainties: ['Whether the new city has good schools'],
      alternatives: ['Stay put another year'],
    };

    render(
      <InterviewConsole interview={interview} onSend={vi.fn()} onSkip={vi.fn()} onContinueToStressTest={vi.fn()} />,
    );

    expect(screen.getByText('A calmer life')).toBeInTheDocument();
    expect(screen.getByText('Must stay within budget')).toBeInTheDocument();
    expect(screen.getByText('Whether the new city has good schools')).toBeInTheDocument();
    expect(screen.getByText('Stay put another year')).toBeInTheDocument();
  });

  it('shows the turn progress counter against the max turn ceiling', () => {
    const interview = baseInterview();
    interview.state = { ...interview.state!, turn_number: 3, max_turns: 7 };

    render(
      <InterviewConsole interview={interview} onSend={vi.fn()} onSkip={vi.fn()} onContinueToStressTest={vi.fn()} />,
    );

    expect(screen.getByText('03 / 07')).toBeInTheDocument();
  });

  it('supports submitting an answer with the Enter key, without a Shift modifier', () => {
    const onSend = vi.fn();
    render(
      <InterviewConsole interview={baseInterview()} onSend={onSend} onSkip={vi.fn()} onContinueToStressTest={vi.fn()} />,
    );

    const textarea = screen.getByLabelText('Your answer');
    fireEvent.change(textarea, { target: { value: 'A calmer life.' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

    expect(onSend).toHaveBeenCalledWith('A calmer life.');
  });
});
