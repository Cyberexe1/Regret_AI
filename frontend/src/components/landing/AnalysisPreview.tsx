import { motion, useReducedMotion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { previewStages } from '@/data/landing';
import { cn } from '@/lib/cn';
import { toneFill } from '@/lib/tone';

/**
 * Abstract product-interface preview for the hero: the five stages an analysis
 * moves through, rendered as real interface chrome rather than an illustration.
 */
export function AnalysisPreview() {
  const reduceMotion = useReducedMotion();
  const lastIndex = previewStages.length - 1;

  return (
    <div className="relative">
      {/* Single soft accent wash behind the panel */}
      <div
        aria-hidden
        className="pointer-events-none absolute -inset-x-8 -inset-y-10 -z-10 opacity-70"
        style={{
          background:
            'radial-gradient(60% 55% at 65% 30%, var(--color-accent-soft) 0%, transparent 70%)',
        }}
      />

      <div className="overflow-hidden rounded-2xl border border-hairline-strong bg-surface shadow-raised">
        <div className="flex items-center justify-between gap-3 border-b border-hairline bg-surface-raised/60 px-5 py-3.5">
          <div className="min-w-0">
            <p className="eyebrow">Analysis pipeline</p>
            <p className="truncate text-card-title text-ink">Cloud kitchen investment</p>
          </div>
          <Badge tone="accent" size="sm">
            5 stages
          </Badge>
        </div>

        <ol className="px-5 py-5">
          {previewStages.map((stage, index) => {
            const isLast = index === lastIndex;

            return (
              <motion.li
                key={stage.label}
                className="grid grid-cols-[1.5rem_minmax(0,1fr)] gap-x-3"
                initial={reduceMotion ? undefined : { opacity: 0, y: 10 }}
                animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
                transition={{
                  duration: 0.45,
                  delay: 0.35 + index * 0.09,
                  ease: [0.22, 1, 0.36, 1],
                }}
              >
                <div className="flex flex-col items-center pt-1.5">
                  <span
                    className={cn(
                      'size-2.5 shrink-0 rounded-full ring-4 ring-surface',
                      toneFill[stage.tone],
                    )}
                    aria-hidden
                  />
                  {isLast ? null : <span className="mt-1 w-px flex-1 bg-hairline" aria-hidden />}
                </div>

                <div className={cn('min-w-0', isLast ? 'pb-0' : 'pb-6')}>
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-card-title text-ink">{stage.label}</p>
                    <Badge tone={stage.tone} size="sm" variant={isLast ? 'soft' : 'outline'}>
                      {stage.chip}
                    </Badge>
                  </div>
                  <p className="mt-1 text-small text-ink-secondary">{stage.detail}</p>
                </div>
              </motion.li>
            );
          })}
        </ol>

        <div className="flex items-center gap-2.5 border-t border-hairline bg-accent-soft/40 px-5 py-3.5">
          <ArrowRight className="size-4 shrink-0 text-accent-ink" aria-hidden />
          <p className="text-small text-ink-secondary">
            Output is an experiment, not an answer.
          </p>
        </div>
      </div>
    </div>
  );
}
