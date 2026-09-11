import {
  ArrowRight,
  Beaker,
  Brain,
  CheckCircle2,
  CircleDashed,
  Compass,
  FlaskConical,
  Gauge,
  History,
  Lightbulb,
  ScanSearch,
  SquarePen,
  TriangleAlert,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { cn } from '@/lib/cn';
import { toneSurface } from '@/lib/tone';
import type { EvolutionEventRow } from '@/types/report';
import type { EvolutionEventType } from '@/api/types';

export interface DecisionEvolutionTimelineProps {
  events: EvolutionEventRow[];
  onSelectEvent: (event: EvolutionEventRow) => void;
}

const ICON_BY_TYPE: Record<EvolutionEventType, LucideIcon> = {
  decision_created: SquarePen,
  analysis_completed: ScanSearch,
  assumption_identified: Lightbulb,
  blindspot_identified: TriangleAlert,
  regret_scenario_identified: TriangleAlert,
  threshold_identified: Gauge,
  experiment_recommended: FlaskConical,
  experiment_started: Beaker,
  experiment_completed: CheckCircle2,
  experiment_result: Beaker,
  threshold_validated: CheckCircle2,
  threshold_failed: TriangleAlert,
  re_evaluation: History,
  assessment_changed: ArrowRight,
  learning_recorded: Brain,
  next_experiment_selected: Compass,
  validation_state_changed: ArrowRight,
  decision_completed: CheckCircle2,
  historical_insight_surfaced: History,
};

/** Impact drives border weight/color, never a fabricated severity score -
 * a `major` event (e.g. an assessment change) is visually heavier so the
 * causal chain "belief -> test -> result -> change" stands out from
 * routine bookkeeping events, matching the spec's explicit "do not make
 * it look like a normal activity feed" requirement. */
const IMPACT_TONE = {
  minor: 'neutral',
  moderate: 'info',
  major: 'accent',
} as const;

/**
 * REGRET ENGINE 2.0's Decision Evolution timeline (Step 22): the
 * BELIEF -> EVIDENCE -> TEST -> RESULT -> CHANGE narrative, never a
 * generic activity log. Deliberately visually distinct from
 * `MemoryTimeline`/`AdaptiveDecisionTimeline` (larger bullets, an
 * explicit "->" connector on state-changing events, and a HISTORICAL
 * badge on any surfaced historical insight - spec section 20) - every
 * event is clickable to open its full detail panel.
 */
export function DecisionEvolutionTimeline({ events, onSelectEvent }: DecisionEvolutionTimelineProps) {
  if (events.length === 0) {
    return (
      <EmptyState
        icon={History}
        title="Nothing to show yet"
        description="This decision's evolution will appear here once it has been analyzed."
      />
    );
  }

  const lastIndex = events.length - 1;

  return (
    <ol>
      {events.map((event, index) => {
        const Icon = ICON_BY_TYPE[event.eventType] ?? ICON_BY_TYPE.decision_created;
        const isLast = index === lastIndex;
        const tone = event.isHistorical ? 'neutral' : IMPACT_TONE[event.impact];

        return (
          <li key={event.eventId} className="grid grid-cols-[2rem_minmax(0,1fr)] gap-x-4">
            <div className="flex flex-col items-center">
              <span
                className={cn(
                  'inline-flex size-8 shrink-0 items-center justify-center rounded-full border-2',
                  toneSurface[tone],
                  event.impact === 'major' && 'border-accent',
                )}
              >
                <Icon className="size-4" aria-hidden />
              </span>
              {isLast ? null : <span className="mt-1.5 w-px flex-1 bg-hairline" aria-hidden />}
            </div>

            <button
              type="button"
              onClick={() => onSelectEvent(event)}
              className={cn(
                'min-w-0 rounded-lg text-left transition-colors duration-150 hover:bg-surface-raised',
                isLast ? 'pb-0' : 'pb-7',
                'px-2 py-1.5 -mx-2',
              )}
            >
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <p className="eyebrow">{event.typeLabel}</p>
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
              </div>

              <p className="mt-1 text-card-title text-ink">{event.title}</p>
              <p className="mt-1 text-small text-ink-secondary">{event.summary}</p>

              {event.previousStateLabel !== null && event.newStateLabel !== null ? (
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span className="text-small text-ink-muted line-through">
                    {event.previousStateLabel}
                  </span>
                  <ArrowRight className="size-3.5 shrink-0 text-ink-muted" aria-hidden />
                  <span className="text-small font-semibold text-ink">{event.newStateLabel}</span>
                </div>
              ) : null}

              <span className="numeric mt-1.5 block text-micro text-ink-muted">
                {event.timestampLabel}
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}

/** Unused fallback icon export kept for parity with other timeline
 * components' `iconFor`-style helpers, in case a future caller needs the
 * bare mapping without the component. */
export function iconForEvolutionEvent(type: EvolutionEventType): LucideIcon {
  return ICON_BY_TYPE[type] ?? CircleDashed;
}
