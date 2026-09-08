import type { RiskLevel, Tone } from './index';

/* -------------------------------------------------------------------------- *
 * Experiment detail
 *
 * The running view of an experiment: what it asks, how far along it is, what it
 * has produced, and what the user may do next. Distinct from `Experiment`,
 * which is the record of the experiment itself.
 * -------------------------------------------------------------------------- */

/** Coarse lifecycle grouping used in listings. */
export type ExperimentPhase = 'Proposed' | 'Running' | 'Completed';

export interface ExperimentResultMetric {
  label: string;
  value: string;
  hint?: string;
  tone?: Tone;
}

export interface ExperimentChoice {
  id: string;
  label: string;
  description: string;
  /** Route this path leads to, where one exists. */
  to?: string;
  emphasis: 'primary' | 'secondary' | 'ghost';
  /** Confirmation copy once the path is recorded locally. */
  recorded: string;
}

export interface ExperimentVerdict {
  headline: string;
  detail: string;
  tone: Tone;
  /** Offered as equals: none is presented as the correct answer. */
  choices: ExperimentChoice[];
}

export interface ExperimentDetail {
  experimentId: string;
  question: string;
  successThreshold: string;
  failureThreshold: string;
  expectedLearning: RiskLevel;
  durationDays: number;
  currentDay: number;
  /** 0-100, elapsed against the planned window. */
  progress: number;
  /** Day numbers marked on the tracker. */
  milestones: number[];
  measures: string[];
  results: ExperimentResultMetric[];
  /** Observed value and threshold for the inline comparison bar. */
  observedValue: number;
  thresholdValue: number;
  scaleMax: number;
  statusLabel: string;
  statusTone: Tone;
  verdict: ExperimentVerdict;
}
