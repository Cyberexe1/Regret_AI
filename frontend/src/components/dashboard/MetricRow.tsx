import { StatCard } from '@/components/cards/StatCard';
import { Reveal } from '@/components/Reveal';
import type { DashboardMetric } from '@/lib/buildDashboard';

export interface MetricRowProps {
  metrics: DashboardMetric[];
}

/** Four compact figures: context for the page, not the headline. */
export function MetricRow({ metrics }: MetricRowProps) {
  return (
    <div className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 2xl:grid-cols-4">
      {metrics.map((metric, index) => (
        <Reveal key={metric.label} className="min-w-0" delay={index * 0.05}>
          <StatCard
            label={metric.label}
            value={String(metric.value)}
            icon={metric.icon}
            tone={metric.tone}
            help={metric.help}
            className="h-full min-w-0"
          />
        </Reveal>
      ))}
    </div>
  );
}
