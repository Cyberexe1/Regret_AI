/**
 * Universal decision categories and adaptive context configuration
 * (Step 25 - "Universal Decision Intake & Adaptive Context UI").
 *
 * REGRET ENGINE's analysis engine is decision-agnostic - nothing here
 * changes what the backend does. This module only decides which
 * CONTEXT FIELDS the intake form emphasizes and how they're labeled for
 * a given kind of decision, so a career decision doesn't get asked
 * about "monthly profit" and a technology decision doesn't get asked
 * about "customer demand."
 *
 * The category a user picks (or that gets inferred, see
 * `inferDecisionCategory`) is CONTEXTUAL METADATA for the frontend only
 * - it personalizes which fields are shown and how they're labeled. It
 * is never a hard requirement, and REGRET works identically for
 * "Other." The backend's own Decision Analyzer does its own,
 * independent classification during analysis from the full decision
 * text and context - the source of truth for what kind of decision this
 * actually is always remains the AI's analysis, never this frontend
 * guess (see this file's `inferDecisionCategory` doc comment).
 */

import type { DecisionCategory } from '@/types';

export type { DecisionCategory };

export interface DecisionCategoryOption {
  value: DecisionCategory;
  label: string;
}

export const decisionCategories: DecisionCategoryOption[] = [
  { value: 'career', label: 'Career' },
  { value: 'education', label: 'Education' },
  { value: 'personal', label: 'Personal' },
  { value: 'financial', label: 'Financial' },
  { value: 'business', label: 'Business' },
  { value: 'product', label: 'Product' },
  { value: 'technology', label: 'Technology' },
  { value: 'hiring', label: 'Hiring' },
  { value: 'operations', label: 'Operations' },
  { value: 'strategy', label: 'Strategy' },
  { value: 'relationships', label: 'Relationships' },
  { value: 'health', label: 'Health & Lifestyle' },
  { value: 'other', label: 'Other' },
];

const CATEGORY_LABEL_BY_VALUE: Record<DecisionCategory, string> = decisionCategories.reduce(
  (acc, option) => ({ ...acc, [option.value]: option.label }),
  {} as Record<DecisionCategory, string>,
);

export function decisionCategoryLabel(category: DecisionCategory): string {
  return CATEGORY_LABEL_BY_VALUE[category];
}

/* -------------------------------------------------------------------------- *
 * Smart context chips (Step 26 - "Smart Minimal Intake Experience")
 *
 * "Anything else that matters?" - clicking a chip reveals exactly one
 * field, nothing more. Every chip is one of two kinds:
 *
 *   - a CORE chip (financial/timing/location/risk/commitment) reveals a
 *     field that already exists on `DecisionDraft` (the legacy
 *     `constraints` object, or `commitment`) - so its data keeps
 *     flowing through the SAME backend mapping Step 25 already
 *     established, unchanged.
 *   - a NOTE chip (e.g. "Career growth", "Customer demand") reveals a
 *     small free-text field stored in `DecisionDraft.extraDetails`,
 *     keyed by the chip's own `id` - folded into `description` on
 *     submission (see `@/lib/decisionPayload`), never sent as a new
 *     structured backend field.
 *
 * Nothing here is authoritative or AI-driven - it is exactly the
 * "lightweight configuration" spec section 20 asks for, kept ready to
 * be swapped for backend-generated suggestions later without changing
 * this shape.
 * -------------------------------------------------------------------------- */

export type ContextChipKind = 'financial' | 'timing' | 'location' | 'risk' | 'commitment' | 'note';

export interface ContextChip {
  /** Stable id - for `note` chips, also the `extraDetails` key. */
  id: string;
  /** Chip label, e.g. "Compensation". */
  label: string;
  kind: ContextChipKind;
  /** Only present for `note` chips - the field label/placeholder shown
   * once the chip is selected. */
  fieldLabel?: string;
  fieldPlaceholder?: string;
}

/** "Other"/unknown decisions get no suggested chips at all (spec
 * section 6's universal fallback) - the five minimal fields are already
 * enough, and REGRET's own analysis discovers the rest. */
const NO_SUGGESTED_CHIPS: ContextChip[] = [];

export const contextChipsByCategory: Record<DecisionCategory, ContextChip[]> = {
  career: [
    { id: 'compensation', label: 'Compensation', kind: 'financial' },
    { id: 'location', label: 'Location', kind: 'location' },
    {
      id: 'growth',
      label: 'Growth',
      kind: 'note',
      fieldLabel: 'Career growth',
      fieldPlaceholder: 'How this affects your growth or trajectory.',
    },
    {
      id: 'work-life-balance',
      label: 'Work-life balance',
      kind: 'note',
      fieldLabel: 'Work-life balance',
      fieldPlaceholder: 'How this affects your day-to-day life.',
    },
    { id: 'timeline', label: 'Timeline', kind: 'timing' },
    { id: 'commitment', label: 'What you would give up', kind: 'commitment' },
  ],
  education: [
    { id: 'tuition', label: 'Tuition', kind: 'financial' },
    {
      id: 'duration',
      label: 'Duration',
      kind: 'note',
      fieldLabel: 'Duration',
      fieldPlaceholder: 'How long this would take.',
    },
    {
      id: 'career-outcome',
      label: 'Career outcome',
      kind: 'note',
      fieldLabel: 'Career outcome',
      fieldPlaceholder: 'What this is meant to lead to.',
    },
    { id: 'location', label: 'Location', kind: 'location' },
    {
      id: 'opportunity-cost',
      label: 'Opportunity cost',
      kind: 'note',
      fieldLabel: 'Opportunity cost',
      fieldPlaceholder: 'What you would give up to do this.',
    },
    { id: 'timeline', label: 'Timeline', kind: 'timing' },
  ],
  personal: [
    { id: 'cost', label: 'Cost', kind: 'financial' },
    { id: 'timeline', label: 'Time', kind: 'timing' },
    { id: 'location', label: 'Location', kind: 'location' },
    {
      id: 'lifestyle',
      label: 'Lifestyle',
      kind: 'note',
      fieldLabel: 'Lifestyle',
      fieldPlaceholder: 'How this affects your day-to-day life.',
    },
    {
      id: 'family',
      label: 'Family',
      kind: 'note',
      fieldLabel: 'Family',
      fieldPlaceholder: 'How this affects the people close to you.',
    },
    { id: 'commitment', label: 'What you would give up', kind: 'commitment' },
  ],
  financial: [
    { id: 'purchase-budget', label: 'Amount', kind: 'financial' },
    { id: 'timeline', label: 'Timeline', kind: 'timing' },
    {
      id: 'risk-appetite',
      label: 'Risk',
      kind: 'note',
      fieldLabel: 'Risk',
      fieldPlaceholder: 'How reversible or risky this is.',
    },
    { id: 'commitment', label: 'What you would give up', kind: 'commitment' },
  ],
  business: [
    { id: 'capital', label: 'Capital', kind: 'financial' },
    {
      id: 'revenue-target',
      label: 'Revenue target',
      kind: 'note',
      fieldLabel: 'Revenue target',
      fieldPlaceholder: 'What success would look like in numbers.',
    },
    {
      id: 'customers',
      label: 'Customers',
      kind: 'note',
      fieldLabel: 'Customer demand',
      fieldPlaceholder: 'What you know about real or expected demand.',
    },
    { id: 'timeline', label: 'Timeline', kind: 'timing' },
    { id: 'location', label: 'Location', kind: 'location' },
    { id: 'risk', label: 'Risk', kind: 'risk' },
  ],
  product: [
    { id: 'cost', label: 'Cost to build', kind: 'financial' },
    { id: 'timeline', label: 'Timeline', kind: 'timing' },
    {
      id: 'success-metric',
      label: 'Success metric',
      kind: 'note',
      fieldLabel: 'Success metric',
      fieldPlaceholder: 'How you would know this worked.',
    },
    { id: 'risk', label: 'Risk', kind: 'risk' },
  ],
  technology: [
    { id: 'cost', label: 'Cost', kind: 'financial' },
    {
      id: 'scale',
      label: 'Scale',
      kind: 'note',
      fieldLabel: 'Scale',
      fieldPlaceholder: 'Current or expected scale (traffic, data, users).',
    },
    {
      id: 'performance',
      label: 'Performance',
      kind: 'note',
      fieldLabel: 'Performance requirements',
      fieldPlaceholder: 'Latency, throughput, or other performance needs.',
    },
    {
      id: 'reliability',
      label: 'Reliability',
      kind: 'note',
      fieldLabel: 'Reliability requirements',
      fieldPlaceholder: 'Uptime, durability, or failure tolerance needs.',
    },
    {
      id: 'migration-effort',
      label: 'Migration effort',
      kind: 'note',
      fieldLabel: 'Migration effort',
      fieldPlaceholder: 'How much work this would realistically take.',
    },
    {
      id: 'team-capability',
      label: 'Team capability',
      kind: 'note',
      fieldLabel: 'Team expertise',
      fieldPlaceholder: "Your team's existing experience with this.",
    },
    { id: 'timeline', label: 'Timeline', kind: 'timing' },
  ],
  hiring: [
    { id: 'compensation', label: 'Compensation', kind: 'financial' },
    { id: 'location', label: 'Location', kind: 'location' },
    {
      id: 'team-needs',
      label: 'Team needs',
      kind: 'note',
      fieldLabel: 'Team needs',
      fieldPlaceholder: 'What the team actually needs right now.',
    },
    { id: 'timeline', label: 'Timeline', kind: 'timing' },
  ],
  operations: [
    { id: 'cost', label: 'Cost', kind: 'financial' },
    { id: 'timeline', label: 'Timeline', kind: 'timing' },
    {
      id: 'team-impact',
      label: 'Team impact',
      kind: 'note',
      fieldLabel: 'Team impact',
      fieldPlaceholder: 'How this affects the people doing the work.',
    },
    { id: 'risk', label: 'Risk', kind: 'risk' },
  ],
  strategy: [
    { id: 'resources', label: 'Resources required', kind: 'financial' },
    { id: 'timeline', label: 'Timeline', kind: 'timing' },
    {
      id: 'competitive-risk',
      label: 'Competitive risk',
      kind: 'note',
      fieldLabel: 'Competitive risk',
      fieldPlaceholder: 'What a competitor or the market could do.',
    },
    { id: 'risk', label: 'Risk', kind: 'risk' },
  ],
  relationships: [
    {
      id: 'stakes',
      label: 'What is at stake',
      kind: 'note',
      fieldLabel: 'What is at stake',
      fieldPlaceholder: 'What could genuinely change as a result.',
    },
    { id: 'timeline', label: 'Timeline', kind: 'timing' },
    { id: 'commitment', label: 'What you would give up', kind: 'commitment' },
  ],
  health: [
    { id: 'cost', label: 'Cost', kind: 'financial' },
    { id: 'timeline', label: 'Time', kind: 'timing' },
    {
      id: 'daily-life-impact',
      label: 'Daily life impact',
      kind: 'note',
      fieldLabel: 'Impact on daily life',
      fieldPlaceholder: 'How this changes your day-to-day.',
    },
  ],
  other: NO_SUGGESTED_CHIPS,
};

/** Every chip across every category, deduplicated by id - used by
 * `@/lib/decisionPayload` to look up a "note" chip's own field label
 * when composing the submitted description, so it always matches what
 * the user actually saw on screen. */
export const allContextChips: ContextChip[] = (() => {
  const seen = new Set<string>();
  const chips: ContextChip[] = [];
  for (const categoryChips of Object.values(contextChipsByCategory)) {
    for (const chip of categoryChips) {
      if (seen.has(chip.id)) continue;
      seen.add(chip.id);
      chips.push(chip);
    }
  }
  return chips;
})();

/** Deduplicated chips across every category the user has selected -
 * multi-category decisions (spec section 2) see the union of relevant
 * chips, never a forced single list.
 *
 * "Core" chip kinds (financial/timing/location/risk/commitment) all
 * write to the SAME underlying `DecisionDraft` field regardless of
 * which category suggested them (e.g. career's "Compensation" and
 * personal's "Cost" both reveal the one `budget` field) - so those are
 * deduplicated by KIND, keeping only the first category's own label/
 * chip for that kind. "Note" chips (free text, keyed by their own id)
 * are deduplicated by id as before, since two categories can suggest
 * the exact same note (e.g. "Location" isn't a note chip, but
 * "timeline"/"location" ids ARE reused deliberately across categories
 * to mean the same field). */
export function chipsForCategories(categories: DecisionCategory[]): ContextChip[] {
  if (categories.length === 0) return [];
  const seenIds = new Set<string>();
  const seenCoreKinds = new Set<ContextChipKind>();
  const chips: ContextChip[] = [];
  for (const category of categories) {
    for (const chip of contextChipsByCategory[category]) {
      if (chip.kind === 'note') {
        if (seenIds.has(chip.id)) continue;
        seenIds.add(chip.id);
      } else {
        if (seenCoreKinds.has(chip.kind)) continue;
        seenCoreKinds.add(chip.kind);
      }
      chips.push(chip);
    }
  }
  return chips;
}

/* -------------------------------------------------------------------------- *
 * Adaptive context configuration
 *
 * Every category shares the SAME six universal fields (desired outcome,
 * constraints, beliefs, uncertainties, commitment, alternatives - see
 * `DynamicContextSection`). What adapts per category is only:
 *   - the "what constraints matter" hint (drawn from the spec's own
 *     per-category "suggested context" lists, shown as guidance rather
 *     than as a dozen separate rigid inputs),
 *   - whether/how the legacy budget/timeline/location/risk-tolerance
 *     fields are labeled and which ones are worth showing at all.
 * -------------------------------------------------------------------------- */

export interface CategoryContextConfig {
  /** Guidance shown under the "Constraints" field - the category's own
   * "suggested context" vocabulary, never a set of separate mandatory
   * inputs. */
  constraintsHint: string;
  /** Contextual relabeling of the legacy `budget` field (section 8). */
  financialLabel: string;
  financialPlaceholder: string;
  /** Contextual relabeling of the "Location" field's placeholder -
   * always rendered (section 7: "Do not remove the ability to enter
   * these values"), only the framing adapts. */
  locationPlaceholder: string;
}

const GENERIC_CONTEXT_CONFIG: CategoryContextConfig = {
  constraintsHint: 'Time, money, commitments, location, eligibility, responsibilities, etc.',
  financialLabel: 'Financial commitment',
  financialPlaceholder: 'Money, time, or resources this decision would require, if any.',
  locationPlaceholder: 'Where this decision plays out, if location matters.',
};

export const contextFieldConfig: Record<DecisionCategory, CategoryContextConfig> = {
  career: {
    constraintsHint:
      'Current situation, compensation, career growth, location, work-life balance, timeline, alternatives, what matters most.',
    financialLabel: 'Financial impact',
    financialPlaceholder: 'Change in pay, relocation cost, lost equity, etc.',
    locationPlaceholder: 'Where the role is based, if relevant.',
  },
  education: {
    constraintsHint:
      'Program, cost, duration, career goal, alternatives, current skills, opportunity cost, geographic constraints.',
    financialLabel: 'Total cost',
    financialPlaceholder: 'Tuition, living costs, lost income while studying, etc.',
    locationPlaceholder: 'Where the program is based, if relevant.',
  },
  personal: {
    constraintsHint:
      'Budget, intended use, running cost, ownership duration, alternatives, financing, expected usage.',
    financialLabel: 'Financial commitment',
    financialPlaceholder: 'What this would cost you, upfront or ongoing.',
    locationPlaceholder: 'Where this applies, if relevant.',
  },
  financial: {
    constraintsHint:
      'Capital available, timeline, expected return, risk, alternatives, how reversible this is.',
    financialLabel: 'Purchase budget',
    financialPlaceholder: 'The amount you would actually commit.',
    locationPlaceholder: 'Where this applies, if relevant.',
  },
  business: {
    constraintsHint:
      'Capital, timeline, revenue target, location, customer demand, alternatives, risk tolerance.',
    financialLabel: 'Capital commitment',
    financialPlaceholder: 'Upfront capital plus ongoing costs, if known.',
    locationPlaceholder: 'Where the business operates.',
  },
  product: {
    constraintsHint:
      'User need, cost to build, effort required, success metric, alternatives, timeline.',
    financialLabel: 'Financial commitment',
    financialPlaceholder: 'Budget or cost to build, if relevant.',
    locationPlaceholder: 'Where this applies, if relevant.',
  },
  technology: {
    constraintsHint:
      'Current architecture, scale, performance requirements, cost, migration effort, reliability requirements, team expertise, alternatives, timeline.',
    financialLabel: 'Financial commitment',
    financialPlaceholder: 'Infrastructure, licensing, or migration cost, if known.',
    locationPlaceholder: 'Where this applies, if relevant.',
  },
  hiring: {
    constraintsHint:
      'Role, required skills, evidence from interviews, team needs, compensation, risks, alternatives, hiring urgency.',
    financialLabel: 'Financial commitment',
    financialPlaceholder: 'Compensation and onboarding cost, if relevant.',
    locationPlaceholder: 'Where the role is based, if relevant.',
  },
  operations: {
    constraintsHint:
      'Current process, capacity, cost, risk, team impact, timeline, alternatives.',
    financialLabel: 'Financial commitment',
    financialPlaceholder: 'Cost of making this change, if known.',
    locationPlaceholder: 'Where this applies, if relevant.',
  },
  strategy: {
    constraintsHint:
      'Market position, resources required, competitive risk, timeline, alternatives, what success looks like.',
    financialLabel: 'Financial commitment',
    financialPlaceholder: 'Resources or investment this direction would require.',
    locationPlaceholder: 'Where this applies, if relevant.',
  },
  relationships: {
    constraintsHint:
      "What's at stake, time horizon, the other person's perspective, alternatives, what you're uncertain about.",
    financialLabel: 'Financial commitment',
    financialPlaceholder: 'Rarely the deciding factor here - leave blank if not relevant.',
    locationPlaceholder: 'Where this applies, if relevant.',
  },
  health: {
    constraintsHint:
      'Time commitment, cost, impact on daily life, alternatives, what matters most.',
    financialLabel: 'Financial commitment',
    financialPlaceholder: 'Cost, if any, of this choice.',
    locationPlaceholder: 'Where this applies, if relevant.',
  },
  other: GENERIC_CONTEXT_CONFIG,
};

export function getContextFieldConfig(category: DecisionCategory | null): CategoryContextConfig {
  if (category === null) return GENERIC_CONTEXT_CONFIG;
  return contextFieldConfig[category];
}

/* -------------------------------------------------------------------------- *
 * Client-side category inference (fallback only)
 *
 * This is a lightweight, deterministic keyword heuristic used ONLY to
 * suggest a category while the user types, before they've picked one
 * themselves - a UX convenience, never authoritative. The backend's own
 * Decision Analyzer performs its own real classification from the full
 * decision text during analysis; if/when that classification is ever
 * exposed back to the frontend, it should take priority over this
 * function's guess (see this file's module docstring). Kept intentionally
 * simple - this is not a decision-intelligence algorithm, just a rough
 * signal for which context fields to suggest before submission.
 * -------------------------------------------------------------------------- */

const CATEGORY_KEYWORDS: Record<Exclude<DecisionCategory, 'other'>, string[]> = {
  career: ['job', 'offer', 'salary', 'promotion', 'career', 'relocat', 'employer', 'role at'],
  education: ['degree', 'course', 'university', 'college', 'ms in', 'masters', 'phd', 'certification', 'study', 'program'],
  personal: ['buy', 'purchase', 'car', 'house', 'apartment', 'move to', 'moving to'],
  financial: ['invest', 'stock', 'fund', 'loan', 'mortgage', 'savings', 'crore', 'lakh', 'rupee', '₹', '$'],
  business: ['startup', 'business', 'launch', 'venture', 'kitchen', 'store', 'shop', 'franchise', 'company'],
  product: ['feature', 'product', 'build', 'launch our', 'roadmap'],
  technology: ['migrat', 'database', 'postgres', 'dynamodb', 'architecture', 'infrastructure', 'framework', 'tech stack', 'server'],
  hiring: ['hire', 'candidate', 'interview', 'recruit'],
  operations: ['process', 'workflow', 'operations', 'vendor', 'supplier'],
  strategy: ['strategy', 'strategic', 'market', 'expand', 'pivot'],
  relationships: ['relationship', 'partner', 'marry', 'marriage', 'friend', 'family'],
  health: ['health', 'gym', 'diet', 'therapy', 'surgery', 'fitness'],
};

/** Returns the best-guess category from the decision text, or `null` if
 * no keyword matched confidently enough - `null` is a legitimate result,
 * never forced into a guess. */
export function inferDecisionCategory(decisionText: string): DecisionCategory | null {
  const normalized = decisionText.toLowerCase();
  if (normalized.trim().length === 0) return null;

  for (const [category, keywords] of Object.entries(CATEGORY_KEYWORDS) as [
    Exclude<DecisionCategory, 'other'>,
    string[],
  ][]) {
    if (keywords.some((keyword) => normalized.includes(keyword))) {
      return category;
    }
  }
  return null;
}

/* -------------------------------------------------------------------------- *
 * Example decisions ("Try an example" / "Explore example decisions")
 *
 * Populates the real form fields on click - not a separate demo mode,
 * not hardcoded into the default/empty state. The FIRST example
 * (career) is also the page's neutral default placeholder text, so the
 * product never opens on a business/investment scenario.
 * -------------------------------------------------------------------------- */

export interface ExampleDecision {
  /** One or more - see `DecisionTypeSelector`'s multi-select support
   * (Step 26 section 2). The first entry is used as the card's own
   * eyebrow label. */
  categories: DecisionCategory[];
  /** Short label shown on the example card, e.g. "Accept a new job?" */
  cardLabel: string;
  decision: string;
  desiredOutcome?: string;
  constraints?: string;
  beliefs?: string;
  uncertainties?: string;
  commitment?: string;
  alternatives?: string;
  financialCommitment?: string;
  timing?: string;
  location?: string;
}

export const exampleDecisions: ExampleDecision[] = [
  {
    // Deliberately spans two categories (spec section 2's own example) -
    // a relocation-driven job offer is genuinely both Career and Personal.
    categories: ['career', 'personal'],
    cardLabel: 'Accept a new job?',
    decision:
      'Should I accept a software engineering offer that pays more but requires relocating?',
    desiredOutcome: 'Faster career growth without regretting the move in a year.',
    constraints: 'Partner would need to find work in the new city. Lease ends in two months.',
    beliefs: 'I believe the new role gives me more scope and a stronger team.',
    uncertainties: "Whether the new city's cost of living actually leaves me better off.",
    commitment: 'Relocating, breaking the current lease, my partner changing jobs.',
    alternatives: 'Stay and ask for a counter-offer, or negotiate a remote arrangement.',
    financialCommitment: 'Relocation cost, and giving up unvested equity at my current job.',
    timing: 'Need to respond to the offer within two weeks.',
    location: 'Moving from Bangalore to Hyderabad.',
  },
  {
    categories: ['education'],
    cardLabel: 'Choose an MS program?',
    decision: 'Should I pursue an MS in AI?',
    desiredOutcome: 'A credible path into an ML engineering role within two years of graduating.',
    constraints: 'Would need to leave my current job. Program is two years full-time.',
    beliefs: 'I believe the degree meaningfully improves my odds versus staying self-taught.',
    uncertainties: 'Whether employers actually weight the degree over demonstrated project work.',
    commitment: 'Two years of lost income, tuition, and relocating for the program.',
    alternatives: 'Self-study plus a part-time certification, or a shorter bootcamp.',
    financialCommitment: 'Tuition plus two years of foregone salary.',
    timing: 'Applications for the next intake close in three months.',
  },
  {
    categories: ['financial'],
    cardLabel: 'Invest ₹5 lakh?',
    decision: 'Should I invest ₹5 lakh in this opportunity?',
    desiredOutcome: 'Meaningful return without risking money I need in the next two years.',
    constraints: 'This is money earmarked for a down payment in three years.',
    beliefs: 'I believe the opportunity is undervalued relative to its real risk.',
    uncertainties: "How liquid this investment actually is if I need the money sooner.",
    commitment: '₹5 lakh of capital, locked up for an uncertain period.',
    alternatives: 'A lower-return but more liquid instrument, or waiting six months.',
    financialCommitment: '₹5,00,000.',
    timing: 'The opportunity closes at the end of the month.',
  },
  {
    categories: ['personal'],
    cardLabel: 'Buy a car?',
    decision: 'Should I buy a car this year?',
    desiredOutcome: 'Reliable transport without straining my monthly budget.',
    constraints: 'No dedicated parking at home. Mostly city driving.',
    beliefs: 'I believe owning will be cheaper than my current cab spend within two years.',
    uncertainties: 'Whether my actual usage justifies ownership versus renting when needed.',
    commitment: 'A multi-year loan and ongoing maintenance cost.',
    alternatives: 'Keep using cabs/rentals, or buy used instead of new.',
    financialCommitment: 'Roughly ₹8-12 lakh depending on model.',
    timing: 'No hard deadline, but my current lease on a rental ends in two months.',
    location: 'Primarily city driving in Mumbai.',
  },
  {
    categories: ['business'],
    cardLabel: 'Launch a new venture?',
    decision: 'Should I invest ₹5 lakh to launch a cloud kitchen?',
    desiredOutcome: 'A cloud kitchen that reaches profitability within its first year.',
    constraints: 'One kitchen lease. No second round of funding if this fails.',
    beliefs: 'I believe there is real repeat demand in this neighborhood.',
    uncertainties: 'Whether the repeat-order rate is high enough to sustain the model.',
    commitment: 'Capital, a lease commitment, and my full-time attention.',
    alternatives: 'A smaller pilot from a shared kitchen, or not launching at all.',
    financialCommitment: '₹5,00,000 upfront, plus ongoing monthly costs.',
    timing: 'Want to launch within the next quarter.',
    location: 'Mumbai.',
  },
  {
    categories: ['technology'],
    cardLabel: 'Migrate our system?',
    decision: 'Should we migrate our production PostgreSQL database to DynamoDB?',
    desiredOutcome: 'Lower latency at scale without a costly, risky migration.',
    constraints: 'Cannot afford significant downtime. Team has limited DynamoDB experience.',
    beliefs: 'I believe our access patterns fit a single-table design well.',
    uncertainties: 'Whether our reporting/analytics queries still work well without joins.',
    commitment: 'Engineering time for the migration and a period of dual-running both systems.',
    alternatives: 'Optimize the existing PostgreSQL setup, or a managed Postgres-compatible service.',
    financialCommitment: 'Engineering time plus dual-running infrastructure cost during migration.',
    timing: 'Would want to start within the next sprint planning cycle.',
  },
  {
    categories: ['hiring'],
    cardLabel: 'Hire this candidate?',
    decision: 'Should I hire this candidate?',
    desiredOutcome: 'A hire who is productive within the first quarter and stays a year or more.',
    constraints: 'Need someone ramped before the next release cycle.',
    beliefs: "I believe their interview performance reflects how they'd actually work here.",
    uncertainties: 'Whether they can operate independently without close guidance.',
    commitment: 'Compensation, onboarding time, and a team seat that would otherwise stay open.',
    alternatives: 'Keep the role open longer, or hire a more senior/more junior candidate instead.',
    financialCommitment: 'Their compensation package plus onboarding cost.',
    timing: 'Need to give them an answer this week.',
  },
  {
    categories: ['product', 'strategy'],
    cardLabel: 'Launch this product?',
    decision: 'Should I launch this product?',
    desiredOutcome: 'A product that meaningfully expands our addressable market.',
    constraints: 'Limited engineering headcount. One more quarter of runway allocated to this.',
    beliefs: 'I believe our existing customers would pay for this.',
    uncertainties: 'Whether this is a real, underserved need or just a vocal minority.',
    commitment: 'One quarter of engineering time diverted from the current roadmap.',
    alternatives: 'Validate with a smaller prototype first, or focus the quarter elsewhere.',
    financialCommitment: 'One quarter of engineering cost.',
    timing: 'Would need to start this quarter to hit the target launch window.',
  },
];
