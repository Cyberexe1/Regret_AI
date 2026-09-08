import {
  CapabilitiesSection,
  ExampleSection,
  FinalCtaSection,
  HeroSection,
  HowItWorksSection,
  LandingFooter,
  LandingNav,
  ProblemSection,
} from '@/components/landing';

/**
 * Root route. Composition only: every band is a section component under
 * `components/landing`, and its copy lives in `data/landing.ts`.
 */
export function LandingPage() {
  return (
    <div className="min-h-dvh bg-canvas text-ink">
      <LandingNav />

      <main id="landing-content">
        <HeroSection />
        <ProblemSection />
        <HowItWorksSection />
        <ExampleSection />
        <CapabilitiesSection />
        <FinalCtaSection />
      </main>

      <LandingFooter />
    </div>
  );
}
