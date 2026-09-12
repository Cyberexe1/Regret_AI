import { ChevronDown } from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { faqHeading, faqItems, LAUNCH_ANCHORS } from '@/data/landingLaunch';
import { cn } from '@/lib/cn';
import { BAND, TYPE_SECTION } from './tokens';

/**
 * Reference accordion. Built on native `details` / `summary` so it opens
 * without JavaScript, is keyboard operable by default, and exposes correct
 * expanded state to assistive technology.
 */
export function LaunchFaq() {
  return (
    <section id={LAUNCH_ANCHORS.faq} className={cn(BAND, 'scroll-mt-24 py-16 md:py-20')}>
      <Reveal className="mx-auto flex max-w-180 flex-col gap-12">
        <h2 className={cn(TYPE_SECTION, 'text-center text-ink')}>{faqHeading}</h2>

        <div>
          {faqItems.map((item) => (
            <details key={item.question} className="group border-b border-white/10">
              {/* `list-none` hides the marker in Chrome and Firefox; the
                  webkit pseudo-element is needed for Safari. */}
              <summary className="flex cursor-pointer list-none items-center gap-3 py-4 [&::-webkit-details-marker]:hidden">
                <span className="flex-1 text-base font-medium text-ink">{item.question}</span>
                <ChevronDown
                  className="size-4 shrink-0 text-ink transition-transform duration-200 ease-out group-open:-rotate-180"
                  aria-hidden
                />
              </summary>
              <p className="pr-8 pb-4 text-base text-ink-secondary">{item.answer}</p>
            </details>
          ))}
        </div>
      </Reveal>
    </section>
  );
}
