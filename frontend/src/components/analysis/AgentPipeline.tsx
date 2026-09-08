import { motion, useReducedMotion } from 'framer-motion';
import { Check } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Card, CardTitle } from '@/components/ui/Card';
import { analysisAgents, type AgentStatus, type AnalysisAgent } from '@/data/analysisAgents';
import { cn } from '@/lib/cn';
import { ActivityPulse } from './ActivityPulse';

const ICON_SHELL: Record<AgentStatus, string> = {
  complete: 'border-accent-line bg-accent-soft text-accent-ink',
  running: 'border-accent bg-accent-soft text-accent-ink',
  waiting: 'border-hairline bg-surface-inset text-ink-faint',
};

const NAME_COLOR: Record<AgentStatus, string> = {
  complete: 'text-ink',
  running: 'text-ink',
  waiting: 'text-ink-muted',
};

function StatusBadge({ status }: { status: AgentStatus }) {
  if (status === 'complete') {
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
  status: AgentStatus;
  isLast: boolean;
}) {
  const reduceMotion = useReducedMotion();
  const isRunning = status === 'running';

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
              status === 'complete' ? 'bg-accent-line' : 'bg-hairline',
            )}
            aria-hidden
          />
        )}
      </div>

      <div className={cn('min-w-0', isLast ? 'pb-0' : 'pb-6')}>
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          <div className="flex min-w-0 items-baseline gap-2.5">
            <span className="numeric text-micro text-ink-faint">{agent.index}</span>
            <p className={cn('truncate text-card-title transition-colors', NAME_COLOR[status])}>
              {agent.name}
            </p>
          </div>
          <StatusBadge status={status} />
        </div>

        <p
          className={cn(
            'mt-1.5 text-small transition-colors',
            status === 'waiting' ? 'text-ink-faint' : 'text-ink-secondary',
          )}
        >
          {agent.description}
        </p>
      </div>
    </li>
  );
}

export interface AgentPipelineProps {
  statuses: Record<string, AgentStatus>;
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
            Seven specialists, each attacking a different part of the decision
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
            status={statuses[agent.id] ?? 'waiting'}
            isLast={index === analysisAgents.length - 1}
          />
        ))}
      </ol>
    </Card>
  );
}
