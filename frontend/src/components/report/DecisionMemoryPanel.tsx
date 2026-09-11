import { Brain, HelpCircle } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { cn } from '@/lib/cn';
import { toneText } from '@/lib/tone';
import type { DecisionMemorySummary, MemoryTimelineEvent } from '@/types/report';
import { MemoryTimeline } from './MemoryTimeline';

export interface DecisionMemoryPanelProps {
  summary: DecisionMemorySummary;
  timeline: MemoryTimelineEvent[];
}

/**
 * REGRET ENGINE 2.0's Decision Memory panel: what REGRET ENGINE remembers
 * about this decision, structured as "what we thought" (the original
 * analysis - assumptions, thresholds, regret scenarios; EXPECTED, not
 * observed) versus "what we learned" (real, observed learnings from an
 * actual experiment result; KNOWN, not merely expected).
 *
 * This distinction is deliberately load-bearing in the layout, not just
 * the copy: while `summary.isValidated` is false, the "what we learned"
 * section never claims an outcome exists - it shows the decision's
 * current unresolved uncertainties instead, exactly matching what the
 * backend itself leaves `null` until a real result is submitted.
 */
export function DecisionMemoryPanel({ summary, timeline }: DecisionMemoryPanelProps) {
  if (!summary.hasMemory) {
    return (
      <EmptyState
        icon={Brain}
        title="No memory yet"
        description="This decision has not been analyzed yet. Run a stress test to start building its memory."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-2">
        <Card variant="inset">
          <div className="flex items-center gap-2.5">
            <HelpCircle className="size-4 shrink-0 text-ink-muted" aria-hidden />
            <p className="eyebrow">What we thought</p>
          </div>
          <p className="mt-3 text-small text-ink-secondary">
            {summary.originalAssessment ?? 'No analysis summary recorded yet.'}
          </p>
          <dl className="mt-4 grid grid-cols-3 gap-3 border-t border-hairline pt-4">
            <div>
              <dt className="text-micro text-ink-muted">Assumptions</dt>
              <dd className="numeric text-card-title text-ink">
                {summary.criticalAssumptionCount}
              </dd>
            </div>
            <div>
              <dt className="text-micro text-ink-muted">Thresholds</dt>
              <dd className="numeric text-card-title text-ink">
                {summary.criticalThresholdCount}
              </dd>
            </div>
            <div>
              <dt className="text-micro text-ink-muted">Regret scenarios</dt>
              <dd className="numeric text-card-title text-ink">
                {summary.criticalRegretScenarioCount}
              </dd>
            </div>
          </dl>
        </Card>

        <Card
          variant="inset"
          className={cn(!summary.isValidated && 'border-dashed opacity-90')}
        >
          <div className="flex items-center gap-2.5">
            <Brain className={cn('size-4 shrink-0', toneText.accent)} aria-hidden />
            <p className="eyebrow">What we learned</p>
            <Badge tone={summary.isValidated ? 'success' : 'neutral'} size="sm" dot>
              {summary.isValidated ? 'Known' : 'Not yet tested'}
            </Badge>
          </div>
          {summary.isValidated ? (
            <>
              <p className="mt-3 text-small text-ink-secondary">{summary.outcomeSummary}</p>
              {summary.finalAssessment ? (
                <p className="mt-3 border-t border-hairline pt-3 text-small font-medium text-ink">
                  {summary.finalAssessment}
                </p>
              ) : null}
              {summary.confidencePercent !== undefined ? (
                <p className="mt-2 text-micro text-ink-muted">
                  Confidence: {summary.confidencePercent}%
                </p>
              ) : null}
            </>
          ) : (
            <p className="mt-3 text-small text-ink-secondary">
              No experiment result has been observed yet - this decision has {summary.experimentCount}{' '}
              recommended experiment{summary.experimentCount === 1 ? '' : 's'} awaiting a real-world
              test.
            </p>
          )}
        </Card>
      </div>

      {summary.unresolvedUncertainties.length > 0 ? (
        <div className="rounded-xl border border-hairline bg-surface-inset px-5 py-4">
          <p className="eyebrow">Remaining uncertainties</p>
          <ul className="mt-2 space-y-1.5">
            {summary.unresolvedUncertainties.map((item) => (
              <li key={item} className="text-small text-ink-secondary">
                • {item}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {summary.learnings.length > 0 ? (
        <div className="space-y-3">
          <p className="eyebrow">Learnings</p>
          <ul className="space-y-3">
            {summary.learnings.map((learning) => (
              <li key={learning.id} className="rounded-lg border border-hairline bg-surface px-4 py-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <p className="min-w-0 flex-1 text-small text-ink">{learning.statement}</p>
                  <Badge tone={learning.typeTone} size="sm" variant="outline" className="shrink-0">
                    {learning.typeLabel}
                  </Badge>
                </div>
                {learning.observedValue !== null || learning.expectedValue !== null ? (
                  <p className="numeric mt-2 text-micro text-ink-muted">
                    {learning.observedValue !== null ? `Observed: ${learning.observedValue}` : ''}
                    {learning.observedValue !== null && learning.expectedValue !== null ? ' · ' : ''}
                    {learning.expectedValue !== null ? `Expected: ${learning.expectedValue}` : ''}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="rounded-xl border border-hairline bg-surface p-5 md:p-6">
        <p className="eyebrow">Timeline</p>
        <div className="mt-4">
          <MemoryTimeline events={timeline} />
        </div>
      </div>
    </div>
  );
}
