import { AlertTriangle } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { cn } from '@/lib/cn';
import { toneSurface, toneText } from '@/lib/tone';
import type { ReportScenario } from '@/types/report';

export interface ScenarioCardsProps {
  scenarios: ReportScenario[];
}

export function ScenarioCards({ scenarios }: ScenarioCardsProps) {
  if (scenarios.length === 0) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="No regret scenarios yet"
        description="The Regret Simulator has not produced any scenarios for this decision, or the analysis has not reached this stage yet."
      />
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {scenarios.map((scenario) => (
        <article
          key={scenario.id}
          className="flex h-full flex-col rounded-xl border border-hairline bg-surface p-5 transition-colors duration-200 hover:border-hairline-strong"
        >
          <div className="flex items-center justify-between gap-3">
            <span
              className={cn(
                'inline-flex size-8 items-center justify-center rounded-md border',
                toneSurface[scenario.regretLevelTone],
              )}
            >
              <AlertTriangle className="size-4" aria-hidden />
            </span>
            {scenario.probabilityBand ? (
              <Badge tone="neutral" size="sm" variant="outline">
                {scenario.probabilityBand} probability
              </Badge>
            ) : null}
          </div>

          <h4 className={cn('mt-4 text-card-title', toneText[scenario.regretLevelTone])}>{scenario.title}</h4>
          <p className="mt-2 text-small text-ink-secondary">{scenario.failureCondition}</p>

          <dl className="mt-5 space-y-3 border-t border-hairline pt-4">
            {scenario.impact ? (
              <div className="flex items-baseline justify-between gap-3">
                <dt className="text-small text-ink-muted">Impact</dt>
                <dd className={cn('text-small font-medium', toneText[scenario.impactTone])}>{scenario.impact}</dd>
              </div>
            ) : null}
            {scenario.regretLevel ? (
              <div className="flex items-baseline justify-between gap-3">
                <dt className="text-small text-ink-muted">Regret level</dt>
                <dd className={cn('text-small font-medium', toneText[scenario.regretLevelTone])}>
                  {scenario.regretLevel}
                </dd>
              </div>
            ) : null}
            {scenario.triggerVariable ? (
              <div>
                <dt className="text-small text-ink-muted">Trigger</dt>
                <dd className="mt-1.5 text-small text-ink-secondary">
                  {scenario.triggerVariable}
                  {scenario.triggerDirection ? ` (${scenario.triggerDirection})` : ''}
                </dd>
              </div>
            ) : null}
            {scenario.consequence ? (
              <div>
                <dt className="text-small text-ink-muted">Consequence</dt>
                <dd className="mt-1.5 text-small text-ink-secondary">{scenario.consequence}</dd>
              </div>
            ) : null}
          </dl>
        </article>
      ))}
    </div>
  );
}
