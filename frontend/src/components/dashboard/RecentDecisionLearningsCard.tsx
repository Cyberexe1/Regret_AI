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
    <Card padding="none" className="min-w-0 overflow-hidden">
      <div className="border-b border-hairline px-4 py-4 sm:px-5 md:px-6">
        <CardTitle>Recent decision learnings</CardTitle>
        <p className="mt-0.5 break-words text-small text-ink-muted">
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
        <div className="min-w-0 divide-y divide-hairline">
          {rows.map((row) => (
            <Link
              key={row.id}
              to={decisionPath(row.decisionId)}
              className="group flex min-w-0 flex-col gap-3 px-4 py-4 transition-colors duration-150 hover:bg-surface-raised sm:flex-row sm:items-start sm:justify-between sm:gap-5 sm:px-5"
            >
              <div className="min-w-0 flex-1">
                <p className="break-words text-small leading-relaxed text-ink">{row.statement}</p>
                <p className="mt-1 break-words text-micro text-ink-muted">{row.decisionTitle}</p>
              </div>
              <div className="flex min-w-0 flex-wrap items-center gap-2 sm:max-w-48 sm:shrink-0 sm:justify-end">
                <Badge tone={row.tone} size="sm" dot />
                <span className="break-words text-micro text-ink-muted sm:text-right">{row.timestamp}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </Card>
  );
}
