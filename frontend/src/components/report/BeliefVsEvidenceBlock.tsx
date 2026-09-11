import { CircleQuestionMark, FlaskConical, Lightbulb, ScanEye } from 'lucide-react';
import type { EvolutionEventRow } from '@/types/report';

export interface BeliefVsEvidenceBlockProps {
  event: EvolutionEventRow;
  /** The real statement of the assumption this event tested, resolved
   * from already-loaded report data (never a new per-event API call) -
   * `undefined` when the event doesn't reference a real assumption. */
  beliefStatement: string | undefined;
  /** The real title of the experiment this event's result came from,
   * resolved the same way. */
  testTitle: string | undefined;
}

/**
 * "WHAT WE BELIEVED" vs "WHAT WE LEARNED" - a central REGRET ENGINE
 * concept (spec section 14). Renders nothing (`null`) unless there is a
 * real belief statement AND a real observed/learned outcome to show -
 * never fills in a placeholder belief that wasn't actually recorded.
 */
export function BeliefVsEvidenceBlock({ event, beliefStatement, testTitle }: BeliefVsEvidenceBlockProps) {
  if (!beliefStatement) return null;

  const observed = event.summary;
  const learned = event.reason ?? event.summary;

  return (
    <div className="space-y-3 rounded-xl border border-hairline bg-surface-inset p-5 md:p-6">
      <Row icon={Lightbulb} label="What we believed" text={beliefStatement} />
      {testTitle ? <Row icon={FlaskConical} label="Test" text={testTitle} /> : null}
      <Row icon={ScanEye} label="What we observed" text={observed} />
      <Row icon={CircleQuestionMark} label="What we learned" text={learned} emphasize />
    </div>
  );
}

function Row({
  icon: Icon,
  label,
  text,
  emphasize = false,
}: {
  icon: typeof Lightbulb;
  label: string;
  text: string;
  emphasize?: boolean;
}) {
  return (
    <div className="flex items-start gap-3">
      <Icon className="mt-0.5 size-4 shrink-0 text-ink-muted" aria-hidden />
      <div className="min-w-0">
        <p className="text-micro text-ink-muted">{label}</p>
        <p className={emphasize ? 'mt-0.5 text-small font-medium text-ink' : 'mt-0.5 text-small text-ink-secondary'}>
          {text}
        </p>
      </div>
    </div>
  );
}
