import { describe, expect, it } from 'vitest';
import { buildDecisionCreatePayload } from './decisionPayload';
import { emptyDecisionDraft } from './decisionDraft';
import type { DecisionDraftWithFiles } from '@/hooks/useDecisionIntake';

function draft(overrides: Partial<DecisionDraftWithFiles> = {}): DecisionDraftWithFiles {
  return { ...emptyDecisionDraft, evidence: [], ...overrides };
}

describe('buildDecisionCreatePayload', () => {
  it('sends only fields the existing backend DecisionCreate schema accepts', () => {
    const payload = buildDecisionCreatePayload(draft({ decision: 'Should I accept the offer?' }));

    const allowedKeys = new Set([
      'title',
      'description',
      'desired_outcome',
      'budget',
      'currency',
      'timeline',
      'location',
      'risk_tolerance',
      'beliefs',
    ]);
    for (const key of Object.keys(payload)) {
      expect(allowedKeys.has(key)).toBe(true);
    }
  });

  it('always sends a non-empty title derived from the decision text', () => {
    const payload = buildDecisionCreatePayload(draft({ decision: 'Should I move cities?' }));
    expect(payload.title).toBe('Should I move cities?');
  });

  it('falls back to a placeholder title only if decision text is somehow empty', () => {
    const payload = buildDecisionCreatePayload(draft({ decision: '' }));
    expect(payload.title).toBe('Untitled decision');
  });

  it('folds constraintsText/uncertainties/commitment/alternatives into description, never dropping them', () => {
    const payload = buildDecisionCreatePayload(
      draft({
        decision: 'Should I take the job?',
        constraintsText: 'Must decide within two weeks.',
        uncertainties: 'Whether the team is a good fit.',
        commitment: 'Relocating for the role.',
        alternatives: 'Stay in my current role.',
      }),
    );

    expect(payload.description).toContain('Should I take the job?');
    expect(payload.description).toContain('Must decide within two weeks.');
    expect(payload.description).toContain('Whether the team is a good fit.');
    expect(payload.description).toContain('Relocating for the role.');
    expect(payload.description).toContain('Stay in my current role.');
  });

  it('handles every universal field being empty without throwing, and sends just the decision text', () => {
    const payload = buildDecisionCreatePayload(draft({ decision: 'Should I do this?' }));
    expect(payload.description).toBe('Should I do this?');
  });

  it('keeps the legacy budget/timeline/location/risk_tolerance mapping intact', () => {
    const payload = buildDecisionCreatePayload(
      draft({
        decision: 'Should I buy a car?',
        constraints: { budget: '800000', timeline: 'This month', location: 'Mumbai', riskTolerance: 'conservative' },
      }),
    );

    expect(payload.budget).toBe(800000);
    expect(payload.timeline).toBe('This month');
    expect(payload.location).toBe('Mumbai');
    expect(payload.risk_tolerance).toBe('conservative');
  });

  it('silently drops a non-numeric budget rather than sending an invalid value', () => {
    const payload = buildDecisionCreatePayload(
      draft({
        decision: 'Should I take the job?',
        constraints: { budget: 'not a number', timeline: '', location: '', riskTolerance: 'balanced' },
      }),
    );

    expect(payload.budget).toBeUndefined();
  });

  it('never sends a decision_type/category field - the backend schema has no such field', () => {
    const payload = buildDecisionCreatePayload(
      draft({ decision: 'Should I do this?', categories: ['career'] }),
    );

    expect('decision_type' in payload).toBe(false);
    expect('category' in payload).toBe(false);
    expect('categories' in payload).toBe(false);
  });

  it('folds commitment and extraDetails into description, never dropping them', () => {
    const payload = buildDecisionCreatePayload(
      draft({
        decision: 'Should I take the job?',
        commitment: 'Relocating and giving up my current lease.',
        extraDetails: { growth: 'Bigger scope, stronger team.' },
      }),
    );

    expect(payload.description).toContain('Should I take the job?');
    expect(payload.description).toContain('Relocating and giving up my current lease.');
    expect(payload.description).toContain('Bigger scope, stronger team.');
    expect(payload.description).toContain('Career growth');
  });
});
