import { Reveal } from '@/components/Reveal';
import { rising } from '@/data/landingLaunch';
import { cn } from '@/lib/cn';
import { Glow } from './Glow';
import { RisingPlanet } from './RisingPlanet';
import { BAND, GRADIENT_TEXT, TYPE_DISPLAY, TYPE_LEAD } from './tokens';

/**
 * Reference "rising" band: a display heading over a planet edge climbing into
 * frame, rim-lit from behind.
 *
 * Copy stays in the normal 1312px content band. The illustration is deliberately
 * outside it and spans the viewport: putting a horizon inside a content column
 * gives it hard vertical edges and makes it look like a card.
 */
export function LaunchRising() {
  return (
    <section className="relative isolate overflow-hidden pt-24 md:pt-32">
      <Reveal className={cn(BAND, 'flex flex-col items-center gap-8')}>
        <h2 className={cn(TYPE_DISPLAY, GRADIENT_TEXT, 'max-w-5xl text-center')}>
          {rising.title}
        </h2>
        <p className={cn(TYPE_LEAD, 'max-w-2xl text-center')}>{rising.lead}</p>
      </Reveal>

      {/* The art starts close to the copy. Overflow remains visible here so the
          blurred atmosphere can feather upward instead of being cut at the
          illustration's own top edge. The section still clips at the viewport
          boundary, preventing horizontal scroll. */}
      <div aria-hidden className="relative mt-6 h-64 w-full sm:h-80 lg:h-[26rem]">
        <Glow
          variant="wide"
          className="-top-20 -right-20 -left-20 h-60 -z-10"
          opacity={0.58}
        />

        <RisingPlanet />

        {/* Settles the base of the sphere back into the page. */}
        <div
          className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3"
          style={{
            background: 'linear-gradient(180deg, transparent 0%, var(--color-canvas) 94%)',
          }}
        />
      </div>
    </section>
  );
}
