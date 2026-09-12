import {
  LaunchBento,
  LaunchCapabilities,
  LaunchCta,
  LaunchFaq,
  LaunchFooter,
  LaunchHero,
  LaunchNavbar,
  LaunchRising,
  LaunchStack,
  LaunchWorkflow,
} from '@/components/landing';

/**
 * Root route.
 *
 * Composition only: the page follows the Launch UI dark-mode desktop layout
 * band for band (navbar, hero + mockup, stack strip, bento, capability grid,
 * rising feature, workflow tabs, FAQ, CTA, footer). Each band is a component
 * under `components/landing`, and every line of copy lives in
 * `data/landingLaunch.ts`.
 *
 * The reference's testimonial and pricing bands are intentionally absent:
 * there are no customers to quote and nothing to charge for yet.
 */
export function LandingPage() {
  return (
    <div className="min-h-dvh bg-canvas text-ink">
      <LaunchNavbar />

      <main id="landing-content">
        <LaunchHero />
        <LaunchStack />
        <LaunchBento />
        <LaunchCapabilities />
        <LaunchRising />
        <LaunchWorkflow />
        <LaunchFaq />
        <LaunchCta />
      </main>

      <LaunchFooter />
    </div>
  );
}
