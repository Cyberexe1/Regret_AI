import { History, TriangleAlert } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { decisionPath } from '@/data/navigation';
import type { HistoricalContextSummary } from '@/types/report';

export interface HistoricalInsightsPanelProps {
  summary: HistoricalContextSummary;
  isLoading?: boolean;
  /** Compact mode drops the "Why REGRET connected these decisions"
   * explanation footer and the recurring-variables strip, for use in
   * tighter spaces (e.g. NewDecisionPage's intake preview). */
  compact?: boolean;
}

/**
 * REGRET ENGINE 2.0's shared Historical Insights surface - used on
 * NewDecisionPage (as a live preview), AnalysisPage ("Historical
 * Insights" section), and DecisionDetailPage ("Related Past Decisions").
 *
 * Deliberately conservative in its language: `relevancePercent` is
 * always labelled "similarity", never "probability" or "confidence in
 * outcome" - see `buildHistoricalContext.ts` and the backend's own
 * `similarity_schemas.py` module docstring for why that distinction is
 * load-bearing. Every insight is phrased as something a PREVIOUS
 * decision observed, never as a fact about the decision being viewed
 * now - this component never rewrites that framing, it only displays it.
 */
export function HistoricalInsightsPanel({
  summary,
  isLoading = false,
  compact = false,
}: HistoricalInsightsPanelProps) {
  if (isLoading) {
    return (
      <EmptyState
        size={compact ? 'inline' : 'panel'}
        icon={History}
        title="Checking your past decisions…"
        description="Looking for relevant context from decisions you've already analyzed."
      />
    );
  }

  if (!summary.found) {
    return (
      <EmptyState
        size={compact ? 'inline' : 'panel'}
        icon={History}
        title="No relevant past decisions yet"
        description="Once you've analyzed a few decisions, REGRET ENGINE will surface relevant learnings here automatically."
      />
    );
  }

  return (
    <div className="space-y-5">
      {summary.warnings.length > 0 ? (
        <div className="flex items-start gap-2.5 rounded-lg border border-hairline bg-surface-inset px-4 py-3">
          <TriangleAlert className="mt-0.5 size-4 shrink-0 text-ink-muted" aria-hidden />
          <p className="text-small text-ink-secondary">{summary.warnings.join(' ')}</p>
        </div>
      ) : null}

      <div className="space-y-3">
        {summary.relevantDecisions.map((decision) => (
          <Card key={decision.decisionId} variant="inset" padding="md">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <Link
                to={decisionPath(decision.decisionId)}
                className="min-w-0 flex-1 text-small font-medium text-ink underline-offset-4 hover:underline"
              >
                {decision.title}
              </Link>
              <Badge tone="accent" size="sm" variant="outline">
                {decision.relevancePercent}% similar
              </Badge>
            </div>
            <p className="mt-2 text-small text-ink-secondary">{decision.explanation}</p>
          </Card>
        ))}
      </div>

      {summary.insights.length > 0 ? (
        <div className="space-y-3">
          <p className="eyebrow">What was learned from those decisions</p>
          <ul className="space-y-3">
            {summary.insights.map((insight) => (
              <li key={insight.id} className="rounded-lg border border-hairline bg-surface px-4 py-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <p className="min-w-0 flex-1 text-small text-ink">
                    <span className="text-ink-muted">Previous decision: </span>
                    {insight.statement}
                  </p>
                  <Badge tone={insight.typeTone} size="sm" variant="outline" className="shrink-0">
                    {insight.typeLabel}
                  </Badge>
                </div>
                <p className="numeric mt-2 text-micro text-ink-muted">
                  Historical relevance: {insight.relevancePercent}% (similarity, not a probability)
                  {insight.observedValue !== null ? ` · Observed: ${insight.observedValue}` : ''}
                  {insight.expectedValue !== null ? ` · Expected: ${insight.expectedValue}` : ''}
                </p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {!compact && summary.recurringVariables.length > 0 ? (
        <div className="rounded-xl border border-hairline bg-surface-inset px-5 py-4">
          <p className="eyebrow">Recurring variables across your decisions</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {summary.recurringVariables.map((variable) => (
              <Badge key={variable} tone="neutral" size="sm">
                {variable}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}

      {!compact ? (
        <p className="text-micro text-ink-muted">
          Why REGRET connected these decisions: each match above is a deterministic comparison of
          decision text, key variables, assumptions, and constraints from your own past decisions
          only - never another user's data, and never an automatic override of this decision's own
          evidence or thresholds.
        </p>
      ) : null}
    </div>
  );
}
