import type { LucideIcon } from 'lucide-react';

/* -------------------------------------------------------------------------- *
 * Shared UI primitives
 * -------------------------------------------------------------------------- */

/** Semantic colour intent shared by Badge, Progress, Tooltip and cards. */
export type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';

export type Size = 'sm' | 'md' | 'lg';

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  /** Shown as a small counter in the sidebar when present. */
  count?: number;
}

/* -------------------------------------------------------------------------- *
 * Decision domain
 * -------------------------------------------------------------------------- */

export const DECISION_STATUSES = [
  'draft',
  'analyzing',
  'analyzed',
  'testing',
  'committed',
  'abandoned',
] as const;

export type DecisionStatus = (typeof DECISION_STATUSES)[number];

export const DECISION_DOMAINS = [
  'career',
  'product',
  'financial',
  'hiring',
  'relocation',
  'technology',
  'business-model',
] as const;

export type DecisionDomain = (typeof DECISION_DOMAINS)[number];

/** How hard it is to walk the decision back once committed. */
export type Reversibility = 'reversible' | 'costly-to-reverse' | 'irreversible';

export type Severity = 'low' | 'moderate' | 'high' | 'critical';

export type Confidence = 'low' | 'medium' | 'high';

export type RegretHorizon = '6-months' | '1-year' | '3-years' | '5-years';

/**
 * An assumption the decision silently depends on. `origin` separates what the
 * user wrote down from what the engine inferred was being taken for granted.
 */
export interface Assumption {
  id: string;
  statement: string;
  origin: 'stated' | 'hidden';
  confidence: Confidence;
  /** 0-100. How easily this assumption breaks under real-world pressure. */
  fragility: number;
  evidence: 'none' | 'anecdotal' | 'partial' | 'documented';
  impactIfWrong: Severity;
}

/** A category of consideration missing from the user's framing. */
export interface BlindSpot {
  id: string;
  title: string;
  description: string;
  severity: Severity;
  /** Question that forces the blind spot into the open. */
  probingQuestion: string;
}

/** A specific, observable condition under which the decision fails. */
export interface FailureCondition {
  id: string;
  trigger: string;
  mechanism: string;
  /** 0-1 estimated likelihood within the stated horizon. */
  probability: number;
  horizon: RegretHorizon;
  severity: Severity;
  earlyWarningSignal: string;
}

/** A narrated future in which the user looks back on this decision. */
export interface RegretScenario {
  id: string;
  horizon: RegretHorizon;
  title: string;
  narrative: string;
  /** 0-100 projected regret intensity. */
  regretScore: number;
  /** 0-1 estimated likelihood of this branch. */
  likelihood: number;
  recoveryCost: Reversibility;
}

export type ExperimentStatus = 'proposed' | 'running' | 'inconclusive' | 'validated' | 'invalidated';

/** The cheapest test that could move belief before committing. */
export interface Experiment {
  id: string;
  decisionId: string;
  title: string;
  hypothesis: string;
  method: string;
  status: ExperimentStatus;
  cost: {
    currency: 'USD';
    amount: number;
    days: number;
    effort: 'low' | 'medium' | 'high';
  };
  /** 0-100. How much uncertainty this experiment is expected to remove. */
  informationGain: number;
  /** Which assumption ids this experiment attacks. */
  targets: string[];
  successCriteria: string[];
  createdAt: string;
  finding?: string;
}

/** One point on the commit-now vs wait-and-test regret curve. */
export interface RegretTrajectoryPoint {
  horizonMonths: number;
  commitNow: number;
  runExperiment: number;
}

export interface DecisionAnalysis {
  /** 0-100 composite of fragility, irreversibility and blind-spot severity. */
  regretIndex: number;
  /** 0-100 confidence the engine has in its own read of the decision. */
  analysisConfidence: number;
  reversibility: Reversibility;
  verdictSummary: string;
  assumptions: Assumption[];
  blindSpots: BlindSpot[];
  failureConditions: FailureCondition[];
  regretScenarios: RegretScenario[];
  trajectory: RegretTrajectoryPoint[];
  /** Id of the recommended cheapest experiment. */
  recommendedExperimentId: string | null;
}

export interface Decision {
  id: string;
  title: string;
  /** The decision written in the user's own words. */
  statement: string;
  domain: DecisionDomain;
  status: DecisionStatus;
  stakes: 'low' | 'moderate' | 'high' | 'defining';
  createdAt: string;
  updatedAt: string;
  /** ISO date by which the decision must be made, when one exists. */
  commitBy?: string;
  analysis?: DecisionAnalysis;
}
