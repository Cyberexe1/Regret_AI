import type { Transition } from 'framer-motion';

/* -------------------------------------------------------------------------- *
 * Motion vocabulary
 *
 * One easing curve and four durations for the whole product. Animation is used
 * to explain a change of state, never to decorate, so everything is short.
 * -------------------------------------------------------------------------- */

/** Standard ease-out. The only curve used in the product. */
export const EASE_OUT = [0.22, 1, 0.36, 1] as const;

export const DURATION = {
  /** Hover, toggle, colour change. */
  micro: 0.15,
  /** Panels appearing, overlays, list items. */
  quick: 0.22,
  /** Section reveals and page transitions. */
  entrance: 0.3,
  /** Progress fills, where the travel itself is the information. */
  fill: 0.5,
} as const;

export const transition = {
  micro: { duration: DURATION.micro, ease: EASE_OUT },
  quick: { duration: DURATION.quick, ease: EASE_OUT },
  entrance: { duration: DURATION.entrance, ease: EASE_OUT },
  fill: { duration: DURATION.fill, ease: EASE_OUT },
} satisfies Record<string, Transition>;

/** Stagger step for sequenced reveals. Kept small so lists settle quickly. */
export const STAGGER_STEP = 0.04;
