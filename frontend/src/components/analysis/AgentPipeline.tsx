import { motion, useReducedMotion } from 'framer-motion';
import { Check, Minus, X } from 'lucide-react';
import type { AgentRunStatus } from '@/api/types';
import { Badge } from '@/components/ui/Badge';
import { Card, CardTitle } from '@/components/ui/Card';
import { analysisAgents, type AnalysisAgent } from '@/data/analysisAgents';
import { cn } from '@/lib/cn';
import { ActivityPulse } from './ActivityPulse';

const ICON_SHELL: Record<AgentRunStatus, string> = {
  completed: 'border-accent-line bg-accent-soft text-accent-ink',
  running: 'border-accent bg-accent-soft text-accent-ink',
  pending: 'border-hairline bg-surface-inset text-ink-muted',
  failed: 'border-danger-line bg-danger-soft text-danger-ink',
  skipped: 'border-hairline bg-surface-inset text-ink-muted',
  unavailable: 'border-hairline bg-surface-inset text-ink-muted',
};

const NAME_COLOR: Record<AgentRunStatus, string> = {
  completed: 'text-ink',
  running: 'text-ink',
  pending: 'text-ink-muted',
  failed: 'text-danger-ink',
  skipped: 'text-ink-muted',
  unavailable: 'text-ink-muted',
};

function StatusBadge({ status }: { status: AgentRunStatus }) {
  if (status === 'completed') {
    return (
      <Badge tone="success" size="sm" icon={Check}>
        Complete
      </Badge>
    );
  }

  if (status === 'running') {
    return (
      <Badge tone="accent" size="sm">
        <ActivityPulse className="mr-0.5" />
        Running
      </Badge>
    );
  }

  if (status === 'failed') {
    return (
      <Badge tone="danger" size="sm" icon={X}>
        Failed
      </Badge>
    );
  }

  if (status === 'skipped' || status === 'unavailable') {
    return (
      <Badge tone="neutral" size="sm" variant="outline" icon={Minus}>
        {status === 'skipped' ? 'Skipped' : 'Unavailable'}
      </Badge>
    );
  }

  return (
    <Badge tone="neutral" size="sm" variant="outline">
      Waiting
    </Badge>
  );
}

function AgentRow({
  agent,
  status,
  isLast,
}: {
  agent: AnalysisAgent;
  status: AgentRunStatus;
  isLast: boolean;
}) {
  const reduceMotion = useReducedMotion();
  const isRunning = status === 'running';
  const lineComplete = status === 'completed' || status === 'skipped' || status === 'unavailable';

  return (
    <li className="grid grid-cols-[2.25rem_minmax(0,1fr)] gap-x-4">
      <div className="flex flex-col items-center">
        <span className="relative flex size-9 shrink-0 items-center justify-center">
          {isRunning && !reduceMotion ? (
            <motion.span
              className="absolute inset-0 rounded-lg border border-accent"
              animate={{ opacity: [0.55, 0, 0.55], scale: [1, 1.3, 1] }}
              transition={{ duration: 1.9, repeat: Infinity, ease: 'easeInOut' }}
            />
          ) : null}
          <span
            className={cn(
              'relative flex size-9 items-center justify-center rounded-lg border transition-colors duration-300',
              ICON_SHELL[status],
            )}
          >
            <agent.icon className="size-4" aria-hidden />
          </span>
        </span>

        {isLast ? null : (
          <span
            className={cn(
              'mt-1.5 w-px flex-1 transition-colors duration-500',
              lineComplete ? 'bg-accent-line' : 'bg-hairline',
            )}
            aria-hidden
          />
        )}
      </div>

      <div className={cn('min-w-0', isLast ? 'pb-0' : 'pb-6')}>
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          <div className="flex min-w-0 items-baseline gap-2.5">
            <span className="numeric text-micro text-ink-muted">{agent.index}</span>
            <p className={cn('truncate text-card-title transition-colors', NAME_COLOR[status])}>
              {agent.name}
            </p>
          </div>
          <StatusBadge status={status} />
        </div>

        <p
          className={cn(
            'mt-1.5 text-small transition-colors',
            status === 'pending' ? 'text-ink-muted' : 'text-ink-secondary',
          )}
        >
          {agent.description}
        </p>
      </div>
    </li>
  );
}

export interface AgentPipelineProps {
  statuses: Partial<Record<string, AgentRunStatus>>;
  activeAgentId: string | null;
}

export function AgentPipeline({ statuses, activeAgentId }: AgentPipelineProps) {
  const active = analysisAgents.find((agent) => agent.id === activeAgentId);

  return (
    <Card padding="none" className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-hairline px-5 py-4 md:px-6">
        <div>
          <CardTitle>Investigation pipeline</CardTitle>
          <p className="mt-0.5 text-small text-ink-muted">
            Nine specialists, each attacking a different part of the decision
          </p>
        </div>
        {active ? (
          <span className="flex items-center gap-2 text-small text-accent-ink">
            <ActivityPulse />
            {active.name}
          </span>
        ) : null}
      </div>

      <ol className="px-5 py-6 md:px-6">
        {analysisAgents.map((agent, index) => (
          <AgentRow
            key={agent.id}
            agent={agent}
            status={statuses[agent.id] ?? 'pending'}
            isLast={index === analysisAgents.length - 1}
          />
        ))}
      </ol>
    </Card>
  );
}
