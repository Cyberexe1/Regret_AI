import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { SkeletonText } from '@/components/ui/Skeleton';
import type { EvolutionEventRow } from '@/types/report';
import { BeliefVsEvidenceBlock } from './BeliefVsEvidenceBlock';
import { DecisionDeltaCard } from './DecisionDeltaCard';

export interface EvolutionEventDetailPanelProps {
  event: EvolutionEventRow | null;
  onClose: () => void;
  isLoadingDelta?: boolean;
  /** Real assumption statements/experiment titles, keyed by id, already
   * loaded elsewhere on the page - resolved here only for display, never
   * fetched with a new per-event API call. */
  assumptionStatementsById?: Record<string, string>;
  experimentTitlesById?: Record<string, string>;
}

/**
 * Detail panel opened when a user clicks an event on the Decision
 * Evolution timeline (spec section 12). Shows only structured, real
 * fields from the source `DecisionEvolutionEvent` - never internal
 * chain-of-thought, never a fabricated explanation beyond what the
 * event itself carries.
 */
export function EvolutionEventDetailPanel({
  event,
  onClose,
  isLoadingDelta = false,
  assumptionStatementsById = {},
  experimentTitlesById = {},
}: EvolutionEventDetailPanelProps) {
  return (
    <Modal open={event !== null} onClose={onClose} title={event?.title ?? ''} size="lg">
      {event ? (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="neutral" size="sm">
              {event.typeLabel}
            </Badge>
            {event.isHistorical ? (
              <Badge tone="neutral" size="sm" variant="outline">
                HISTORICAL
              </Badge>
            ) : null}
            {event.cycleNumber !== null ? (
              <Badge tone="neutral" size="sm">
                Cycle {event.cycleNumber}
              </Badge>
            ) : null}
            <span className="numeric text-micro text-ink-muted">{event.timestampLabel}</span>
          </div>

          <div>
            <p className="eyebrow">What happened</p>
            <p className="mt-2 text-body text-ink">{event.summary}</p>
          </div>

          {isLoadingDelta ? (
            <SkeletonText lines={3} />
          ) : (
            <DecisionDeltaCard event={event} />
          )}

          <BeliefVsEvidenceBlock
            event={event}
            beliefStatement={
              event.affectedAssumptionIds.length > 0
                ? assumptionStatementsById[event.affectedAssumptionIds[0]!]
                : undefined
            }
            testTitle={
              event.affectedExperimentIds.length > 0
                ? experimentTitlesById[event.affectedExperimentIds[0]!]
                : undefined
            }
          />

          {event.reason ? (
            <div className="rounded-lg border border-hairline bg-surface-inset px-4 py-3">
              <p className="eyebrow">Why this matters</p>
              <p className="mt-2 text-small text-ink-secondary">{event.reason}</p>
            </div>
          ) : null}

          <div className="grid grid-cols-2 gap-3 border-t border-hairline pt-4 sm:grid-cols-4">
            <div>
              <p className="text-micro text-ink-muted">Source</p>
              <p className="mt-1 text-small text-ink">{event.sourceTypeLabel}</p>
            </div>
            {event.affectedAssumptionIds.length > 0 ? (
              <div>
                <p className="text-micro text-ink-muted">Assumptions</p>
                <p className="numeric mt-1 text-small text-ink">
                  {event.affectedAssumptionIds.length}
                </p>
              </div>
            ) : null}
            {event.affectedThresholdIds.length > 0 ? (
              <div>
                <p className="text-micro text-ink-muted">Thresholds</p>
                <p className="numeric mt-1 text-small text-ink">
                  {event.affectedThresholdIds.length}
                </p>
              </div>
            ) : null}
            {event.evidenceIds.length > 0 ? (
              <div>
                <p className="text-micro text-ink-muted">Evidence</p>
                <p className="numeric mt-1 text-small text-ink">{event.evidenceIds.length}</p>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </Modal>
  );
}
