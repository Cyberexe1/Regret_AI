import { Gauge } from 'lucide-react';
import { EmptyState } from '@/components/ui/EmptyState';
import type { ReportThreshold } from '@/types/report';
import { ThresholdCard } from './ThresholdCard';

export interface ThresholdSectionProps {
  thresholds: ReportThreshold[];
}

/**
 * Renders every real threshold the Threshold Engine produced. There is no
 * fabricated curve/chart here anymore - the backend does not compute a
 * contribution-vs-rate curve, and REGRET ENGINE never invents one. Each
 * threshold is shown honestly: a real numeric gauge when the backend
 * supplied real bounds, a qualitative card otherwise.
 */
export function ThresholdSection({ thresholds }: ThresholdSectionProps) {
  if (thresholds.length === 0) {
    return (
      <EmptyState
        icon={Gauge}
        title="No thresholds identified yet"
        description="The Threshold Engine has not produced any tipping points for this decision, or the analysis has not reached this stage yet."
      />
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {thresholds.map((threshold) => (
        <ThresholdCard key={threshold.id} threshold={threshold} />
      ))}
    </div>
  );
}
