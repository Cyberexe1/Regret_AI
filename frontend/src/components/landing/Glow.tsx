import { cn } from '@/lib/cn';

export interface GlowProps {
  /**
   * `wide` is the hero / CTA lamp: a broad ember with a tighter, warmer core
   * inside it. `spot` is the circular wash behind the bento illustrations.
   */
  variant?: 'wide' | 'spot';
  className?: string;
  /** 0-1. Sections dim the same lamp rather than recolouring it. */
  opacity?: number;
}

/* -------------------------------------------------------------------------- *
 * Tuning
 *
 * Three things multiply together to decide how strong the lamp looks, and it is
 * easy to starve it by accident:
 *
 *   1. the base colour's luminance,
 *   2. the alpha the falloff stops mix it down to,
 *   3. the blur radius, which spreads that alpha over area.
 *
 * Blur is the one that bites: a 150px blur on a 288px-tall band smears the
 * whole thing into the canvas, so a colour that looks strong on paper vanishes
 * on screen. Blur is therefore kept well under the band height, and the peaks
 * below are the single knob for brightness.
 * -------------------------------------------------------------------------- */

const STRENGTH = {
  /** Broad ember behind the hero and CTA. */
  body: 92,
  /** Hot centre sitting inside it. */
  core: 72,
  /** Circular wash behind bento illustrations. */
  spot: 78,
} as const;

/**
 * Builds the radial falloff for a lamp layer.
 *
 * A plain `closest-side` ramp holds near full strength across most of its
 * radius and then drops off only at the very edge, which reads as a flat disc.
 * These stops fade continuously instead, so each ring outward carries less
 * colour than the one inside it — while still keeping enough mass through the
 * inner half that the lamp is actually visible once blurred.
 *
 * @param color CSS custom property to burn down from.
 * @param peak Strength at the centre, in percent.
 */
function falloff(color: string, peak: number): string {
  const mix = (fraction: number) =>
    `color-mix(in oklab, var(${color}) ${(peak * fraction).toFixed(1)}%, transparent)`;

  return [
    'radial-gradient(closest-side',
    `${mix(1)} 0%`,
    `${mix(0.78)} 22%`,
    `${mix(0.46)} 44%`,
    `${mix(0.2)} 64%`,
    `${mix(0.06)} 82%`,
    'transparent 100%)',
  ].join(', ');
}

/**
 * The single decorative element repeated across the page: an out-of-focus warm
 * ellipse behind content.
 *
 * Colour comes from the middle of the accent ramp — `--color-accent` for the
 * body, `--color-accent-hover` for the core — rather than the light peach
 * `--color-accent-ink` the template used. That keeps it a deep amber ember
 * instead of a neon wash, without dimming it into nothing.
 *
 * Purely presentational: always `aria-hidden`, never intercepts pointer events.
 */
export function Glow({ variant = 'wide', className, opacity = 1 }: GlowProps) {
  if (variant === 'spot') {
    return (
      <div
        aria-hidden
        className={cn('pointer-events-none absolute', className)}
        style={{ opacity }}
      >
        <div
          className="size-full rounded-full blur-[90px]"
          style={{ background: falloff('--color-accent', STRENGTH.spot) }}
        />
      </div>
    );
  }

  /**
   * Two ellipses sharing a centre line. Callers size the wrapper to the band
   * the lamp should occupy — it is not meant to fill the whole section.
   */
  return (
    <div aria-hidden className={cn('pointer-events-none absolute', className)} style={{ opacity }}>
      <div
        className="absolute inset-0 blur-[90px]"
        style={{ background: falloff('--color-accent', STRENGTH.body) }}
      />
      <div
        className="absolute inset-x-[12%] top-1/2 h-[46%] -translate-y-1/2 blur-[26px]"
        style={{ background: falloff('--color-accent-hover', STRENGTH.core) }}
      />
    </div>
  );
}
