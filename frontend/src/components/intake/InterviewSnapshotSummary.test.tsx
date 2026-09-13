import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { InterviewSnapshotSummary } from './InterviewSnapshotSummary';
import type { ApiDecisionSnapshot } from '@/api/types';

function snapshot(overrides: Partial<ApiDecisionSnapshot> = {}): ApiDecisionSnapshot {
  return {
    decision: 'Should I move cities?',
    goal: 'A calmer life',
    constraints: ['Must decide within two weeks'],
    commitments: [],
    beliefs: [],
    uncertainties: ['Whether the new city has good schools'],
    alternatives: ['Stay put another year'],
    evidence: [],
    important_variables: [],
    stakeholders: [],
    decision_criteria: [],
    missing_information: [],
    interview_summary: 'Interview covered 4 topic(s) over 5 turn(s).',
    ...overrides,
  };
}

describe('InterviewSnapshotSummary', () => {
  it('shows the exact readiness copy for the given readiness level', () => {
    render(
      <InterviewSnapshotSummary snapshot={snapshot()} readiness="enough" onSaveNotes={vi.fn()} />,
    );

    expect(screen.getByText('I have enough context to stress-test this decision.')).toBeInTheDocument();
  });

  it("renders the interview's discovered goal, constraints, uncertainties, and alternatives", () => {
    render(
      <InterviewSnapshotSummary snapshot={snapshot()} readiness="ready" onSaveNotes={vi.fn()} />,
    );

    expect(screen.getByText('A calmer life')).toBeInTheDocument();
    expect(screen.getByText('Must decide within two weeks')).toBeInTheDocument();
    expect(screen.getByText('Whether the new city has good schools')).toBeInTheDocument();
    expect(screen.getByText('Stay put another year')).toBeInTheDocument();
  });

  it('shows "Not discussed" for a field the interview never covered', () => {
    render(
      <InterviewSnapshotSummary
        snapshot={snapshot({ goal: null, alternatives: [] })}
        readiness="early"
        onSaveNotes={vi.fn()}
      />,
    );

    expect(screen.getAllByText('Not discussed.').length).toBeGreaterThanOrEqual(2);
  });

  it('lets the user edit the notes and saves them via onSaveNotes', async () => {
    const onSaveNotes = vi.fn().mockResolvedValue(undefined);
    render(
      <InterviewSnapshotSummary snapshot={snapshot()} readiness="enough" onSaveNotes={onSaveNotes} />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
    const textarea = screen.getByLabelText('Notes for REGRET');
    fireEvent.change(textarea, { target: { value: 'One more thing REGRET should know.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => expect(onSaveNotes).toHaveBeenCalledWith('One more thing REGRET should know.'));
    await waitFor(() => expect(screen.queryByLabelText('Notes for REGRET')).not.toBeInTheDocument());
  });

  it('shows an error and keeps the edit open when saving notes fails', async () => {
    const onSaveNotes = vi.fn().mockRejectedValue(new Error('network error'));
    render(
      <InterviewSnapshotSummary snapshot={snapshot()} readiness="enough" onSaveNotes={onSaveNotes} />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => expect(screen.getByText('Could not save your edit. Please try again.')).toBeInTheDocument());
    expect(screen.getByLabelText('Notes for REGRET')).toBeInTheDocument();
  });

  it('cancelling an edit discards the change and keeps the original notes', () => {
    render(
      <InterviewSnapshotSummary snapshot={snapshot()} readiness="enough" onSaveNotes={vi.fn()} />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
    fireEvent.change(screen.getByLabelText('Notes for REGRET'), { target: { value: 'Discard me.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(screen.queryByText('Discard me.')).not.toBeInTheDocument();
    expect(screen.getAllByText(/Must decide within two weeks/).length).toBeGreaterThan(0);
  });
});
