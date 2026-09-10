import type { GraphCategory, Tone } from '@/types';

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

/* --- Domain -> tone mappings ------------------------------------------------ *
 * Real backend-derived mappings (assumption/blindspot/threshold/experiment
 * status, confidence, importance) now live in `@/lib/reportModel` -
 * everything below here is presentational only (the graph's fixed
 * category set) and unrelated to any backend enum. */

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
