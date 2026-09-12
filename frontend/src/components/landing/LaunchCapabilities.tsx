import { Reveal } from '@/components/Reveal';
import { capabilitiesHeading, capabilityItems, LAUNCH_ANCHORS } from '@/data/landingLaunch';
import { cn } from '@/lib/cn';
import { BAND, TYPE_SECTION } from './tokens';

/** Item grid: centred heading, then icon + title + description in four columns. */
export function LaunchCapabilities() {
  return (
    <section
      id={LAUNCH_ANCHORS.capabilities}
      className={cn(BAND, 'scroll-mt-24 py-16 md:py-20')}
    >
      <Reveal className="flex justify-center">
        <h2 className={cn(TYPE_SECTION, 'max-w-lg text-center text-ink')}>
          {capabilitiesHeading}
        </h2>
      </Reveal>

      <ul className="mt-16 grid min-w-0 grid-cols-[minmax(0,1fr)] gap-12 sm:grid-cols-2 lg:grid-cols-4">
        {capabilityItems.map(({ icon: Icon, title, body }, index) => (
          <Reveal key={title} delay={index * 0.04} className="min-w-0">
            <li className="min-w-0 w-full">
              <div className="flex min-w-0 items-center gap-2">
                <Icon className="size-6 shrink-0 text-ink" aria-hidden />
                <h3 className="min-w-0 text-lg font-semibold text-ink">{title}</h3>
              </div>
              <p className="mt-2 text-base text-ink-secondary">{body}</p>
            </li>
          </Reveal>
        ))}
      </ul>
    </section>
  );
}
