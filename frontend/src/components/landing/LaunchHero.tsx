import { motion, useReducedMotion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { hero } from '@/data/landingLaunch';
import { cn } from '@/lib/cn';
import { DURATION, EASE_OUT } from '@/lib/motion';
import { Glow } from './Glow';
import { HeroBackdrop } from './HeroBackdrop';
import { MockFrame } from './MockScreen';
import { BAND, BTN_GLASS, BTN_LIGHT, BTN_MD, GRADIENT_TEXT, TYPE_HERO, TYPE_LEAD } from './tokens';

/**
 * Hero band: outlined pill, gradient display heading, lead, two actions, then a
 * product mockup lit from behind and faded into the canvas at the bottom.
 *
 * `HeroBackdrop` carries the upper half. Without it the band above the mockup
 * is bare canvas, since the lamp is deliberately confined to the mockup.
 */
export function LaunchHero() {
  const reduceMotion = useReducedMotion();

  const rise = (delay: number) =>
    reduceMotion
      ? {}
      : {
          initial: { opacity: 0, y: 24 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: DURATION.entrance, delay, ease: EASE_OUT },
        };

  return (
    <section className="relative isolate overflow-hidden">
      <HeroBackdrop />

      <div className={cn(BAND, 'relative flex flex-col items-center pt-16 md:pt-20')}>
        <motion.div
          /* Faint fill and blur so the pill still separates from the grid
             running behind it. */
          className="flex flex-wrap items-center justify-center gap-2 rounded-full border border-white/20 bg-white/[0.03] px-2.5 py-1 backdrop-blur-sm"
          {...rise(0)}
        >
          <span className="text-xs font-semibold text-ink-secondary">{hero.badge}</span>
          <a
            href={hero.badgeLink.href}
            className="inline-flex items-center gap-1 text-xs font-semibold text-ink hover:underline"
          >
            {hero.badgeLink.label}
            <ArrowRight className="size-3" aria-hidden />
          </a>
        </motion.div>

        <motion.h1
          className={cn(TYPE_HERO, GRADIENT_TEXT, 'mt-12 max-w-5xl text-center')}
          {...rise(0.08)}
        >
          {hero.title}
        </motion.h1>

        <motion.p className={cn(TYPE_LEAD, 'mt-12 max-w-2xl text-center')} {...rise(0.16)}>
          {hero.lead}
        </motion.p>

        <motion.div className="mt-12 flex flex-wrap justify-center gap-4" {...rise(0.24)}>
          <Link to={hero.primary.to} className={cn(BTN_LIGHT, BTN_MD)}>
            {hero.primary.label}
          </Link>
          <a href={hero.secondary.href} className={cn(BTN_GLASS, BTN_MD)}>
            {hero.secondary.label}
          </a>
        </motion.div>

        {/* Mockup + lamp. The glow sits behind the frame and above the canvas,
            which is what gives the reference its lit-from-below look. */}
        <motion.div className="relative mt-24 w-full" {...rise(0.3)}>
          <Glow variant="wide" className="top-1 -right-16 -left-16 h-72 -z-10" />
          <MockFrame variant="dashboard" fade className="h-[26rem] sm:h-[34rem] lg:h-[46rem]" />
        </motion.div>
      </div>
    </section>
  );
}
