import { StatCard } from '@/components/cards/StatCard';
import { Reveal } from '@/components/Reveal';
import { dashboardMetrics } from '@/data/dashboard';

/** Four compact figures: context for the page, not the headline. */
export function MetricRow() {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {dashboardMetrics.map((metric, index) => (
        <Reveal key={metric.label} delay={index * 0.05}>
          <StatCard
            label={metric.label}
            value={String(metric.value)}
            icon={metric.icon}
            tone={metric.tone}
            help={metric.help}
            className="h-full"
          />
        </Reveal>
      ))}
    </div>
  );
}
