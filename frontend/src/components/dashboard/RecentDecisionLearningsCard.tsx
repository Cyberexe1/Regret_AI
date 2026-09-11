import { Brain } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/Badge';
import { Card, CardTitle } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { decisionPath } from '@/data/navigation';
import type { RecentLearningRow } from '@/lib/buildDashboard';

export interface RecentDecisionLearningsCardProps {
  rows: RecentLearningRow[];
}

/**
 * REGRET ENGINE 2.0: a few of the workspace's most recent, real Decision
 * Memory learnings (e.g. "Retention assumption failed validation.",
 * "Pricing threshold was validated."). Clicking a row navigates to the
 * decision it came from. Mirrors `RecentDecisionsCard`'s exact layout.
 */
export function RecentDecisionLearningsCard({ rows }: RecentDecisionLearningsCardProps) {
  return (
    <Card padding="none" className="overflow-hidden">
      <div className="border-b border-hairline px-5 py-4 md:px-6">
        <CardTitle>Recent decision learnings</CardTitle>
        <p className="mt-0.5 text-small text-ink-muted">
          What REGRET ENGINE has learned from real experiment results
        </p>
      </div>

      {rows.length === 0 ? (
        <EmptyState
          size="inline"
          icon={Brain}
          title="No learnings yet"
          description="Submit a real experiment result to start building decision memory."
        />
      ) : (
        <div className="divide-y divide-hairline">
          {rows.map((row) => (
            <Link
              key={row.id}
              to={decisionPath(row.decisionId)}
              className="group flex flex-col gap-2 px-5 py-4 transition-colors duration-150 hover:bg-surface-raised sm:flex-row sm:items-center sm:justify-between sm:gap-4"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-small text-ink">{row.statement}</p>
                <p className="mt-0.5 truncate text-micro text-ink-muted">{row.decisionTitle}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Badge tone={row.tone} size="sm" dot />
                <span className="text-micro text-ink-muted">{row.timestamp}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </Card>
  );
}
