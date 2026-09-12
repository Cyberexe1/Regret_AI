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
        <Reveal className="flex flex-col items-center gap-12 pt-32 pb-48">
          <h2 className={cn(TYPE_SECTION, 'text-center text-ink')}>{cta.title}</h2>

          <div className="flex flex-wrap justify-center gap-4">
            <Link to={cta.primary.to} className={cn(BTN_LIGHT, BTN_MD)}>
              {cta.primary.label}
            </Link>
            <Link to={cta.secondary.to} className={cn(BTN_GLASS, BTN_MD)}>
              {cta.secondary.label}
            </Link>
          </div>
        </Reveal>

        <Glow variant="wide" className="inset-x-0 -bottom-40 h-72 -z-10" />
      </div>
    </section>
  );
}
