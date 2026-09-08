import { useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ArrowRight, RotateCcw, TriangleAlert } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button, buttonClasses, type ButtonVariant } from '@/components/ui/Button';
import type { ExperimentChoice, ExperimentVerdict } from '@/types';
import { DURATION, EASE_OUT } from '@/lib/motion';

const EMPHASIS_TO_VARIANT: Record<ExperimentChoice['emphasis'], ButtonVariant> = {
  primary: 'primary',
  secondary: 'secondary',
  ghost: 'ghost',
};

export interface ExperimentVerdictCardProps {
  verdict: ExperimentVerdict;
}

/**
 * Presents the evidence and three equally available paths. Selecting one is
 * recorded in local state and can be undone, so nothing is forced or final.
 */
export function ExperimentVerdictCard({ verdict }: ExperimentVerdictCardProps) {
  const [chosenId, setChosenId] = useState<string | null>(null);
  const reduceMotion = useReducedMotion();

  const chosen = verdict.choices.find((choice) => choice.id === chosenId) ?? null;

  return (
    <section className="rounded-2xl border border-warning-line bg-panel-warning p-6 md:p-7">
      <div className="flex gap-3.5">
        <TriangleAlert className="mt-0.5 size-5 shrink-0 text-warning-ink" aria-hidden />
        <div className="min-w-0">
          <h3 className="text-section-title text-ink">{verdict.headline}</h3>
          <p className="mt-2.5 max-w-2xl text-small text-ink-secondary">{verdict.detail}</p>
        </div>
      </div>

      <AnimatePresence mode="wait" initial={false}>
        {chosen ? (
          <motion.div
            key="recorded"
            initial={reduceMotion ? undefined : { opacity: 0, y: 6 }}
            animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
            exit={reduceMotion ? undefined : { opacity: 0 }}
            transition={{ duration: DURATION.quick, ease: EASE_OUT }}
            className="mt-6 rounded-xl border border-hairline-strong bg-panel-inset p-5"
          >
            <p className="eyebrow">Path recorded locally</p>
            <p className="mt-2 text-body text-ink">{chosen.recorded}</p>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              {chosen.to ? (
                <Link
                  to={chosen.to}
                  className={buttonClasses({ variant: 'primary', size: 'sm' })}
                >
                  {chosen.label}
                  <ArrowRight className="size-3.5" aria-hidden />
                </Link>
              ) : null}
              <Button
                variant="ghost"
                size="sm"
                leftIcon={RotateCcw}
                onClick={() => setChosenId(null)}
              >
                Choose a different path
              </Button>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="choices"
            initial={reduceMotion ? undefined : { opacity: 0 }}
            animate={reduceMotion ? undefined : { opacity: 1 }}
            exit={reduceMotion ? undefined : { opacity: 0 }}
            transition={{ duration: DURATION.quick }}
            className="mt-6 grid gap-4 lg:grid-cols-3"
          >
            {verdict.choices.map((choice) => (
              <div
                key={choice.id}
                className="flex flex-col justify-between gap-4 rounded-xl border border-hairline-strong bg-panel-inset p-4"
              >
                <p className="text-small text-ink-secondary">{choice.description}</p>
                <Button
                  variant={EMPHASIS_TO_VARIANT[choice.emphasis]}
                  size="sm"
                  fullWidth
                  onClick={() => setChosenId(choice.id)}
                >
                  {choice.label}
                </Button>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
