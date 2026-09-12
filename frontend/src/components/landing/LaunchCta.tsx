import { Link } from 'react-router-dom';
import { Reveal } from '@/components/Reveal';
import { cta } from '@/data/landingLaunch';
import { cn } from '@/lib/cn';
import { Glow } from './Glow';
import { BAND, BTN_GLASS, BTN_LIGHT, BTN_MD, TYPE_SECTION } from './tokens';

/** Closing band: heading, two actions, and the lamp cropped at the fold. */
export function LaunchCta() {
  return (
    <section className="relative isolate overflow-hidden">
      <div className={cn(BAND, 'relative')}>
        <Reveal className="flex min-w-0 flex-col items-center gap-10 pt-24 pb-36 sm:gap-12 sm:pt-32 sm:pb-48">
          <h2 className={cn(TYPE_SECTION, 'text-center text-ink')}>{cta.title}</h2>

          <div className="flex w-full min-w-0 flex-col justify-center gap-4 sm:w-auto sm:flex-row sm:flex-wrap">
            <Link to={cta.primary.to} className={cn(BTN_LIGHT, BTN_MD, 'w-full sm:w-auto')}>
              {cta.primary.label}
            </Link>
            <Link to={cta.secondary.to} className={cn(BTN_GLASS, BTN_MD, 'w-full sm:w-auto')}>
              {cta.secondary.label}
            </Link>
          </div>
        </Reveal>

        <Glow variant="wide" className="inset-x-0 -bottom-40 h-72 -z-10" />
      </div>
    </section>
  );
}
