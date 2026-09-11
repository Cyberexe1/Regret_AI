import { ArrowRight, CheckCircle2, CircleDashed, FlaskConical, OctagonPause, TriangleAlert } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { cn } from '@/lib/cn';
import { toneText } from '@/lib/tone';
import type { AdaptiveLoopSummary } from '@/types/report';

export interface AdaptiveLoopPanelProps {
  summary: AdaptiveLoopSummary;
  isLoading?: boolean;
  isAdvancing?: boolean;
  isStopping?: boolean;
  onAdvance?: () => void;
  onStop?: () => void;
  errorMessage?: string | null;
}

/**
 * REGRET ENGINE 2.0's Adaptive Experiment Loop (Step 21): the closed
 * loop that decides what to test next after learning from the last
 * result, rather than stopping at a single round of analysis -
 *
 *     Decision -> Uncertainties -> Value of Information -> Best
 *     Experiment -> Real-World Result -> Re-evaluation -> Updated
 *     Uncertainties -> (repeat, or stop)
 *
 * Renders three things, always built from a real, already-persisted
 * `AdaptiveExperimentState` - never a fabricated recommendation:
 *
 *   1. "Decision Validation" - the current cycle, the decision's
 *      current evidence-supported assessment (and, when it changed this
 *      cycle, the previous -> current transition), and what changed
 *      about any threshold this cycle.
 *   2. "The Next Question" - the next uncertainty/experiment to run and
 *      why, or a clear stopping banner if the loop has concluded.
 *   3. Manual controls: advance to the next cycle, or stop the loop
 *      entirely - the human always remains in control (REGRET ENGINE
 *      never auto-runs an experiment on the user's behalf).
 */
export function AdaptiveLoopPanel({
  summary,
  isLoading = false,
  isAdvancing = false,
  isStopping = false,
  onAdvance,
  onStop,
  errorMessage,
}: AdaptiveLoopPanelProps) {
  if (isLoading) {
    return (
      <EmptyState
        icon={FlaskConical}
        title="Loading the validation loop…"
        description="Checking where this decision's testing cycle currently stands."
      />
    );
  }

  if (!summary.found) {
    return (
      <EmptyState
        icon={FlaskConical}
        title="Not started yet"
        description="Once an experiment has been recommended for this decision, start the adaptive loop to have REGRET ENGINE track what to test next after each result."
        action={
          onAdvance ? (
            <Button variant="primary" size="sm" loading={isAdvancing} onClick={onAdvance}>
              Start validation loop
            </Button>
          ) : undefined
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-2">
        <Card variant="inset">
          <div className="flex items-center justify-between gap-3">
            <p className="eyebrow">Decision validation</p>
            <Badge tone="neutral" size="sm">
              Cycle {summary.cycleNumber}
            </Badge>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Badge tone={summary.statusTone} size="sm" dot>
              {summary.statusLabel}
            </Badge>
          </div>

          <div className="mt-4 border-t border-hairline pt-4">
            {summary.assessmentChanged && summary.previousAssessmentLabel ? (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-small text-ink-muted line-through">
                  {summary.previousAssessmentLabel}
                </span>
                <ArrowRight className="size-3.5 shrink-0 text-ink-muted" aria-hidden />
                <span className={cn('text-card-title font-semibold', toneText[summary.currentAssessmentTone])}>
                  {summary.currentAssessmentLabel}
                </span>
              </div>
            ) : (
              <p className={cn('text-card-title font-semibold', toneText[summary.currentAssessmentTone])}>
                {summary.currentAssessmentLabel}
              </p>
            )}
            <p className="mt-1 text-micro text-ink-muted">Current evidence-supported assessment</p>
          </div>

          {summary.thresholdChanges.length > 0 ? (
            <div className="mt-4 space-y-2 border-t border-hairline pt-4">
              <p className="text-micro text-ink-muted">What changed this cycle</p>
              {summary.thresholdChanges.map((change) => (
                <div key={change.thresholdId} className="flex items-center gap-2 text-small">
                  <span className="text-ink-muted line-through">{change.previousStatusLabel}</span>
                  <ArrowRight className="size-3 shrink-0 text-ink-muted" aria-hidden />
                  <Badge tone={change.currentStatusTone} size="sm">
                    {change.currentStatusLabel}
                  </Badge>
                </div>
              ))}
            </div>
          ) : null}
        </Card>

        <Card
          variant={summary.isConcluded ? 'inset' : 'raised'}
          className={cn(!summary.isConcluded && 'border-accent-line')}
        >
          <div className="flex items-center gap-2.5">
            {summary.isConcluded ? (
              <StoppingIcon summary={summary} />
            ) : (
              <FlaskConical className="size-4 shrink-0 text-accent-ink" aria-hidden />
            )}
            <p className="eyebrow">{summary.isConcluded ? 'Validation loop status' : 'The next question'}</p>
          </div>

          {summary.isConcluded ? (
            <>
              <p className="mt-3 text-card-title text-ink">{summary.statusLabel}</p>
              {summary.stoppingReason ? (
                <p className="mt-2 text-small text-ink-secondary">{summary.stoppingReason}</p>
              ) : null}
            </>
          ) : (
            <>
              <p className="mt-3 text-small text-ink-secondary">{summary.nextAction}</p>
              {summary.whyThisIsNext ? (
                <p className="mt-3 border-t border-hairline pt-3 text-micro text-ink-muted">
                  {summary.whyThisIsNext}
                </p>
              ) : null}
            </>
          )}
        </Card>
      </div>

      {errorMessage ? (
        <div className="flex items-start gap-2.5 rounded-xl border border-danger-line bg-panel-danger px-4 py-3 text-small text-danger-ink">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>{errorMessage}</span>
        </div>
      ) : null}

      {!summary.isConcluded ? (
        <div className="flex flex-wrap gap-3">
          {onAdvance ? (
            <Button variant="primary" size="sm" loading={isAdvancing} onClick={onAdvance}>
              Advance the validation loop
            </Button>
          ) : null}
          {onStop ? (
            <Button variant="secondary" size="sm" loading={isStopping} onClick={onStop}>
              Stop testing
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function StoppingIcon({ summary }: { summary: AdaptiveLoopSummary }) {
  if (summary.isUserStopped) return <OctagonPause className="size-4 shrink-0 text-ink-muted" aria-hidden />;
  if (summary.isBlocked) return <TriangleAlert className="size-4 shrink-0 text-warning-ink" aria-hidden />;
  if (summary.statusTone === 'success') {
    return <CheckCircle2 className="size-4 shrink-0 text-success-ink" aria-hidden />;
  }
  return <CircleDashed className="size-4 shrink-0 text-ink-muted" aria-hidden />;
}
