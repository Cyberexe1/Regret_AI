/* -------------------------------------------------------------------------- *
 * Hero backdrop
 *
 * The reference hero leaves everything above the mockup as flat canvas, which
 * reads as empty once the lamp is confined to the mockup band. These layers
 * give the upper hero something to sit on without competing with the headline:
 *
 *   1. warm bleed from behind the navbar, tying the top of the page to the
 *      ember further down
 *   2. a faint centre lift so the headline sits in light rather than on nothing
 *   3. a measurement grid, radially masked so it never reaches an edge and
 *      stop before the mockup
 *   4. corner vignette, pulling focus back to the middle
 *   5. film grain, which is what stops large dark gradients from banding
 *
 * Every layer is decorative: the wrapper is `aria-hidden` and inert.
 * -------------------------------------------------------------------------- */

/** Fractal noise as a data URI. Cheaper and sharper than shipping a PNG. */
const GRAIN =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='180' height='180' filter='url(%23n)'/%3E%3C/svg%3E\")";

/** Keeps the grid off every edge and clear of the mockup below. */
const GRID_MASK = 'radial-gradient(ellipse 78% 52% at 50% 26%, #000 0%, transparent 76%)';

export function HeroBackdrop() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 -z-20 overflow-hidden">
      {/* 1. Warm bleed from above the fold. */}
      <div
        className="absolute inset-x-0 top-0 h-[38rem]"
        style={{
          background:
            'radial-gradient(ellipse 62% 46% at 50% -12%, color-mix(in oklab, var(--color-accent) 20%, transparent) 0%, transparent 72%)',
        }}
      />

      {/* 2. Centre lift behind the headline. */}
      <div
        className="absolute inset-x-0 top-0 h-[42rem]"
        style={{
          background:
            'radial-gradient(ellipse 68% 48% at 50% 26%, color-mix(in oklab, var(--color-ink) 5%, transparent) 0%, transparent 74%)',
        }}
      />

      {/* 3. Measurement grid. A decision tool should feel measured, so the
             texture is a grid rather than an abstract blob. */}
      <div
        className="absolute inset-x-0 top-0 h-[46rem]"
        style={{
          backgroundImage: `
            linear-gradient(to right, color-mix(in oklab, var(--color-ink) 7%, transparent) 1px, transparent 1px),
            linear-gradient(to bottom, color-mix(in oklab, var(--color-ink) 7%, transparent) 1px, transparent 1px)
          `,
          backgroundSize: '72px 72px',
          maskImage: GRID_MASK,
          WebkitMaskImage: GRID_MASK,
        }}
      />

      {/* 4. Vignette. */}
      <div
        className="absolute inset-x-0 top-0 h-[46rem]"
        style={{
          background:
            'radial-gradient(ellipse 96% 74% at 50% 32%, transparent 42%, var(--color-canvas) 100%)',
        }}
      />

      {/* 5. Grain. `screen` rather than the usual `overlay`: overlay decides
             from the base layer, so on a near-black canvas it collapses to a
             multiply and does nothing. Screen adds the noise's own brightness,
             which is what actually breaks up banding in the gradients above. */}
      <div
        className="absolute inset-0 opacity-[0.07] mix-blend-screen"
        style={{ backgroundImage: GRAIN, backgroundRepeat: 'repeat' }}
      />
    </div>
  );
}
