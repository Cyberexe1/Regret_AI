import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { NewDecisionPage } from './NewDecisionPage';
import { mockFetchOnce } from '@/test/mockFetch';

afterEach(() => {
  vi.unstubAllGlobals();
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

describe('NewDecisionPage - smart minimal intake', () => {
  it('opens with a neutral, category-agnostic placeholder - never the cloud-kitchen scenario', () => {
    renderNewDecisionPage();

    const decisionField = screen.getByPlaceholderText(
      'Should I accept the software engineering offer from Company A?',
    );
    expect(decisionField).toHaveValue('');
    expect(screen.queryByText(/cloud kitchen/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/₹5,00,000/)).not.toBeInTheDocument();
  });

  it('renders exactly the five minimal context questions by default, nothing more', () => {
    renderNewDecisionPage();

    expect(screen.getByLabelText('What would make this decision successful?')).toBeInTheDocument();
    expect(screen.getByLabelText('What could realistically limit this decision?')).toBeInTheDocument();
    expect(screen.getByLabelText('What are you currently assuming?')).toBeInTheDocument();
    expect(screen.getByLabelText('What are you least sure about?')).toBeInTheDocument();
    expect(screen.getByLabelText('What else could you do?')).toBeInTheDocument();

    // None of the progressively-disclosed fields render until a chip is
    // selected - no financial/timing/location/risk/commitment fields.
    expect(screen.queryByLabelText(/Financial commitment/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Location')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('What are you putting at stake?')).not.toBeInTheDocument();
    expect(
      screen.queryByText('How much downside are you willing to accept?'),
    ).not.toBeInTheDocument();
  });

  it('shows every universal decision category as a selectable option, including "Other"', () => {
    renderNewDecisionPage();

    for (const label of ['Career', 'Education', 'Personal', 'Financial', 'Business', 'Technology', 'Other']) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument();
    }
  });

  it('never forces a decision type - the decision can be submitted with none selected', () => {
    renderNewDecisionPage();

    expect(screen.getByText(/Not sure\? REGRET will infer the decision type\./)).toBeInTheDocument();
    for (const label of ['Career', 'Business', 'Other']) {
      expect(screen.getByRole('button', { name: label })).toHaveAttribute('aria-pressed', 'false');
    }
  });

  it('allows selecting more than one category at once (e.g. Career + Personal)', () => {
    renderNewDecisionPage();

    fireEvent.click(screen.getByRole('button', { name: 'Career' }));
    fireEvent.click(screen.getByRole('button', { name: 'Personal' }));

    expect(screen.getByRole('button', { name: 'Career' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Personal' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('shows no "anything else that matters" chips until a category is selected', () => {
    renderNewDecisionPage();

    expect(screen.queryByText('Anything else that matters?')).not.toBeInTheDocument();
  });

  it('suggests career-relevant chips once Career is selected', () => {
    renderNewDecisionPage();

    fireEvent.click(screen.getByRole('button', { name: 'Career' }));

    expect(screen.getByText('Anything else that matters?')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Compensation' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Location' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Growth' })).toBeInTheDocument();
    // Nothing is revealed until a chip is actually clicked.
    expect(screen.queryByLabelText('Financial impact')).not.toBeInTheDocument();
  });

  it('clicking a chip reveals exactly its field, and nothing else', () => {
    renderNewDecisionPage();

    fireEvent.click(screen.getByRole('button', { name: 'Career' }));
    fireEvent.click(screen.getByRole('button', { name: 'Compensation' }));

    expect(screen.getByLabelText('Financial impact')).toBeInTheDocument();
    expect(screen.queryByLabelText('Location')).not.toBeInTheDocument();
  });

  it('deselecting a chip hides its field again', () => {
    renderNewDecisionPage();

    fireEvent.click(screen.getByRole('button', { name: 'Career' }));
    const compensationChip = screen.getByRole('button', { name: 'Compensation' });
    fireEvent.click(compensationChip);
    expect(screen.getByLabelText('Financial impact')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Compensation' }));
    expect(screen.queryByLabelText('Financial impact')).not.toBeInTheDocument();
  });

  it('suggests education-relevant chips once Education is selected', () => {
    renderNewDecisionPage();

    fireEvent.click(screen.getByRole('button', { name: 'Education' }));

    expect(screen.getByRole('button', { name: 'Tuition' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Duration' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Career outcome' })).toBeInTheDocument();
  });

  it('suggests business-relevant chips once Business is selected', () => {
    renderNewDecisionPage();

    fireEvent.click(screen.getByRole('button', { name: 'Business' }));

    expect(screen.getByRole('button', { name: 'Capital' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Customers' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Risk' })).toBeInTheDocument();
  });

  it('suggests technology-relevant chips once Technology is selected', () => {
    renderNewDecisionPage();

    fireEvent.click(screen.getByRole('button', { name: 'Technology' }));

    expect(screen.getByRole('button', { name: 'Migration effort' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Team capability' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Scale' })).toBeInTheDocument();
  });

  it('merges chips from multiple selected categories without duplicates', () => {
    renderNewDecisionPage();

    fireEvent.click(screen.getByRole('button', { name: 'Career' }));
    fireEvent.click(screen.getByRole('button', { name: 'Personal' }));

    // "Location" is suggested by both categories - only one chip should
    // ever render for the underlying field it reveals.
    expect(screen.getAllByRole('button', { name: 'Location' })).toHaveLength(1);
  });

  it('shows no suggested chips at all for "Other"/unrecognized decisions - the universal fallback', () => {
    renderNewDecisionPage();

    fireEvent.click(screen.getByRole('button', { name: 'Other' }));

    expect(screen.queryByText('Anything else that matters?')).not.toBeInTheDocument();
  });

  it('populates the entire form, including categories and chips, when an example decision card is clicked', async () => {
    renderNewDecisionPage();

    fireEvent.click(screen.getByText('Accept a new job?'));

    await waitFor(() =>
      expect(
        screen.getByPlaceholderText('Should I accept the software engineering offer from Company A?'),
      ).toHaveValue('Should I accept a software engineering offer that pays more but requires relocating?'),
    );
    // The example spans two categories (Career + Personal, spec section 2).
    expect(screen.getByRole('button', { name: 'Career' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Personal' })).toHaveAttribute('aria-pressed', 'true');
    // Fields the example actually filled (timing/location/financial) are
    // pre-revealed rather than hidden behind an unselected chip.
    expect(screen.getByLabelText('Financial impact')).toHaveValue(
      'Relocation cost, and giving up unvested equity at my current job.',
    );
  });

  it('populates the business example without that being the default/opening state', async () => {
    renderNewDecisionPage();

    expect(screen.queryByText(/cloud kitchen/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Launch a new venture?'));

    await waitFor(() =>
      expect(
        screen.getByPlaceholderText('Should I accept the software engineering offer from Company A?'),
      ).toHaveValue('Should I invest ₹5 lakh to launch a cloud kitchen?'),
    );
  });

  it('handles the technology migration example the same way as the business example', async () => {
    renderNewDecisionPage();

    fireEvent.click(screen.getByText('Migrate our system?'));

    await waitFor(() =>
      expect(
        screen.getByPlaceholderText('Should I accept the software engineering offer from Company A?'),
      ).toHaveValue('Should we migrate our production PostgreSQL database to DynamoDB?'),
    );
    expect(screen.getByRole('button', { name: 'Technology' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('leaves every optional context field empty without blocking the ability to type into them', () => {
    renderNewDecisionPage();

    const uncertainty = screen.getByLabelText('What are you least sure about?');
    expect(uncertainty).toHaveValue('');
    expect(uncertainty).not.toBeRequired();
  });

  it('keeps the "Start Stress Test" button disabled until a decision is entered, and enables it with zero optional context filled', () => {
    renderNewDecisionPage();

    const button = screen.getByRole('button', { name: /Start Stress Test/i });
    expect(button).toBeDisabled();

    fireEvent.change(screen.getByPlaceholderText('Should I accept the software engineering offer from Company A?'), {
      target: { value: 'Should I move to another city?' },
    });

    expect(button).not.toBeDisabled();
  });

  it('shows the "start with what you know" copy once a decision is entered, and "start with the decision" copy before that', () => {
    renderNewDecisionPage();

    expect(screen.getByText('Start with the decision. The engine will discover what could make it fail.')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('Should I accept the software engineering offer from Company A?'), {
      target: { value: 'Should I move to another city?' },
    });

    expect(
      screen.getByText("Start with what you know. REGRET will uncover what you haven't considered."),
    ).toBeInTheDocument();
  });

  it('associates every minimal context field label with its control for screen readers', () => {
    renderNewDecisionPage();

    expect(screen.getByLabelText('What would make this decision successful?')).toBeInTheDocument();
    expect(screen.getByLabelText('What could realistically limit this decision?')).toBeInTheDocument();
    expect(screen.getByLabelText('What are you currently assuming?')).toBeInTheDocument();
    expect(screen.getByLabelText('What are you least sure about?')).toBeInTheDocument();
    expect(screen.getByLabelText('What else could you do?')).toBeInTheDocument();
  });

  it('keeps the step indicator labels universal (Decision / Context / Evidence / Stress Test)', () => {
    renderNewDecisionPage();

    for (const label of ['Decision', 'Context', 'Evidence', 'Stress Test']) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
  });
});

describe('NewDecisionPage - universality across all eight example decision types', () => {
  const cases: Array<{ decisionText: string; category: string }> = [
    {
      decisionText: 'Should I accept a software engineering offer that pays more but requires relocating?',
      category: 'Career',
    },
    { decisionText: 'Should I pursue an MS in AI?', category: 'Education' },
    { decisionText: 'Should I buy a car this year?', category: 'Personal' },
    { decisionText: 'Should I invest ₹5 lakh into a cloud kitchen?', category: 'Business' },
    {
      decisionText: 'Should we migrate our production database to DynamoDB?',
      category: 'Technology',
    },
    { decisionText: 'Should I move to another city?', category: 'Personal' },
    { decisionText: 'Should I hire this candidate?', category: 'Hiring' },
    { decisionText: 'Should I launch this product?', category: 'Product' },
  ];

  for (const { decisionText, category } of cases) {
    it(`accepts "${decisionText}" and lets the user tag it as ${category}`, () => {
      renderNewDecisionPage();

      fireEvent.change(
        screen.getByPlaceholderText('Should I accept the software engineering offer from Company A?'),
        { target: { value: decisionText } },
      );
      fireEvent.click(screen.getByRole('button', { name: category }));

      expect(
        screen.getByPlaceholderText('Should I accept the software engineering offer from Company A?'),
      ).toHaveValue(decisionText);
      expect(screen.getByRole('button', { name: category })).toHaveAttribute('aria-pressed', 'true');
      expect(screen.getByRole('button', { name: /Start Stress Test/i })).not.toBeDisabled();
    });
  }
});
