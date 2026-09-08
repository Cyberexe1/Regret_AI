import { LANDING_ANCHORS, processSteps, type ProcessStep } from '@/data/landing';
import { cn } from '@/lib/cn';
import { LandingSection } from './LandingSection';
import { Reveal } from './Reveal';

function StepBody({ step }: { step: ProcessStep }) {
  return (
    <>
      <p className="numeric text-small font-medium tracking-[0.14em] text-accent-ink">
        {step.index}
      </p>
      <h3 className="mt-2 text-card-title text-ink">{step.title}</h3>
      <p className="mt-2 text-small text-ink-secondary">{step.body}</p>
    </>
  );
}

/** Node plus the hairline that connects it to the next step. */
function StepNode({ orientation, isLast }: { orientation: 'row' | 'column'; isLast: boolean }) {
  const horizontal = orientation === 'row';

  return (
    <div className={cn('flex', horizontal ? 'items-center' : 'h-full flex-col items-center pt-2')}>
      <span className="size-2 shrink-0 rounded-full bg-accent ring-4 ring-canvas" aria-hidden />
      {isLast ? null : (
        <span
          className={cn(
            'bg-hairline',
            horizontal ? 'ml-2 h-px flex-1 -mr-6' : 'mt-2 w-px flex-1',
          )}
          aria-hidden
        />
      )}
    </div>
  );
}

export function HowItWorksSection() {
  const lastIndex = processSteps.length - 1;

  return (
    <LandingSection
      id={LANDING_ANCHORS.howItWorks}
      bordered
      eyebrow="How it works"
      title="Five passes between a decision and a commitment."
      lead="Each stage produces something concrete: a scored assumption, a failure condition, a threshold, an experiment."
    >
      {/* Horizontal at lg and above */}
      <ol className="hidden lg:grid lg:grid-cols-5">
        {processSteps.map((step, index) => (
          <li key={step.index} className="pr-6">
            <Reveal delay={index * 0.07}>
              <StepNode orientation="row" isLast={index === lastIndex} />
              <div className="mt-5">
                <StepBody step={step} />
              </div>
            </Reveal>
          </li>
        ))}
      </ol>

      {/* Vertical below lg */}
      <ol className="lg:hidden">
        {processSteps.map((step, index) => (
          <li key={step.index} className="grid grid-cols-[1.25rem_minmax(0,1fr)] gap-x-4">
            <StepNode orientation="column" isLast={index === lastIndex} />
            <Reveal delay={0} className={index === lastIndex ? 'pb-0' : 'pb-8'}>
              <StepBody step={step} />
            </Reveal>
          </li>
        ))}
      </ol>
    </LandingSection>
  );
}
