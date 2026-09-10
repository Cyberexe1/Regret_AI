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

/** Everything captured on the intake page before a decision is created
 * through the real API. Mapped to `ApiDecisionCreate` on submission - see
 * `useDecisionSubmission`. */
export interface DecisionDraft {
  decision: string;
  desiredOutcome: string;
  constraints: {
    budget: string;
    timeline: string;
    location: string;
    riskTolerance: RiskTolerance;
  };
  beliefs: string;
  evidence: DraftEvidenceFile[];
  sourceUrl: string;
  /** ISO timestamp of the moment the draft was submitted. */
  submittedAt?: string;
}
