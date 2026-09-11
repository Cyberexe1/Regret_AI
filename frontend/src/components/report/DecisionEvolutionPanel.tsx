import { useState } from 'react';
import { History } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import type { DecisionEvolutionSummary, EvolutionEventRow } from '@/types/report';
import { DecisionEvolutionTimeline } from './DecisionEvolutionTimeline';
import { EvolutionEventDetailPanel } from './EvolutionEventDetailPanel';

export interface DecisionEvolutionPanelProps {
  summary: DecisionEvolutionSummary;
  isLoading?: boolean;
  /** Real assumption statements/experiment titles, keyed by id, already
   * loaded elsewhere on the page (see `useDecisionReportData`) - passed
   * through to the event detail panel's "Belief vs Evidence" block so it
   * never needs a new per-event API call. */
  assumptionStatementsById?: Record<string, string>;
  experimentTitlesById?: Record<string, string>;
}

/**
 * REGRET ENGINE 2.0's "DECISION EVOLUTION" section (Step 22) - the
 * complete belief -> test -> observe -> change -> learn -> next-test
 * journey for one decision, assembled from real canonical records
 * (never a second, parallel event database - see
 * `backend/app/evolution/service.py`'s own docstring).
 *
 * Structure, top to bottom (per spec sections 15-17):
 *
 *   1. Summary stats (current assessment, cycles, uncertainties
 *      resolved/remaining, experiments completed).
 *   2. The full vertical timeline - click any event to open its detail
 *      panel (`EvolutionEventDetailPanel`), which itself surfaces the
 *      "What changed?" card (`DecisionDeltaCard`) for state-changing
 *      events.
 *   3. "Major Changes" - a compact list of only the events with real,
 *      meaningful impact, never every tiny database write.
 *   4. "Current State" - a closing block connecting back to Step 21's
 *      adaptive loop (current primary uncertainty, unresolved
 *      uncertainties, truncation notice if the history is very long).
 */
export function DecisionEvolutionPanel({
  summary,
  isLoading = false,
  assumptionStatementsById,
  experimentTitlesById,
}: DecisionEvolutionPanelProps) {
  const [selectedEvent, setSelectedEvent] = useState<EvolutionEventRow | null>(null);

  if (isLoading) {
    return (
      <EmptyState
        icon={History}
        title="Reconstructing the decision's evolution…"
        description="Assembling the timeline from everything analyzed, tested, and learned so far."
      />
    );
  }

  if (!summary.found) {
    return (
      <EmptyState
        icon={History}
        title="No evolution to show yet"
        description="This decision hasn't been created yet."
      />
    );
  }

  return (
    <div className="space-y-6">
      <DecisionEvolutionSummaryStats summary={summary} />

      {summary.truncated ? (
        <p className="text-micro text-ink-muted">
          This decision's history is long - showing only the most recent events.
        </p>
      ) : null}

      <div className="rounded-xl border border-hairline bg-surface p-5 md:p-6">
        <p className="eyebrow">Timeline</p>
        <div className="mt-4">
          <DecisionEvolutionTimeline events={summary.timeline} onSelectEvent={setSelectedEvent} />
        </div>
      </div>

      <MajorChangesSection summary={summary} />

      <CurrentStateBlock summary={summary} />

      <EvolutionEventDetailPanel
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
        assumptionStatementsById={assumptionStatementsById}
        experimentTitlesById={experimentTitlesById}
      />
    </div>
  );
}

function DecisionEvolutionSummaryStats({ summary }: { summary: DecisionEvolutionSummary }) {
  const stats = [
    { label: 'Current assessment', value: summary.currentAssessmentLabel },
    { label: 'Cycles completed', value: String(summary.cyclesCompleted) },
    { label: 'Uncertainties resolved', value: String(summary.uncertaintiesResolvedCount) },
    { label: 'Uncertainties remaining', value: String(summary.uncertaintiesRemainingCount) },
    { label: 'Experiments completed', value: String(summary.experimentsCompletedCount) },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
      {stats.map((stat) => (
        <Card key={stat.label} variant="inset" className="flex flex-col justify-between gap-2">
          <p className="text-micro text-ink-muted">{stat.label}</p>
          <p className="numeric text-card-title text-ink">{stat.value}</p>
        </Card>
      ))}
    </div>
  );
}

function MajorChangesSection({ summary }: { summary: DecisionEvolutionSummary }) {
  if (summary.majorChanges.length === 0) return null;

  return (
    <div className="rounded-xl border border-hairline-strong bg-surface-raised p-5 md:p-6">
      <p className="eyebrow">Major changes</p>
      <ul className="mt-3 space-y-2.5">
        {summary.majorChanges.map((event) => (
          <li key={event.eventId} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <span className="text-small text-ink">{event.title}</span>
            <span className="numeric text-micro text-ink-muted">{event.timestampLabel}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function CurrentStateBlock({ summary }: { summary: DecisionEvolutionSummary }) {
  return (
    <div className="rounded-xl border border-hairline bg-surface-inset p-5 md:p-6">
      <p className="eyebrow">Current state</p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Badge tone={summary.currentAssessmentTone} size="sm" dot>
          {summary.currentAssessmentLabel}
        </Badge>
        {summary.currentCycle !== null ? (
          <Badge tone="neutral" size="sm">
            Cycle {summary.currentCycle}
          </Badge>
        ) : null}
      </div>

      {summary.currentUncertaintyIds.length > 0 ? (
        <p className="mt-3 text-small text-ink-secondary">
          {summary.currentUncertaintyIds.length} uncertaint
          {summary.currentUncertaintyIds.length === 1 ? 'y' : 'ies'} remain unresolved.
        </p>
      ) : (
        <p className="mt-3 text-small text-ink-secondary">
          No unresolved uncertainties remain from the analyzed assumptions.
        </p>
      )}
    </div>
  );
}
