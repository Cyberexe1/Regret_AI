import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { DashboardPage } from './DashboardPage';
import { mockFetchOnce, mockFetchSequence } from '@/test/mockFetch';

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderDashboard() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  );
}

describe('DashboardPage', () => {
  it('shows an empty state when the workspace has no decisions, never fake data', async () => {
    mockFetchOnce({ status: 200, body: { items: [], next_cursor: null } });

    renderDashboard();

    await waitFor(() => expect(screen.getByText('No decisions yet')).toBeInTheDocument());
  });

  it('shows a real error state on backend failure, never a silent fallback to fake data', async () => {
    mockFetchOnce({
      status: 500,
      body: {
        error: { code: 'STORAGE_ERROR', message: 'A storage error occurred. Please try again.', request_id: 'req-1' },
        detail: 'A storage error occurred. Please try again.',
      },
    });

    renderDashboard();

    await waitFor(() => expect(screen.getByText('Unable to load your dashboard')).toBeInTheDocument());
    expect(screen.getByText('A storage error occurred. Please try again.')).toBeInTheDocument();
  });

  it('renders real decision data from the backend, never mock/static rows', async () => {
    mockFetchSequence([
      {
        status: 200,
        body: {
          items: [
            {
              id: 'dec-1',
              title: 'Open a bakery',
              description: 'Should I open a second location?',
              desired_outcome: null,
              budget: null,
              currency: null,
              timeline: null,
              location: null,
              risk_tolerance: null,
              beliefs: null,
              status: 'needs_validation',
              created_at: '2026-01-01T00:00:00Z',
              updated_at: '2026-01-02T00:00:00Z',
            },
          ],
          next_cursor: null,
        },
      },
      { status: 200, body: [] },
    ]);

    renderDashboard();

    await waitFor(() => expect(screen.getAllByText('Open a bakery').length).toBeGreaterThan(0));
  });
});
