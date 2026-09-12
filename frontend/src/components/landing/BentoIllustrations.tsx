import type { ReactNode } from 'react';
import {
  Braces,
  FlaskConical,
  Gauge,
  GitBranch,
  ScanSearch,
  ShieldAlert,
  type LucideIcon,
} from 'lucide-react';
import { LogoMark } from '@/components/Logo';
import { cn } from '@/lib/cn';
import { Glow } from './Glow';

/* -------------------------------------------------------------------------- *
 * Bento illustrations
 *
 * Four decorative figures from the reference composition: a wireframe globe, a
 * concentric ripple, a tile field with lit icons, and a chat thread. All are
 * drawn in markup rather than imported as images so they follow the accent
 * token, and all are `aria-hidden` â€” the tile copy carries the meaning.
 * -------------------------------------------------------------------------- */

/** Ember halo behind the lit tile icons. Deliberately dim, not a neon bloom. */
const GLOW_FILTER =
  'drop-shadow(0 0 6px color-mix(in oklab, var(--color-accent) 45%, transparent)) ' +
  'drop-shadow(0 0 22px color-mix(in oklab, var(--color-accent-press) 80%, transparent))';

/* --- Wireframe globe ------------------------------------------------------ *
 * Both families of lines are projected from real sphere coordinates rather
 * than faked with axis-aligned ellipses.
 *
 * Orthographic projection of a sphere tilted about the horizontal axis: a
 * point at latitude Ï†, longitude Î» maps to
 *
 *   sx = RÂ·cos Ï†Â·sin Î»
 *   sy = âˆ’(RÂ·sin Ï†Â·cos t âˆ’ RÂ·cos Ï†Â·cos Î»Â·sin t)
 *
 * Latitude rings come out axis-aligned under that transform, but meridians do
 * not â€” they are sheared ellipses. Sampling both as paths gets the meridians
 * right without any rotation maths, and makes the poles converge where they
 * actually belong (slightly inside the silhouette, not on it).
 * -------------------------------------------------------------------------- */

const GLOBE = {
  /** Sphere radius, and centre, in viewBox units. The box is 320 square. */
  r: 148,
  cx: 160,
  cy: 160,
  /** Tilt toward the viewer. Small enough to stay a globe, large enough that
   *  the latitude rings read as curves instead of straight lines. */
  tilt: (20 * Math.PI) / 180,
  /** Points per curve. Enough that the rings stay smooth when scaled up. */
  samples: 128,
} as const;

interface GlobePoint {
  x: number;
  y: number;
  /** True on the hemisphere facing the viewer. */
  front: boolean;
}

function projectToGlobe(latDeg: number, lonDeg: number): GlobePoint {
  const { r, cx, cy, tilt } = GLOBE;
  const lat = (latDeg * Math.PI) / 180;
  const lon = (lonDeg * Math.PI) / 180;

  const x = r * Math.cos(lat) * Math.sin(lon);
  const y = r * Math.sin(lat);
  const z = r * Math.cos(lat) * Math.cos(lon);

  return {
    x: cx + x,
    y: cy - (y * Math.cos(tilt) - z * Math.sin(tilt)),
    // Depth along the view axis after the same tilt: positive faces us.
    front: y * Math.sin(tilt) + z * Math.cos(tilt) >= 0,
  };
}

/**
 * Splits a sampled curve into the contiguous runs that sit on one hemisphere.
 *
 * Drawing the near and far halves as separate paths is what makes the wireframe
 * read as a solid sphere rather than a flat spirograph: the far side is stroked
 * faint, as if seen through the body.
 */
function hemisphereRuns(points: GlobePoint[], front: boolean): string[] {
  const paths: string[] = [];
  let run: string[] = [];

  const flush = () => {
    if (run.length > 1) paths.push(`M${run.join(' L')}`);
    run = [];
  };

  // One extra step wraps past the seam so a run crossing it stays continuous.
  for (let index = 0; index <= points.length; index += 1) {
    const point = points[index % points.length];

    if (point.front === front) {
      run.push(`${point.x.toFixed(2)} ${point.y.toFixed(2)}`);
    } else {
      flush();
    }
  }

  flush();
  return paths;
}

function sampleCurve(at: (turn: number) => GlobePoint): GlobePoint[] {
  return Array.from({ length: GLOBE.samples }, (_, index) =>
    at((index * 360) / GLOBE.samples),
  );
}

/** Seven rings (equator plus three each side) and six great circles. */
const GLOBE_CURVES = [
  ...[-72, -48, -24, 0, 24, 48, 72].map((lat) =>
    sampleCurve((lon) => projectToGlobe(lat, lon)),
  ),
  ...[0, 30, 60, 90, 120, 150].map((lon) => sampleCurve((lat) => projectToGlobe(lat, lon))),
];

const GLOBE_NEAR = GLOBE_CURVES.flatMap((curve) => hemisphereRuns(curve, true));
const GLOBE_FAR = GLOBE_CURVES.flatMap((curve) => hemisphereRuns(curve, false));

/**
 * Wireframe globe, lit from below.
 *
 * The svg scales with `xMidYMid meet` and the viewBox carries 12 units of
 * padding around the silhouette, so the whole sphere stays inside the tile at
 * every width instead of being cropped at the bottom.
 */
export function GlobeFigure() {
  const { r, cx, cy } = GLOBE;

  return (
    <div aria-hidden className="relative flex h-full items-center justify-center">
      <Glow variant="spot" className="left-1/2 size-96 -translate-x-1/2" opacity={0.55} />

      <svg
        viewBox="0 0 320 320"
        preserveAspectRatio="xMidYMid meet"
        className="h-full w-full"
      >
        <defs>
          {/* Body lit from the base, as if the lamp sits below the sphere. */}
          <linearGradient id="globe-body" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%" stopColor="var(--color-accent-press)" stopOpacity="0.26" />
            <stop offset="55%" stopColor="var(--color-accent-press)" stopOpacity="0.1" />
            <stop offset="100%" stopColor="var(--color-accent-press)" stopOpacity="0.01" />
          </linearGradient>

          {/* Limb darkening: sinks the grid toward the canvas at the rim, which
              is most of what sells the curvature. */}
          <radialGradient id="globe-limb">
            <stop offset="52%" stopColor="var(--color-canvas)" stopOpacity="0" />
            <stop offset="88%" stopColor="var(--color-canvas)" stopOpacity="0.45" />
            <stop offset="100%" stopColor="var(--color-canvas)" stopOpacity="0.72" />
          </radialGradient>
        </defs>

        <circle cx={cx} cy={cy} r={r} fill="url(#globe-body)" />

        {/* Far hemisphere: faint, as though seen through the body. */}
        <g
          fill="none"
          stroke="var(--color-accent-press)"
          strokeWidth="1"
          strokeOpacity="0.5"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        >
          {GLOBE_FAR.map((path, index) => (
            <path key={`far-${index}`} d={path} />
          ))}
        </g>

        {/* Near hemisphere. */}
        <g
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth="1"
          strokeOpacity="0.42"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        >
          {GLOBE_NEAR.map((path, index) => (
            <path key={`near-${index}`} d={path} />
          ))}
        </g>

        <circle cx={cx} cy={cy} r={r} fill="url(#globe-limb)" />

        {/* Silhouette last, so the edge stays crisp over the grid. */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth="1"
          strokeOpacity="0.4"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
    </div>
  );
}

/** Number of rings around the core. Each one steps outward by `RING_STEP`. */
const RING_COUNT = 14;
const RING_STEP = 'p-2.5';

/**
 * Ember strength of a ring, as a percentage of the accent colour.
 *
 * `index` counts outward from the core, and the exponent makes the drop-off
 * accelerate, so the near rings stay legible while the far ones lose their
 * colour and dissolve into the tile instead of ending on a hard edge.
 */
function ringStrength(index: number): number {
  const distance = index / RING_COUNT;
  return 34 * (1 - distance) ** 1.9;
}

/** Concentric rings tightening onto the brand mark. */
export function RippleFigure() {
  const rings = Array.from({ length: RING_COUNT });

  return (
    <div aria-hidden className="relative flex h-full items-center justify-center overflow-hidden">
      <Glow variant="spot" className="left-1/2 size-112 -translate-x-1/2" opacity={0.55} />

      {/* Fixed square so the rings stay circular; the parent crops it, which
          is how the reference frames this figure too. */}
      <div className="relative flex size-[30rem] shrink-0 items-center justify-center">
        {rings.reduce<ReactNode>(
          (inner, _, index) => (
            /* `reduce` wraps outward, so iteration 0 produces the innermost
               ring and the last iteration the outermost. */
            <div
              className={cn(
                'flex size-full items-center justify-center rounded-full border',
                RING_STEP,
              )}
              style={{
                borderColor: `color-mix(in oklab, var(--color-accent) ${ringStrength(index).toFixed(1)}%, transparent)`,
              }}
            >
              {inner}
            </div>
          ),
          <div
            className="flex size-full items-center justify-center rounded-full p-2.5 shadow-overlay"
            style={{
              background:
                'linear-gradient(180deg, color-mix(in oklab, var(--color-accent-press) 30%, transparent), color-mix(in oklab, var(--color-accent-press) 8%, transparent))',
            }}
          >
            <div className="flex size-full items-center justify-center rounded-full border border-white/10 bg-gradient-to-t from-white/[0.04] to-white/[0.12]">
              <LogoMark className="size-20" />
            </div>
          </div>,
        )}
      </div>
    </div>
  );
}

/** Tile field: six lit agent tiles among dimmed neighbours. */
export function TilesFigure() {
  const lit: (LucideIcon | null)[] = [
    null,
    ScanSearch,
    null,
    ShieldAlert,
    Braces,
    GitBranch,
    null,
    Gauge,
    FlaskConical,
    null,
    null,
    null,
  ];

  return (
    <div aria-hidden className="relative flex h-full items-center justify-center overflow-hidden">
      <Glow variant="spot" className="left-1/2 size-96 -translate-x-1/2" opacity={0.55} />

      <div className="grid grid-cols-4 gap-1">
        {lit.map((Icon, index) => (
          <div
            key={index}
            className={cn(
              'flex size-16 items-center justify-center rounded-xl sm:size-20',
              Icon
                ? 'border-4 border-canvas/20 bg-gradient-to-t from-transparent to-white/5'
                : 'bg-gradient-to-t from-canvas/30 to-transparent',
            )}
          >
            {Icon ? (
              <Icon className="size-6 text-ink" style={{ filter: GLOW_FILTER }} aria-hidden />
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

interface Bubble {
  text: string;
  side: 'left' | 'right';
  author: string;
  accent?: boolean;
}

const BUBBLES: Bubble[] = [
  {
    text: 'This only works if repeat orders hold above 24%.',
    side: 'left',
    author: 'Devilâ€™s advocate',
    accent: true,
  },
  { text: 'Where is that number coming from?', side: 'right', author: 'You' },
  { text: 'Nowhere. It was never stated.', side: 'left', author: 'Assumption hunter' },
];

/** Chat thread: the adversarial exchange, with cursor name tags. */
export function ChatFigure() {
  return (
    <div aria-hidden className="relative flex h-full items-center justify-center overflow-hidden px-6">
      <Glow variant="spot" className="left-1/2 size-96 -translate-x-1/2" opacity={0.55} />

      <div className="relative w-full max-w-115 space-y-8">
        {BUBBLES.map((bubble) => (
          <div
            key={bubble.text}
            className={cn('relative flex', bubble.side === 'right' ? 'justify-end' : 'justify-start')}
          >
            <div className="relative">
              <p className="rounded-xl bg-gradient-to-t from-white/5 to-white/10 px-3 py-2 text-xs font-medium text-ink-secondary">
                {bubble.text}
              </p>

              <span
                className={cn(
                  'absolute top-full mt-1 inline-flex items-center rounded-md border px-2 py-0.5 text-[0.625rem] font-medium',
                  bubble.side === 'right' ? 'right-0' : 'left-0',
                  bubble.accent
                    ? 'border-accent bg-accent-press text-ink'
                    : 'border-hairline-strong bg-ink text-ink-inverse',
                )}
                style={
                  bubble.accent
                    ? {
                        boxShadow:
                          '0 0 8px color-mix(in oklab, var(--color-accent) 35%, transparent)',
                      }
                    : undefined
                }
              >
                {bubble.author}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
