import type { ComponentType } from 'react';
import { Reveal } from '@/components/Reveal';
import { bentoHeading, bentoTiles, LAUNCH_ANCHORS, type BentoIllustration } from '@/data/landingLaunch';
import { cn } from '@/lib/cn';
import { ChatFigure, GlobeFigure, RippleFigure, TilesFigure } from './BentoIllustrations';
import { BAND, TILE, TYPE_SECTION } from './tokens';

const FIGURE: Record<BentoIllustration, ComponentType> = {
  globe: GlobeFigure,
  ripple: RippleFigure,
  tiles: TilesFigure,
  chat: ChatFigure,
};

/**
 * Reference bento: two rows of two tiles, with the wide tile alternating side
 * (narrow-wide, then wide-narrow) so the grid does not read as a plain 2x2.
 * Collapses to a single column below `lg`.
 */
const SPAN = ['lg:col-span-5', 'lg:col-span-7', 'lg:col-span-7', 'lg:col-span-5'];

export function LaunchBento() {
  return (
    <section id={LAUNCH_ANCHORS.product} className={cn(BAND, 'scroll-mt-24 py-16 md:py-20')}>
      <Reveal>
        <h2 className={cn(TYPE_SECTION, 'max-w-3xl text-ink')}>{bentoHeading}</h2>
      </Reveal>

      <div className="mt-12 grid gap-4 lg:grid-cols-12">
        {bentoTiles.map((tile, index) => {
          const Figure = FIGURE[tile.illustration];

          return (
            <Reveal key={tile.title} delay={index * 0.06} className={SPAN[index]}>
              <article className={cn(TILE, 'flex h-full flex-col gap-6 overflow-hidden p-6')}>
                <div className="max-w-115">
                  <h3 className="text-2xl font-semibold text-ink">{tile.title}</h3>
                  <p className="mt-2 text-base text-ink-secondary">{tile.body}</p>
                </div>

                {/* Tall enough that the globe reads at a useful size and the
                    ripple shows several rings before it bleeds off the tile. */}
                <div className="relative min-h-80 flex-1">
                  <Figure />
                </div>
              </article>
            </Reveal>
          );
        })}
      </div>
    </section>
  );
}
