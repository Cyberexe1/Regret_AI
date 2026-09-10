/**
 * Pure mapping helpers from real backend fields (free-text importance,
 * 0.0-1.0 confidence floats, enum-ish strings) to presentational `Tone`/
 * label values, used across the Decision Report, Threshold visualization,
 * and Decision Graph.
 *
 * Nothing here invents a number or a category the backend didn't
 * provide - every function is a deterministic re-labelling of a real
 * field for display, never a fabricated metric.
 */

import type { EvidenceStatus, BlindspotEvidenceStatus, ExperimentStatus } from '@/api/types';
import type { Tone } from '@/types';

/** `importance`/`severity`-style free-text fields the agents emit
 * ("critical", "high", "medium", "low") - defensively lower-cased and
 * substring-matched since these are plain strings, not a fixed enum, on
 * the backend. */
export function importanceTone(importance: string | null | undefined): Tone {
  const value = (importance ?? '').toLowerCase();
  if (value.includes('critical')) return 'danger';
  if (value.includes('high')) return 'warning';
  if (value.includes('medium') || value.includes('moderate')) return 'info';
  if (value.includes('low')) return 'success';
  return 'neutral';
}

export function importanceLabel(importance: string | null | undefined): string {
  if (!importance) return 'Unrated';
  return importance.charAt(0).toUpperCase() + importance.slice(1);
}

/** Real 0.0-1.0 confidence float -> tone/label. */
export function confidenceTone(confidence: number | null | undefined): Tone {
  if (confidence === null || confidence === undefined) return 'neutral';
  if (confidence >= 0.67) return 'success';
  if (confidence >= 0.34) return 'warning';
  return 'danger';
}

export function confidenceLabel(confidence: number | null | undefined): string {
  if (confidence === null || confidence === undefined) return 'Unknown';
  if (confidence >= 0.67) return 'High';
  if (confidence >= 0.34) return 'Medium';
  return 'Low';
}

export function confidencePercent(confidence: number | null | undefined): number | undefined {
  if (confidence === null || confidence === undefined) return undefined;
  return Math.round(confidence * 100);
}

const EVIDENCE_STATUS_TONE: Record<EvidenceStatus, Tone> = {
  supported: 'success',
  contradicted: 'danger',
  not_addressed: 'warning',
  unverified: 'neutral',
};

const EVIDENCE_STATUS_LABEL: Record<EvidenceStatus, string> = {
  supported: 'Supported',
  contradicted: 'Contradicted',
  not_addressed: 'Not addressed',
  unverified: 'Unverified',
};

export function evidenceStatusTone(status: EvidenceStatus): Tone {
  return EVIDENCE_STATUS_TONE[status];
}

export function evidenceStatusLabel(status: EvidenceStatus): string {
  return EVIDENCE_STATUS_LABEL[status];
}

const BLINDSPOT_EVIDENCE_STATUS_TONE: Record<BlindspotEvidenceStatus, Tone> = {
  already_supported: 'success',
  partially_addressed: 'info',
  contradicted: 'danger',
  not_addressed: 'warning',
  unknown: 'neutral',
};

const BLINDSPOT_EVIDENCE_STATUS_LABEL: Record<BlindspotEvidenceStatus, string> = {
  already_supported: 'Already supported',
  partially_addressed: 'Partially addressed',
  contradicted: 'Contradicted',
  not_addressed: 'Not addressed',
  unknown: 'Unknown',
};

export function blindspotEvidenceStatusTone(status: BlindspotEvidenceStatus): Tone {
  return BLINDSPOT_EVIDENCE_STATUS_TONE[status];
}

export function blindspotEvidenceStatusLabel(status: BlindspotEvidenceStatus): string {
  return BLINDSPOT_EVIDENCE_STATUS_LABEL[status];
}

/** `regret_level`/`severity`-style free text on regret scenarios/challenges. */
export function severityTone(level: string | null | undefined): Tone {
  return importanceTone(level);
}

const EXPERIMENT_STATUS_TONE: Record<ExperimentStatus, Tone> = {
  recommended: 'accent',
  planned: 'neutral',
  active: 'info',
  completed: 'success',
  cancelled: 'neutral',
};

export function experimentStatusTone(status: ExperimentStatus): Tone {
  return EXPERIMENT_STATUS_TONE[status];
}

/** `validation_status` on a Threshold: "validated" | "provisional" | "unknown" (free text). */
export function validationStatusTone(status: string | null | undefined): Tone {
  const value = (status ?? '').toLowerCase();
  if (value === 'validated') return 'success';
  if (value === 'provisional') return 'warning';
  return 'neutral';
}

export function validationStatusLabel(status: string | null | undefined): string {
  const value = (status ?? '').toLowerCase();
  if (value === 'validated') return 'Validated';
  if (value === 'provisional') return 'Provisional';
  return 'Unknown';
}

/** True only when a threshold has an actual numeric value to plot - never
 * fabricated. Backend `threshold_value` is a free-text string (it may
 * hold a formula-derived value like "24" or a qualitative note), and
 * `lower_bound`/`upper_bound` are real floats when the threshold is a
 * range type. */
export function thresholdHasNumericValue(threshold: {
  threshold_value: string | null;
  lower_bound: number | null;
  upper_bound: number | null;
}): boolean {
  if (threshold.lower_bound !== null || threshold.upper_bound !== null) return true;
  if (threshold.threshold_value === null) return false;
  return !Number.isNaN(Number(threshold.threshold_value));
}
