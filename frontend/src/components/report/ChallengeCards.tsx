import { ShieldAlert } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import type { ReportChallenge } from '@/types/report';

export interface ChallengeCardsProps {
  challenges: ReportChallenge[];
}

/** The Devil's Advocate's real, evidence-grounded attacks on the decision -
 * never a fabricated counter-argument, always tied to a specific claim. */
export function ChallengeCards({ challenges }: ChallengeCardsProps) {
  if (challenges.length === 0) {
    return (
      <EmptyState
        icon={ShieldAlert}
        title="No challenges raised yet"
        description="The Devil's Advocate has not raised any challenges for this decision, or the analysis has not reached this stage yet."
      />
    );
  }

  return (
    <ul className="space-y-4">
      {challenges.map((challenge) => (
        <li key={challenge.id} className="rounded-xl border border-hairline bg-surface p-5 md:p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <p className="text-small text-ink-muted">{challenge.claim}</p>
            <div className="flex shrink-0 items-center gap-2">
              <Badge tone={challenge.severityTone} size="sm">
                {challenge.severityLabel} severity
              </Badge>
              {challenge.confidencePercent !== undefined ? (
                <Badge tone="neutral" size="sm" variant="outline">
                  {challenge.confidencePercent}% confidence
                </Badge>
              ) : null}
            </div>
          </div>

          <p className="mt-3 text-card-title text-ink">{challenge.attack}</p>

          {challenge.failureMechanism ? (
            <div className="mt-4 border-t border-hairline pt-4">
              <p className="eyebrow">How this could fail</p>
              <p className="mt-2 text-small text-ink-secondary">{challenge.failureMechanism}</p>
            </div>
          ) : null}

          {challenge.evidenceBasis ? (
            <p className="mt-3 text-micro text-ink-muted">Basis: {challenge.evidenceBasis}</p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
