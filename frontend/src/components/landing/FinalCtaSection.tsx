import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { buttonClasses } from '@/components/ui/Button';
import { LANDING_ANCHORS } from '@/data/landing';
import { ROUTES } from '@/data/navigation';
import { Reveal } from '@/components/Reveal';
import { cn } from '@/lib/cn';
import { LANDING_CONTAINER } from './LandingSection';

export function FinalCtaSection() {
  return (
    <section
      id={LANDING_ANCHORS.about}
      className="relative scroll-mt-[calc(var(--header-offset)+0.25rem)] overflow-hidden border-t border-hairline py-24 md:py-32"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-0 h-100"
        style={{
          background:
            'radial-gradient(50% 70% at 50% 100%, color-mix(in oklab, var(--color-accent) 12%, transparent) 0%, transparent 70%)',
        }}
      />

      <div className={cn(LANDING_CONTAINER, 'relative text-center')}>
        <Reveal>
          <h2 className="mx-auto max-w-3xl text-page-title text-ink">
            Don&rsquo;t ask AI what to choose.
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-body-lg text-ink-secondary">
            Ask what you need to know before you choose.
          </p>

          <div className="mt-10 flex justify-center">
            <Link
              to={ROUTES.newDecision}
              className={buttonClasses({ variant: 'primary', size: 'lg' })}
            >
              Stress-Test Your Decision
              <ArrowRight className="size-4.5" aria-hidden />
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
