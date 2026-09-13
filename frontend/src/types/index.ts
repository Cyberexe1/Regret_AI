import type { LucideIcon } from 'lucide-react';

export * from './graph';
export * from './report';

/* -------------------------------------------------------------------------- *
 * Shared UI primitives
 * -------------------------------------------------------------------------- */

/** Semantic colour intent shared by Badge, Progress, Tooltip and cards. */
export type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';

export type Size = 'sm' | 'md' | 'lg';

export type Currency = 'USD' | 'INR';

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  /** Shown as a small counter in the sidebar when present. */
  count?: number;
  /** Lifts the item above the rest of the nav as the primary action. */
  emphasis?: boolean;
}

/* -------------------------------------------------------------------------- *
 * Decision intake (pre-submission, browser-only form state)
 * -------------------------------------------------------------------------- */

/** How much downside the user is willing to carry on this decision. Sent
 * to the backend as `risk_tolerance` (a free-text string there). */
export type RiskTolerance = 'conservative' | 'balanced' | 'aggressive';

/**
 * Universal decision category (Step 25 - "Universal Decision Intake &
 * Adaptive Context UI"). Frontend-only, contextual metadata used to
 * personalize which intake fields/labels are shown - never a hard
 * requirement, and never sent to the backend as a structured field (the
 * current `DecisionCreate` schema has no such field - see
 * `@/data/decisionTypes` for how this folds into the existing
 * `description`/`beliefs` text instead). The backend's own Decision
 * Analyzer performs its own independent classification from the full
 * decision text during analysis; that classification, not this
 * frontend selection, is the source of truth about what kind of
 * decision this actually is.
 */
export type DecisionCategory =
  | 'career'
  | 'education'
  | 'personal'
  | 'financial'
  | 'business'
  | 'product'
  | 'technology'
  | 'hiring'
  | 'operations'
  | 'strategy'
  | 'relationships'
  | 'health'
  | 'other';

/**
 * A file the user attached during intake, before it has been uploaded.
 * Metadata only for display; the underlying `File` blob lives alongside
 * it in `DraftEvidenceFileWithBlob` (see `@/hooks/useEvidenceFiles`) so
 * it can actually be uploaded once the decision has a real id.
 */
export interface DraftEvidenceFile {
  id: string;
  name: string;
  /** Size in bytes. */
  size: number;
  mimeType: string;
}

/**
 * Everything captured on the intake page before a decision is created
 * through the real API. Mapped to `ApiDecisionCreate` on submission - see
 * `useDecisionSubmission`.
 *
 * Step 26 ("Smart Minimal Intake Experience") introduced `desiredOutcome`/
 * `constraintsText`/`beliefs`/`uncertainties`/`alternatives`/`commitment`
 * as always-optional context fields; Step 27 ("Adaptive Decision
 * Interview Agent") replaced the always-visible form these fields used
 * to power with a conversational interview that discovers the same
 * information adaptively (see `useInterview`/`InterviewConsole`) - these
 * fields remain on the draft only for the "Try an example" pre-fill path
 * and the legacy pre-interview submission fallback. `categories`
 * replaces Step 25's single `category` - a decision
 * can genuinely span more than one (e.g. "accept a higher-paying job
 * that requires relocating" is Career + Personal), and none of them are
 * ever a hard requirement (see `DecisionCategory`'s doc comment). Only
 * `decision` is required; every other field is optional.
 */
export interface DecisionDraft {
  decision: string;
  /** Contextual metadata only, zero or more - see `DecisionCategory`'s
   * doc comment. */
  categories: DecisionCategory[];
  desiredOutcome: string;
  /** Free-text: "what could realistically limit this decision?" (Step
   * 26 section 3B) - distinct from the legacy structured `constraints`
   * object below, which still carries the budget/timeline/location/risk
   * fields the backend has dedicated columns for. */
  constraintsText: string;
  beliefs: string;
  /** "What are you least sure about?" (Step 26 section 3D). */
  uncertainties: string;
  /** "What are the alternatives?" (Step 26 section 3E). */
  alternatives: string;
  /** "What are you putting at stake?" (Step 26 section 7) - progressively
   * disclosed via the `commitment`-kind chip, never shown by default. */
  commitment: string;
  /** Free-text values for category-specific "note" chips (e.g. "Career
   * growth", "Customer demand"), keyed by the chip's stable id - see
   * `@/data/decisionTypes`'s `ContextChip`. Folded into `description` on
   * submission, each labeled by that chip's own field label. */
  extraDetails: Record<string, string>;
  /** Financial/timing/location/risk - progressively disclosed via chips,
   * never shown by default (Step 26 sections 9-11). */
  constraints: {
    budget: string;
    timeline: string;
    location: string;
    riskTolerance: RiskTolerance;
  };
  evidence: DraftEvidenceFile[];
  sourceUrl: string;
  /** ISO timestamp of the moment the draft was submitted. */
  submittedAt?: string;
}
