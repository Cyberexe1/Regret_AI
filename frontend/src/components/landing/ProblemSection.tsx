import { LANDING_ANCHORS, problems } from '@/data/landing';
import { FeatureCard } from './FeatureCard';
import { LandingSection } from './LandingSection';
import { Reveal } from './Reveal';

export function ProblemSection() {
  return (
    <LandingSection
      id={LANDING_ANCHORS.problem}
      bordered
      eyebrow="The problem"
      title="Most decisions fail before the decision is made."
      lead="The failure is usually set in the framing: the questions that went unasked and the assumptions nobody wrote down."
    >
      <div className="grid gap-5 md:grid-cols-3">
        {problems.map((problem, index) => (
          <Reveal key={problem.title} delay={index * 0.08}>
            <FeatureCard
              icon={problem.icon}
              title={problem.title}
              body={problem.body}
              emphasis="statement"
            />
          </Reveal>
        ))}
      </div>
    </LandingSection>
  );
}
