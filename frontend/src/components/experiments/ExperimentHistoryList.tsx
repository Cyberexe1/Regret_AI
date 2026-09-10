import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { WorkspaceExperimentRow } from '@/hooks/useWorkspaceExperiments';
import { Badge } from '@/components/ui/Badge';
import { Card, CardTitle } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { FlaskConical } from 'lucide-react';
import { experimentDetailPath } from '@/data/navigation';
import { formatRelative } from '@/lib/format';
import { experimentStatusLabel } from '@/lib/labels';
import { experimentStatusTone } from '@/lib/reportModel';

export interface ExperimentHistoryListProps {
  rows: WorkspaceExperimentRow[];
}

export function ExperimentHistoryList({ rows }: ExperimentHistoryListProps) {
  return (
    <Card padding="none" className="overflow-hidden">
      <div className="flex items-center justify-between gap-4 border-b border-hairline px-5 py-4 md:px-6">
        <div>
          <CardTitle>All experiments</CardTitle>
          <p className="mt-0.5 text-small text-ink-muted">Every experiment across your decisions, newest first</p>
        </div>
        <span className="numeric text-small text-ink-muted">{rows.length}</span>
      </div>

      {rows.length === 0 ? (
        <EmptyState
          size="inline"
          icon={FlaskConical}
          title="No experiments yet"
          description="Run a stress test on a decision and the engine will propose experiments here."
        />
      ) : (
        <ul className="divide-y divide-hairline">
          {rows.map(({ experiment, decision }) => (
            <li key={experiment.id}>
              <Link
                to={experimentDetailPath(experiment.id)}
                className="group flex flex-col gap-3 px-5 py-4 transition-colors duration-150 hover:bg-surface-raised sm:flex-row sm:items-center sm:gap-4"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-card-title text-ink">{experiment.title}</p>
                  <p className="mt-0.5 truncate text-small text-ink-muted">{decision ? decision.title : 'Unlinked'}</p>
                </div>

                <Badge tone={experimentStatusTone(experiment.status)} size="sm" dot>
                  {experimentStatusLabel[experiment.status]}
                </Badge>

                <div className="flex shrink-0 items-center justify-between gap-2 sm:w-28 sm:justify-end">
                  <span className="text-small text-ink-muted">{formatRelative(experiment.created_at)}</span>
                  <ChevronRight
                    className="size-4 shrink-0 text-ink-muted transition-colors group-hover:text-ink-secondary"
                    aria-hidden
                  />
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
