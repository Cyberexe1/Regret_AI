/* -------------------------------------------------------------------------- *
 * Rising planet
 *
 * A rim-lit sphere climbing into frame from below.
 *
 * The first attempt at this stacked blurred CSS borders on a 1040px circle,
 * which cannot work: a 6px border blurred by 22px spreads into a flat brown
 * smear with no defined edge, and three of them overlapping just muddies it
 * further. SVG gives an actual stroke with an actual blur radius, so the rim
 * can be built the way real rim light behaves — a wide dim halo, a warm mid
 * band, and one crisp hot line exactly on the edge.
 *
 * Geometry (viewBox units): the sphere is far larger than the frame and its
 * centre sits below the bottom edge, so only the top cap is visible and the
 * body runs off both sides at the bottom. See `PLANET` for the numbers.
 * -------------------------------------------------------------------------- */

const PLANET = {
  /** Frame. Wide and shallow, so the arc reads as a horizon rather than a ball. */
  width: 1200,
  height: 460,
  /** Sphere radius and centre. `cy` is below the frame on purpose. */
  r: 720,
  cx: 600,
  cy: 780,
} as const;

/**
 * Headroom above the crown, and therefore the largest the in-frame halo may be.
 *
 * `preserveAspectRatio` anchors the art to the top, so anything painted above
 * `y = 0` is simply gone — and a halo cut mid-gradient leaves a hard horizontal
 * seam across the band. Tying the halo's vertical radius to the headroom means
 * it always reaches zero opacity exactly at the frame edge. The broad
 * atmospheric bloom is a CSS `Glow` behind this svg instead, where it is free
 * to bleed past the edge without being sliced.
 */
const HALO_RY = PLANET.cy - PLANET.r;

/** Top of the arc, and the sphere's half-width where it leaves the frame. */
export const PLANET_GEOMETRY = {
  crownY: PLANET.cy - PLANET.r,
  halfWidthAtBottom: Math.sqrt(PLANET.r ** 2 - (PLANET.cy - PLANET.height) ** 2),
} as const;

export function RisingPlanet() {
  const { width, height, r, cx, cy } = PLANET;

  return (
    <svg
      aria-hidden
      viewBox={`0 0 ${width} ${height}`}
      // `slice` keeps the crown of the arc in frame at every width, cropping
      // the sides on narrow screens rather than shrinking it to a sliver.
      preserveAspectRatio="xMidYMin slice"
      className="block size-full max-w-full overflow-visible"
    >
      <defs>
        {/* Confines the rim to the upper arc: light comes from behind the top
            of the sphere, so the flanks fall away into shadow. */}
        <linearGradient id="planet-rim-falloff" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#fff" stopOpacity="1" />
          <stop offset="26%" stopColor="#fff" stopOpacity="0.9" />
          <stop offset="52%" stopColor="#fff" stopOpacity="0.25" />
          <stop offset="72%" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
        <mask id="planet-rim-mask">
          <rect width={width} height={height} fill="url(#planet-rim-falloff)" />
        </mask>

        {/* Body: barely lifted at the crown, sinking to canvas lower down, so
            the sphere has some form instead of reading as a flat hole. */}
        <linearGradient id="planet-body" x1="0" y1="0" x2="0" y2="1">
          <stop
            offset="0%"
            stopColor="var(--color-accent-press)"
            stopOpacity="0.16"
          />
          <stop offset="34%" stopColor="var(--color-surface)" stopOpacity="0.55" />
          <stop offset="100%" stopColor="var(--color-canvas)" stopOpacity="1" />
        </linearGradient>

        {/* Halo sitting above the horizon, in front of the page glow. */}
        <radialGradient id="planet-halo">
          <stop
            offset="0%"
            stopColor="var(--color-accent)"
            stopOpacity="0.5"
          />
          <stop offset="45%" stopColor="var(--color-accent-press)" stopOpacity="0.22" />
          <stop offset="100%" stopColor="var(--color-accent-press)" stopOpacity="0" />
        </radialGradient>

        <filter id="planet-blur-wide" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="26" />
        </filter>
        <filter id="planet-blur-mid" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="9" />
        </filter>
        <filter id="planet-blur-tight" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2.5" />
        </filter>
      </defs>

      {/* Atmospheric halo above the crown. Its radius is limited to the exact
          available headroom, so it reaches zero opacity at y=0 rather than
          being sliced there at visible strength. */}
      <ellipse
        cx={cx}
        cy={PLANET_GEOMETRY.crownY}
        rx={width * 0.46}
        ry={HALO_RY}
        fill="url(#planet-halo)"
      />

      <circle cx={cx} cy={cy} r={r} fill="url(#planet-body)" />

      <g mask="url(#planet-rim-mask)" fill="none">
        {/* Wide dim bloom. */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          stroke="var(--color-accent-press)"
          strokeWidth="30"
          strokeOpacity="0.75"
          filter="url(#planet-blur-wide)"
        />
        {/* Warm mid band. */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          stroke="var(--color-accent)"
          strokeWidth="11"
          strokeOpacity="0.85"
          filter="url(#planet-blur-mid)"
        />
        {/* Hot line on the edge itself. This is the detail that makes it read
            as a lit sphere rather than a gradient. */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          stroke="var(--color-accent-ink)"
          strokeWidth="2.5"
          strokeOpacity="0.95"
          filter="url(#planet-blur-tight)"
        />
      </g>
    </svg>
  );
}
