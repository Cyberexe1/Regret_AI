import { motion, useReducedMotion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { buttonClasses } from '@/components/ui/Button';
import { LANDING_ANCHORS } from '@/data/landing';
import { ROUTES } from '@/data/navigation';
import { cn } from '@/lib/cn';
import { AnalysisPreview } from './AnalysisPreview';
import { LANDING_CONTAINER } from './LandingSection';

export function HeroSection() {
  const reduceMotion = useReducedMotion();

  const entrance = (delay: number) =>
    reduceMotion
      ? {}
      : {
          initial: { opacity: 0, y: 20 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.6, delay, ease: [0.22, 1, 0.36, 1] as const },
        };

  return (
    <section className="relative overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-125"
        style={{
          background:
            'radial-gradient(50% 60% at 50% 0%, color-mix(in oklab, var(--color-accent) 10%, transparent) 0%, transparent 70%)',
        }}
      />

      <div
        className={cn(
          LANDING_CONTAINER,
          'relative grid items-center gap-14 pt-16 pb-20 md:pt-24 md:pb-28 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-16',
        )}
      >
        <div>
          <motion.p className="eyebrow" {...entrance(0)}>
            Decision intelligence
          </motion.p>

          <motion.h1 className="mt-5 text-display text-ink" {...entrance(0.08)}>
            Know what could make your decision fail.
          </motion.h1>

          <motion.p
            className="mt-6 max-w-xl text-body text-ink-secondary md:text-[1.0625rem]"
            {...entrance(0.16)}
          >
            REGRET ENGINE stress-tests important decisions, exposes hidden assumptions, identifies
            failure conditions, and finds the cheapest experiment to run before you commit.
          </motion.p>

          <motion.div className="mt-9 flex flex-wrap items-center gap-3" {...entrance(0.24)}>
            <Link
              to={ROUTES.newDecision}
              className={buttonClasses({ variant: 'primary', size: 'lg' })}
            >
              Analyze a Decision
              <ArrowRight className="size-4.5" aria-hidden />
            </Link>
            <a
              href={`#${LANDING_ANCHORS.howItWorks}`}
              className={buttonClasses({ variant: 'secondary', size: 'lg' })}
            >
              See How It Works
            </a>
          </motion.div>
        </div>

        <motion.div {...entrance(0.2)}>
          <AnalysisPreview />
        </motion.div>
      </div>
    </section>
  );
}
