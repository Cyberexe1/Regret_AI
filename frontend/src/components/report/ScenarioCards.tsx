import { motion, useReducedMotion } from 'framer-motion';
import { Minus, TrendingDown, TrendingUp } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/cn';
import { riskLabel, riskTone, toneSurface, toneText } from '@/lib/tone';
import type { FutureScenario, ScenarioKind } from '@/types';
import { DURATION, EASE_OUT } from '@/lib/motion';

const KIND_ICON: Record<ScenarioKind, LucideIcon> = {
  base: Minus,
  failure: TrendingDown,
  upside: TrendingUp,
};

export interface ScenarioCardsProps {
  scenarios: FutureScenario[];
}

export function ScenarioCards({ scenarios }: ScenarioCardsProps) {
  const reduceMotion = useReducedMotion();

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {scenarios.map((scenario) => {
        const Icon = KIND_ICON[scenario.kind];

        return (
          <motion.article
            key={scenario.id}
            whileHover={reduceMotion ? undefined : { y: -3 }}
            transition={{ duration: DURATION.quick, ease: EASE_OUT }}
            className="flex h-full flex-col rounded-xl border border-hairline bg-surface p-5 transition-colors duration-200 hover:border-hairline-strong"
          >
            <div className="flex items-center justify-between gap-3">
              <span
                className={cn(
                  'inline-flex size-8 items-center justify-center rounded-md border',
                  toneSurface[scenario.tone],
                )}
              >
                <Icon className="size-4" aria-hidden />
              </span>
              <Badge tone="neutral" size="sm" variant="outline">
                Illustrative scenario
              </Badge>
            </div>

            <h4 className={cn('mt-4 text-card-title', toneText[scenario.tone])}>
              {scenario.title}
            </h4>
            <p className="mt-2 text-small text-ink-secondary">{scenario.description}</p>

            <dl className="mt-5 space-y-3 border-t border-hairline pt-4">
              <div className="flex items-baseline justify-between gap-3">
                <dt className="text-small text-ink-muted">Probability</dt>
                <dd className="numeric text-small font-medium text-ink">
                  {scenario.probability}%
                </dd>
              </div>
              <div className="flex items-baseline justify-between gap-3">
                <dt className="text-small text-ink-muted">Impact</dt>
                <dd className={cn('text-small font-medium', toneText[riskTone[scenario.impact]])}>
                  {riskLabel[scenario.impact]}
                </dd>
              </div>
              <div>
                <dt className="text-small text-ink-muted">Trigger</dt>
                <dd className="mt-1.5 text-small text-ink-secondary">{scenario.trigger}</dd>
              </div>
            </dl>
          </motion.article>
        );
      })}
    </div>
  );
}
