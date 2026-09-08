import { FlaskConical, TriangleAlert } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Divider } from '@/components/ui/Divider';
import { exampleAnalysis, LANDING_ANCHORS } from '@/data/landing';
import { cn } from '@/lib/cn';
import { toneFill, toneText } from '@/lib/tone';
import type { Tone } from '@/types';
import { Reveal } from '@/components/Reveal';
import { LandingSection } from './LandingSection';

/**
 * Horizontal scale showing the evidence band against the threshold the decision
 * needs to clear. Positions are derived from the example values, not hardcoded.
 */
function ThresholdBar() {
  const { scaleMax, evidenceRange, thresholdValue, risk } = exampleAnalysis;
  const [low, high] = evidenceRange;

  const toPercent = (value: number) => `${(value / scaleMax) * 100}%`;

  return (
    <div className="pt-2">
      <div className="relative h-2 w-full rounded-full bg-surface-inset">
        <div
          className={cn('absolute inset-y-0 rounded-full', toneFill[risk.tone])}
          style={{ left: toPercent(low), width: toPercent(high - low) }}
        />
        <div
          className="absolute -top-1 -bottom-1 w-0.5 rounded-full bg-accent"
          style={{ left: toPercent(thresholdValue) }}
        />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1.5">
        <span className="inline-flex items-center gap-2 text-small text-ink-secondary">
          <span className={cn('size-2 rounded-sm', toneFill[risk.tone])} aria-hidden />
          Observed range
        </span>
        <span className="inline-flex items-center gap-2 text-small text-ink-secondary">
          <span className="h-3 w-0.5 rounded-full bg-accent" aria-hidden />
          Required threshold
        </span>
        <span className="numeric ml-auto text-small text-ink-muted">
          Scale 0–{scaleMax}%
        </span>
      </div>
    </div>
  );
}

function MetricRow({ label, value, tone }: { label: string; value: string; tone?: Tone }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-3">
      <span className="text-small text-ink-secondary">{label}</span>
      <span className={cn('numeric text-card-title', tone ? toneText[tone] : 'text-ink')}>
        {value}
      </span>
    </div>
  );
}

export function ExampleSection() {
  const example = exampleAnalysis;

  return (
    <LandingSection
      id={LANDING_ANCHORS.product}
      bordered
      eyebrow="Worked example"
      title="One decision, reduced to the number that decides it."
      lead="The engine does not answer the question. It finds the single uncertainty the decision turns on, then tells you what it would cost to resolve it."
    >
      <Reveal>
        <div className="overflow-hidden rounded-2xl border border-hairline-strong bg-surface shadow-raised">
          {/* Panel header */}
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-hairline bg-surface-raised/60 px-5 py-4 md:px-7 md:py-5">
            <div className="min-w-0">
              <p className="eyebrow">Decision {example.reference}</p>
              <h3 className="mt-1.5 text-section-title text-ink">{example.decision}</h3>
            </div>
            <Badge tone="neutral" size="sm" variant="outline">
              Illustrative example
            </Badge>
          </div>

          <div className="grid gap-0 lg:grid-cols-[minmax(0,1fr)_20rem]">
            {/* Left: the uncertainty that decides it */}
            <div className="px-5 py-6 md:px-7 md:py-7">
              <div className="flex items-center gap-2.5">
                <TriangleAlert className="size-4 shrink-0 text-warning-ink" aria-hidden />
                <p className="eyebrow">Critical uncertainty</p>
              </div>
              <p className="mt-2 text-section-title text-ink">{example.criticalUncertainty}</p>

              <div className="mt-6 divide-y divide-hairline border-y border-hairline">
                <MetricRow
                  label="Current evidence"
                  value={example.currentEvidence}
                  tone={example.risk.tone}
                />
                <MetricRow label="Required threshold" value={example.requiredThreshold} />
              </div>

              <ThresholdBar />
            </div>

            {/* Right: risk read-out */}
            <div className="border-t border-hairline bg-surface-inset/60 px-5 py-6 md:px-7 lg:border-t-0 lg:border-l">
              <p className="eyebrow">Decision risk</p>
              <p className={cn('mt-2 text-page-title', toneText[example.risk.tone])}>
                {example.risk.label}
              </p>
              <p className="mt-2 text-small text-ink-secondary">
                Driven by one unresolved uncertainty with a measurable threshold, not by the size of
                the cheque.
              </p>

              <Divider className="my-6" />

              <p className="eyebrow">Reversibility</p>
              <p className="mt-2 text-card-title text-ink">Costly to reverse</p>
              <p className="mt-2 text-small text-ink-secondary">
                Capital is committed up front; the lease and equipment outlast the test.
              </p>
            </div>
          </div>

          {/* Recommended experiment */}
          <div
            id={LANDING_ANCHORS.experiments}
            className="scroll-mt-[calc(var(--topbar-height)+1rem)] border-t border-accent-line bg-accent-soft/50 px-5 py-5 md:px-7"
          >
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex min-w-0 gap-3">
                <FlaskConical className="mt-0.5 size-4.5 shrink-0 text-accent-ink" aria-hidden />
                <div className="min-w-0">
                  <p className="eyebrow">Recommended action</p>
                  <p className="mt-1.5 text-section-title text-ink">{example.recommendedAction}</p>
                </div>
              </div>
              <Badge tone="accent" size="sm">
                {example.experimentCost}
              </Badge>
            </div>
          </div>
        </div>
      </Reveal>
    </LandingSection>
  );
}
