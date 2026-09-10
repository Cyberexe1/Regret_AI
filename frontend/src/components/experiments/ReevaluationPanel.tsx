import { ArrowDown, TrendingDown, TrendingUp, Minus, HelpCircle } from 'lucide-react';
import type { ApiReEvaluation, DecisionAssessmentStatus } from '@/api/types';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { cn } from '@/lib/cn';
import { toneSurface, toneText } from '@/lib/tone';
import type { Tone } from '@/types';

export interface ReevaluationPanelProps {
  reevaluation: ApiReEvaluation;
}

const ASSESSMENT_TONE: Record<DecisionAssessmentStatus, Tone> = {
  strengthened: 'success',
  weakened: 'danger',
  unchanged: 'neutral',
  inconclusive: 'warning',
  requires_more_evidence: 'info',
};

const ASSESSMENT_ICON: Record<DecisionAssessmentStatus, typeof TrendingUp> = {
  strengthened: TrendingUp,
  weakened: TrendingDown,
  unchanged: Minus,
  inconclusive: HelpCircle,
  requires_more_evidence: HelpCircle,
};

const ASSESSMENT_LABEL: Record<DecisionAssessmentStatus, string> = {
  strengthened: 'Strengthened',
  weakened: 'Weakened',
  unchanged: 'Unchanged',
  inconclusive: 'Inconclusive',
  requires_more_evidence: 'Requires more evidence',
};

/**
 * The before/after re-evaluation moment: what the decision looked like
 * before this experiment result, what was actually observed, and how the
 * backend's deterministic re-evaluation (never an LLM call - see
 * `app.services.re_evaluation_service`) assessed the decision afterward.
 * Every value here is real, persisted backend data.
 */
export function ReevaluationPanel({ reevaluation }: ReevaluationPanelProps) {
  const assessment = reevaluation.decision_assessment;
  const AssessmentIcon = ASSESSMENT_ICON[assessment.status];
  const tone = ASSESSMENT_TONE[assessment.status];

  return (
    <div className="space-y-5">
      <Card variant="inset">
        <p className="eyebrow">Before</p>
        <p className="mt-2 text-small text-ink-secondary">{reevaluation.previous_assessment}</p>
      </Card>

      <div className="flex items-center justify-center">
        <ArrowDown className="size-5 text-ink-muted" aria-hidden />
      </div>

      <Card variant="inset">
        <p className="eyebrow">What was observed</p>
        <p className="mt-2 text-small text-ink-secondary">{reevaluation.new_assessment}</p>
      </Card>

      {reevaluation.threshold_comparisons.length > 0 ? (
        <div className="space-y-3">
          <p className="eyebrow">Threshold comparisons</p>
          {reevaluation.threshold_comparisons.map((comparison) => (
            <div key={comparison.threshold_id} className="rounded-lg border border-hairline bg-surface px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-small font-medium text-ink">{comparison.variable}</p>
                <Badge tone="neutral" size="sm" variant="outline">
                  {comparison.status.replace('_', ' ')}
                </Badge>
              </div>
              <p className="mt-1.5 text-small text-ink-secondary">{comparison.explanation}</p>
              {comparison.observed_value !== null ? (
                <p className="numeric mt-1.5 text-micro text-ink-muted">
                  Observed: {comparison.observed_value}
                  {comparison.threshold_value ? ` · Threshold: ${comparison.threshold_value}` : ''}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}

      <div className="flex items-center justify-center">
        <ArrowDown className="size-5 text-ink-muted" aria-hidden />
      </div>

      <section
        className={cn(
          'overflow-hidden rounded-2xl border p-6 md:p-7',
          toneSurface[tone],
        )}
      >
        <div className="flex items-center gap-2.5">
          <AssessmentIcon className={cn('size-5 shrink-0', toneText[tone])} aria-hidden />
          <p className="eyebrow">Decision assessment</p>
        </div>

        <h3 className={cn('mt-3 text-headline', toneText[tone])}>{ASSESSMENT_LABEL[assessment.status]}</h3>
        <p className="mt-3 max-w-2xl text-body text-ink-secondary">{assessment.summary}</p>

        <p className="mt-4 text-micro text-ink-muted">
          Confidence reflects how deterministic this comparison was, not the probability the decision succeeds.
        </p>

        <div className="mt-6 rounded-xl border border-hairline-strong bg-panel-inset px-5 py-4">
          <p className="eyebrow">Recommended next step</p>
          <p className="mt-2 text-small text-ink-secondary">{reevaluation.recommended_next_step}</p>
        </div>

        <p className="mt-5 text-small font-medium text-ink">{reevaluation.key_learning}</p>
      </section>
    </div>
  );
}
