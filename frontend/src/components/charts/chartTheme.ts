/**
 * Recharts needs concrete colour strings rather than Tailwind classes.
 * These read straight from the design tokens so charts restyle with the theme.
 */
export const chartTokens = {
  accent: 'var(--color-accent)',
  accentSoft: 'var(--color-accent-soft)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  danger: 'var(--color-danger)',
  info: 'var(--color-info)',
  grid: 'var(--color-hairline)',
  axis: 'var(--color-ink-faint)',
  tick: 'var(--color-ink-muted)',
} as const;

/** Spread onto `<XAxis />` / `<YAxis />`. */
export const axisDefaults = {
  tickLine: false,
  axisLine: false,
  stroke: chartTokens.axis,
  tick: { fill: chartTokens.tick, fontSize: 11 },
} as const;

/** Spread onto `<CartesianGrid />`. Horizontal-only keeps charts quiet. */
export const gridDefaults = {
  stroke: chartTokens.grid,
  strokeDasharray: '2 4',
  vertical: false,
} as const;

/** Spread onto `<Tooltip />` to remove the default white cursor highlight. */
export const tooltipDefaults = {
  cursor: { stroke: chartTokens.grid, strokeWidth: 1 },
} as const;
