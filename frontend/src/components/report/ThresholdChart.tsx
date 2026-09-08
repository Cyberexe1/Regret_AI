import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ChartTooltip } from '@/components/charts/ChartTooltip';
import { axisDefaults, gridDefaults } from '@/components/charts/chartTheme';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import type { RegretThreshold } from '@/types';

/** "-₹58k" / "₹16k". Compact enough for an axis tick. */
function formatContribution(value: number | string | undefined): string {
  const numeric = typeof value === 'number' ? value : Number(value ?? 0);
  const sign = numeric < 0 ? '-' : '';
  return `${sign}₹${Math.abs(Math.round(numeric / 1000))}k`;
}

export interface ThresholdChartProps {
  threshold: RegretThreshold;
}

/**
 * Contribution as a function of repeat rate, with the current estimate, the
 * critical threshold and the safe zone marked directly on the plot.
 */
export function ThresholdChart({ threshold }: ThresholdChartProps) {
  const [low, high] = threshold.currentRange;
  const [domainMin, domainMax] = threshold.domain;

  /**
   * Recharts reference labels neither wrap nor shrink, so below `sm` they
   * collide and clip. The legend beneath the chart carries the same meaning.
   */
  const showInlineLabels = useMediaQuery('(min-width: 640px)');

  return (
    <div className="h-64 w-full sm:h-72">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={threshold.curve} margin={{ top: 18, right: 14, bottom: 4, left: 0 }}>
          <CartesianGrid {...gridDefaults} />

          {/* Safe zone: at or above the threshold */}
          <ReferenceArea
            x1={threshold.thresholdValue}
            x2={domainMax}
            fill="var(--color-success)"
            fillOpacity={0.08}
            label={
              showInlineLabels
                ? {
                    value: 'Safe zone',
                    position: 'insideTopRight',
                    fill: 'var(--color-success-ink)',
                    fontSize: 11,
                  }
                : undefined
            }
          />

          {/* Where the decision stands today */}
          <ReferenceArea
            x1={low}
            x2={high}
            fill="var(--color-warning)"
            fillOpacity={0.18}
            label={
              showInlineLabels
                ? {
                    value: 'Current',
                    position: 'insideTopLeft',
                    fill: 'var(--color-warning-ink)',
                    fontSize: 11,
                  }
                : undefined
            }
          />

          <XAxis
            {...axisDefaults}
            dataKey="rate"
            type="number"
            domain={[domainMin, domainMax]}
            ticks={[14, 18, 22, 26, 30]}
            tickFormatter={(value: number) => `${value}%`}
          />
          <YAxis {...axisDefaults} width={54} tickFormatter={formatContribution} />

          {/* Break-even */}
          <ReferenceLine
            y={0}
            stroke="var(--color-ink-faint)"
            strokeDasharray="3 3"
            label={{
              value: 'Break-even',
              position: 'insideBottomLeft',
              fill: 'var(--color-ink-muted)',
              fontSize: 11,
            }}
          />

          {/* The threshold that decides the decision */}
          <ReferenceLine
            x={threshold.thresholdValue}
            stroke="var(--color-danger)"
            strokeDasharray="4 4"
            strokeWidth={1.5}
            label={
              showInlineLabels
                ? {
                    value: `Threshold ${threshold.thresholdValue}%`,
                    position: 'top',
                    fill: 'var(--color-danger-ink)',
                    fontSize: 11,
                  }
                : undefined
            }
          />

          <Area
            type="monotone"
            dataKey="contribution"
            stroke="var(--color-accent)"
            strokeWidth={2}
            fill="var(--color-accent)"
            fillOpacity={0.1}
            dot={false}
            activeDot={{ r: 4, fill: 'var(--color-accent)', stroke: 'var(--color-canvas)' }}
            isAnimationActive={false}
          />

          <Tooltip
            content={
              <ChartTooltip
                formatValue={formatContribution}
                formatLabel={(label) => `${label}% repeat rate`}
              />
            }
            cursor={{ stroke: 'var(--color-hairline-strong)', strokeWidth: 1 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
