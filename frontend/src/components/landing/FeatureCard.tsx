import { motion, useReducedMotion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/cn';
import { DURATION, EASE_OUT } from '@/lib/motion';

export interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  body: string;
  /**
   * `statement` renders the title as a claim in section-title size;
   * `label` renders it as a compact capability name.
   */
  emphasis?: 'statement' | 'label';
}

/**
 * Shared card for the problem and capability grids, including the subtle lift
 * on hover. Kept in one place so both grids stay visually identical.
 */
export function FeatureCard({ icon: Icon, title, body, emphasis = 'label' }: FeatureCardProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      whileHover={reduceMotion ? undefined : { y: -3 }}
      transition={{ duration: DURATION.quick, ease: EASE_OUT }}
      className="h-full rounded-xl border border-hairline bg-surface p-6 transition-colors duration-200 hover:border-hairline-strong hover:bg-surface-raised"
    >
      <span className="inline-flex size-9 items-center justify-center rounded-lg border border-accent-line bg-accent-soft text-accent-ink">
        <Icon className="size-4.5" aria-hidden />
      </span>

      <h3
        className={cn(
          'mt-5 text-ink',
          emphasis === 'statement' ? 'text-section-title' : 'text-card-title',
        )}
      >
        {title}
      </h3>
      <p className="mt-2.5 text-small text-ink-secondary">{body}</p>
    </motion.div>
  );
}
