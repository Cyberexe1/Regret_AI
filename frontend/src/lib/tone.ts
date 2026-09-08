import type {
  AssumptionSupport,
  Confidence,
  ExperimentStatus,
  GraphCategory,
  Reversibility,
  RiskLevel,
  Severity,
  Tone,
} from '@/types';

/**
 * Single source of truth for how semantic tone maps onto tokens.
 * Components read from here instead of re-deciding what "danger" looks like.
 */
export const toneSurface: Record<Tone, string> = {
  neutral: 'bg-surface-raised text-ink-secondary border-hairline',
  accent: 'bg-accent-soft text-accent-ink border-accent-line',
  success: 'bg-success-soft text-success-ink border-success-line',
  warning: 'bg-warning-soft text-warning-ink border-warning-line',
  danger: 'bg-danger-soft text-danger-ink border-danger-line',
  info: 'bg-info-soft text-info-ink border-info-line',
};

export const toneText: Record<Tone, string> = {
  neutral: 'text-ink-secondary',
  accent: 'text-accent-ink',
  success: 'text-success-ink',
  warning: 'text-warning-ink',
  danger: 'text-danger-ink',
  info: 'text-info-ink',
};

export const toneFill: Record<Tone, string> = {
  neutral: 'bg-ink-muted',
  accent: 'bg-accent',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-danger',
  info: 'bg-info',
};

/** Hex values for Recharts, which needs real colours rather than classes. */
export const toneHex: Record<Tone, string> = {
  neutral: 'var(--color-ink-muted)',
  accent: 'var(--color-accent)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  danger: 'var(--color-danger)',
  info: 'var(--color-info)',
};

/* --- Domain -> tone mappings ---------------------------------------------- */

export const assumptionSupportTone: Record<AssumptionSupport, Tone> = {
  supported: 'success',
  uncertain: 'warning',
  unsupported: 'danger',
};

export const assumptionSupportLabel: Record<AssumptionSupport, string> = {
  supported: 'Supported',
  uncertain: 'Uncertain',
  unsupported: 'Unsupported',
};

export const graphCategoryTone: Record<GraphCategory, Tone> = {
  decision: 'accent',
  assumption: 'info',
  evidence: 'neutral',
  uncertainty: 'warning',
  threshold: 'danger',
  outcome: 'success',
};

export const graphCategoryLabel: Record<GraphCategory, string> = {
  decision: 'Decision',
  assumption: 'Assumption',
  evidence: 'Evidence',
  uncertainty: 'Uncertainty',
  threshold: 'Threshold',
  outcome: 'Outcome',
};

export const riskTone: Record<RiskLevel, Tone> = {
  low: 'success',
  medium: 'warning',
  high: 'danger',
};

export const riskLabel: Record<RiskLevel, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
};

export const severityTone: Record<Severity, Tone> = {
  low: 'neutral',
  moderate: 'info',
  high: 'warning',
  critical: 'danger',
};

export const confidenceTone: Record<Confidence, Tone> = {
  low: 'danger',
  medium: 'warning',
  high: 'success',
};

export const confidenceLabel: Record<Confidence, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
};

export const reversibilityTone: Record<Reversibility, Tone> = {
  reversible: 'success',
  'costly-to-reverse': 'warning',
  irreversible: 'danger',
};

export const experimentStatusTone: Record<ExperimentStatus, Tone> = {
  proposed: 'neutral',
  running: 'info',
  inconclusive: 'warning',
  validated: 'success',
  invalidated: 'danger',
};

/** Regret index bands: low regret is good, high regret is a red flag. */
export function regretIndexTone(regretIndex: number): Tone {
  if (regretIndex >= 75) return 'danger';
  if (regretIndex >= 50) return 'warning';
  if (regretIndex >= 25) return 'info';
  return 'success';
}
