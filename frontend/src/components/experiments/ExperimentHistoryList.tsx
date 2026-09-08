import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/Badge';
import { Card, CardTitle } from '@/components/ui/Card';
import { decisionPath } from '@/data/navigation';
import { formatRelative } from '@/lib/format';
import { experimentPhase, experimentStatusLabel } from '@/lib/labels';
import { experimentStatusTone } from '@/lib/tone';
import type { Decision, Experiment, ExperimentPhase } from '@/types';

const PHASE_TONE: Record<ExperimentPhase, 'info' | 'neutral' | 'success'> = {
  Running: 'info',
  Proposed: 'neutral',
  Completed: 'success',
};

export interface ExperimentHistoryListProps {
  experiments: Experiment[];
  /** Decision lookup so each row can name what it was testing. */
  decisionsById: Map<string, Decision>;
}

export function ExperimentHistoryList({
  experiments,
  decisionsById,
}: ExperimentHistoryListProps) {
  return (
    <Card padding="none" className="overflow-hidden">
      <div className="flex items-center justify-between gap-4 border-b border-hairline px-5 py-4">
        <div>
          <CardTitle>Experiment history</CardTitle>
          <p className="mt-0.5 text-small text-ink-muted">
            Every experiment in this workspace, newest first
          </p>
        </div>
        <span className="numeric text-small text-ink-muted">{experiments.length}</span>
      </div>

      <ul className="divide-y divide-hairline">
        {experiments.map((experiment) => {
          const decision = decisionsById.get(experiment.decisionId);
          const phase = experimentPhase(experiment.status);

          return (
            <li key={experiment.id}>
              <Link
                to={decision ? decisionPath(decision.id) : '#'}
                className="group flex flex-col gap-3 px-5 py-4 transition-colors duration-150 hover:bg-surface-raised sm:flex-row sm:items-center sm:gap-4"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-card-title text-ink">{experiment.title}</p>
                  <p className="mt-0.5 truncate text-small text-ink-muted">
                    {decision ? decision.title : 'Unlinked'}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={PHASE_TONE[phase]} size="sm" dot>
                    {phase}
                  </Badge>
                  {phase === 'Completed' ? (
                    <Badge
                      tone={experimentStatusTone[experiment.status]}
                      size="sm"
                      variant="outline"
                    >
                      {experimentStatusLabel[experiment.status]}
                    </Badge>
                  ) : null}
                </div>

                <div className="flex shrink-0 items-center justify-between gap-2 sm:w-28 sm:justify-end">
                  <span className="text-small text-ink-muted">
                    {formatRelative(experiment.createdAt)}
                  </span>
                  <ChevronRight
                    className="size-4 shrink-0 text-ink-faint transition-colors group-hover:text-ink-secondary"
                    aria-hidden
                  />
                </div>
              </Link>

              {experiment.finding ? (
                <p className="px-5 pb-4 text-small text-ink-secondary sm:pr-36">
                  <span className="text-ink-muted">Finding · </span>
                  {experiment.finding}
                </p>
              ) : null}
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
