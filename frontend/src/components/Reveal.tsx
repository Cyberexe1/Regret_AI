import type { ReactNode } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { DURATION, EASE_OUT } from '@/lib/motion';

export interface RevealProps {
  children: ReactNode;
  /** Stagger offset in seconds. */
  delay?: number;
  className?: string;
}

/**
 * One-shot entrance as the element scrolls into view. Respects the operating
 * system reduced-motion preference by rendering statically.
 *
 * Shared by the landing page and the workspace, so entrance motion is
 * consistent across the product.
 */
export function Reveal({ children, delay = 0, className }: RevealProps) {
  const reduceMotion = useReducedMotion();

  if (reduceMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-48px' }}
      transition={{ duration: DURATION.entrance, delay, ease: EASE_OUT }}
    >
      {children}
    </motion.div>
  );
}
