import { capabilities, LANDING_ANCHORS } from '@/data/landing';
import { FeatureCard } from './FeatureCard';
import { LandingSection } from './LandingSection';
import { Reveal } from './Reveal';

export function CapabilitiesSection() {
  return (
    <LandingSection
      id={LANDING_ANCHORS.capabilities}
      bordered
      eyebrow="Capabilities"
      title="What the engine actually does to a decision."
      lead="Six passes, each producing something you can act on rather than a verdict you have to trust."
    >
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {capabilities.map((capability, index) => (
          <Reveal key={capability.title} delay={(index % 3) * 0.07}>
            <FeatureCard
              icon={capability.icon}
              title={capability.title}
              body={capability.body}
            />
          </Reveal>
        ))}
      </div>
    </LandingSection>
  );
}
