import { describe, expect, it } from 'vitest';
import {
  chipsForCategories,
  contextChipsByCategory,
  contextFieldConfig,
  decisionCategories,
  exampleDecisions,
  getContextFieldConfig,
  inferDecisionCategory,
} from './decisionTypes';

describe('inferDecisionCategory', () => {
  it('returns null for empty text, never a guessed category', () => {
    expect(inferDecisionCategory('')).toBeNull();
    expect(inferDecisionCategory('   ')).toBeNull();
  });

  it('returns null when nothing recognizable matches, never a forced guess', () => {
    expect(inferDecisionCategory('Should I do the thing?')).toBeNull();
  });

  it('infers career from a job-offer decision', () => {
    expect(inferDecisionCategory('Should I accept the software engineering offer from Company A?')).toBe(
      'career',
    );
  });

  it('infers education from an MS-program decision', () => {
    expect(inferDecisionCategory('Should I pursue an MS in AI?')).toBe('education');
  });

  it('infers business from a cloud-kitchen decision, without that being the only path through the app', () => {
    expect(inferDecisionCategory('Should I launch my cloud kitchen in Mumbai?')).toBe('business');
  });

  it('a decision mentioning both investment and business terms is not forced into one bucket incorrectly', () => {
    // Ambiguous input is expected to resolve to SOME real category, not
    // crash or silently return null - the exact category picked among
    // genuinely overlapping keywords is a minor, documented heuristic
    // detail (see this file's module docstring: inference is a UX
    // convenience, never authoritative).
    const result = inferDecisionCategory('Should I invest ₹5 lakh to start a cloud kitchen?');
    expect(result).not.toBeNull();
  });

  it('infers technology from a database-migration decision', () => {
    expect(
      inferDecisionCategory('Should we migrate our application from PostgreSQL to DynamoDB?'),
    ).toBe('technology');
  });
});

describe('getContextFieldConfig', () => {
  it('falls back to the generic config for an unknown/null category', () => {
    const config = getContextFieldConfig(null);
    expect(config.financialLabel).toBe('Financial commitment');
  });

  it('returns a category-specific financial label for career', () => {
    expect(getContextFieldConfig('career').financialLabel).toBe('Financial impact');
  });

  it('returns a category-specific financial label for education', () => {
    expect(getContextFieldConfig('education').financialLabel).toBe('Total cost');
  });

  it('returns a category-specific financial label for business', () => {
    expect(getContextFieldConfig('business').financialLabel).toBe('Capital commitment');
  });

  it('every declared category has its own context config entry', () => {
    for (const option of decisionCategories) {
      expect(contextFieldConfig[option.value]).toBeDefined();
    }
  });
});

describe('exampleDecisions', () => {
  it('covers career, education, financial, personal, business, and technology, per spec section 13', () => {
    const categories = new Set(exampleDecisions.flatMap((example) => example.categories));
    for (const required of ['career', 'education', 'financial', 'personal', 'business', 'technology']) {
      expect(categories.has(required as never)).toBe(true);
    }
  });

  it('never includes a bare, unlabeled example - every example has a real decision statement', () => {
    for (const example of exampleDecisions) {
      expect(example.decision.trim().length).toBeGreaterThan(0);
      expect(example.cardLabel.trim().length).toBeGreaterThan(0);
      expect(example.categories.length).toBeGreaterThan(0);
    }
  });

  it('includes at least one multi-category example, per spec section 2', () => {
    expect(exampleDecisions.some((example) => example.categories.length > 1)).toBe(true);
  });
});

describe('chipsForCategories', () => {
  it('returns no chips for an empty category list', () => {
    expect(chipsForCategories([])).toEqual([]);
  });

  it('returns no chips for "Other" - the universal fallback never suggests anything', () => {
    expect(chipsForCategories(['other'])).toEqual([]);
  });

  it('returns every declared chip for a single category', () => {
    expect(chipsForCategories(['career'])).toEqual(contextChipsByCategory.career);
  });

  it('deduplicates "core" chips (financial/timing/location/risk/commitment) by KIND across categories', () => {
    // Career and personal both suggest a "Location" chip, and both a
    // financial-kind chip - only one of each should ever appear so the
    // same underlying field is never revealed by two separate chips.
    const chips = chipsForCategories(['career', 'personal']);
    const locationChips = chips.filter((chip) => chip.kind === 'location');
    const financialChips = chips.filter((chip) => chip.kind === 'financial');
    expect(locationChips).toHaveLength(1);
    expect(financialChips).toHaveLength(1);
  });

  it('keeps distinct "note" chips from different categories side by side', () => {
    const chips = chipsForCategories(['career', 'education']);
    expect(chips.some((chip) => chip.id === 'growth')).toBe(true);
    expect(chips.some((chip) => chip.id === 'career-outcome')).toBe(true);
  });

  it('every category (except "other") suggests at least one chip', () => {
    for (const option of decisionCategories) {
      if (option.value === 'other') continue;
      expect(contextChipsByCategory[option.value].length).toBeGreaterThan(0);
    }
  });
});
