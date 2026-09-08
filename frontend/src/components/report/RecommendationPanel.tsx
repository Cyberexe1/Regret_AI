import { ArrowRight, FlaskConical } from 'lucide-react';
import { Link } from 'react-router-dom';
import { buttonClasses } from '@/components/ui/Button';
import { ROUTES } from '@/data/navigation';
import { cn } from '@/lib/cn';
import { riskLabel, riskTone, toneText } from '@/lib/tone';
import type { ReportRecommendation } from '@/types';

export interface RecommendationPanelProps {
  recommendation: ReportRecommendation;
}

/** The conclusion of the report, and the most prominent block on the page. */
export function RecommendationPanel({ recommendation }: RecommendationPanelProps) {
  const facts = [
    { label: 'Estimated experiment cost', value: recommendation.costLabel, tone: 'neutral' as const },
    {
      label: 'Expected learning',
      value: riskLabel[recommendation.expectedLearning],
      tone: riskTone[recommendation.expectedLearning],
    },
    {
      label: 'Decision impact',
      value: riskLabel[recommendation.decisionImpact],
      tone: riskTone[recommendation.decisionImpact],
    },
  ];

  return (
    <section className="overflow-hidden rounded-2xl border border-accent-line bg-accent-soft/40 shadow-raised">
      <div className="p-6 md:p-8">
        <div className="flex items-center gap-2.5">
          <FlaskConical className="size-4 shrink-0 text-accent-ink" aria-hidden />
          <span className="numeric text-micro text-ink-faint">06</span>
          <p className="eyebrow">Recommendation</p>
        </div>

        <h3 className="mt-4 text-[1.75rem] leading-tight font-semibold tracking-[-0.02em] text-ink md:text-[2rem]">
          {recommendation.verdict}
        </h3>

        <p className="mt-4 max-w-2xl text-body text-ink-secondary md:text-[1.0625rem]">
          {recommendation.action}
        </p>

        <dl className="mt-7 grid gap-4 sm:grid-cols-3">
          {facts.map((fact) => (
            <div
              key={fact.label}
              className="rounded-xl border border-hairline-strong bg-canvas/40 px-5 py-4"
            >
              <dt className="eyebrow">{fact.label}</dt>
              <dd
                className={cn(
                  'numeric mt-2 text-card-title font-semibold',
                  fact.tone === 'neutral' ? 'text-ink' : toneText[fact.tone],
                )}
              >
                {fact.value}
              </dd>
            </div>
          ))}
        </dl>

        <Link
          to={ROUTES.experiments}
          className={cn(buttonClasses({ variant: 'primary', size: 'lg' }), 'mt-7')}
        >
          {recommendation.ctaLabel}
          <ArrowRight className="size-4.5" aria-hidden />
        </Link>
      </div>
    </section>
  );
}
