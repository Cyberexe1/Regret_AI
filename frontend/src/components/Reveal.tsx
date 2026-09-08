import type { ReactNode } from 'react';
import { motion, useReducedMotion } from 'framer-motion';

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
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-64px' }}
      transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
