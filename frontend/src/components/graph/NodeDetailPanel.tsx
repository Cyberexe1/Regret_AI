import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ArrowRight, MousePointerClick } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/Badge';
import { buttonClasses } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { ROUTES } from '@/data/navigation';
import { cn } from '@/lib/cn';
import { graphCategoryLabel, graphCategoryTone, toneText } from '@/lib/tone';
import type { GraphNodeDatum } from '@/types';
import { DURATION, EASE_OUT } from '@/lib/motion';

export interface NodeDetailPanelProps {
  node: GraphNodeDatum | null;
}

export function NodeDetailPanel({ node }: NodeDetailPanelProps) {
  const reduceMotion = useReducedMotion();

  if (!node) {
    return (
      <Card padding="none">
        <EmptyState
          size="inline"
          icon={MousePointerClick}
          title="Nothing selected"
          description="Select any node to see what it depends on, what evidence backs it, and where its threshold sits."
        />
      </Card>
    );
  }

  const tone = graphCategoryTone[node.category];

  return (
    <Card padding="none" className="overflow-hidden">
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={node.id}
          initial={reduceMotion ? undefined : { opacity: 0, y: 6 }}
          animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
          exit={reduceMotion ? undefined : { opacity: 0 }}
          transition={{ duration: DURATION.quick, ease: EASE_OUT }}
        >
          <div className="border-b border-hairline px-5 py-4 md:px-6">
            <Badge tone={tone} size="sm" dot>
              {graphCategoryLabel[node.category]}
            </Badge>
            <h3 className="mt-3 text-section-title text-ink">{node.title}</h3>
          </div>

          <div className="space-y-5 px-5 py-5">
            <div>
              <p className="eyebrow">Type</p>
              <p className={cn('mt-1.5 text-small font-medium', toneText[tone])}>
                {node.typeLabel}
              </p>
            </div>

            <dl className="space-y-2.5 border-t border-hairline pt-4">
              {node.metrics.map((metric) => (
                <div key={metric.label} className="flex items-baseline justify-between gap-4">
                  <dt className="text-small text-ink-muted">{metric.label}</dt>
                  <dd
                    className={cn(
                      'numeric text-right text-small font-medium',
                      metric.tone ? toneText[metric.tone] : 'text-ink',
                    )}
                  >
                    {metric.value}
                  </dd>
                </div>
              ))}
            </dl>

            <div className="border-t border-hairline pt-4">
              <p className="eyebrow">Why this matters</p>
              <p className="mt-2 text-small text-ink-secondary">{node.whyItMatters}</p>
            </div>

            {node.actionable ? (
              <Link
                to={ROUTES.experiments}
                className={cn(
                  buttonClasses({ variant: 'primary', size: 'sm', fullWidth: true }),
                  'mt-1',
                )}
              >
                Design validation experiment
                <ArrowRight className="size-3.5" aria-hidden />
              </Link>
            ) : null}
          </div>
        </motion.div>
      </AnimatePresence>
    </Card>
  );
}
