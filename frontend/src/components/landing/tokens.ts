/* -------------------------------------------------------------------------- *
 * Launch layout — shared class vocabulary
 *
 * The reference design leans on a handful of repeated treatments: a 1312px
 * band, translucent white tiles, two button fills (near-white and glass), and
 * a gradient text mask. They are declared once here so twelve section files do
 * not each re-derive the same opacities.
 *
 * Colours resolve through the project's own tokens (`--color-canvas`,
 * `--color-ink`, `--color-accent`), so the page re-skins with the rest of the
 * product instead of hardcoding the template's palette.
 * -------------------------------------------------------------------------- */

/** 1312px band with the reference's 32px gutter. */
export const BAND = 'mx-auto w-full max-w-[82rem] px-5 sm:px-8';

/** Vertical rhythm of a standard section (80px in the reference). */
export const BAND_Y = 'py-16 md:py-20';

/** Translucent tile used by the bento grid, pricing and workflow panel. */
export const TILE = 'rounded-xl bg-white/[0.02]';

/** Hairline used for tile and accordion edges. */
export const TILE_LINE = 'border border-white/10';

/** Near-white primary fill: `linear-gradient(180deg, #FAFAFA, #FAFAFA cc)`. */
export const BTN_LIGHT =
  'inline-flex items-center justify-center gap-2 rounded-md bg-gradient-to-b from-ink to-ink/80 ' +
  'px-4 text-small font-medium whitespace-nowrap text-ink-inverse shadow-soft ' +
  'transition-opacity duration-150 ease-out hover:opacity-90';

/** Glass secondary fill: `linear-gradient(360deg, #FAFAFA0d, #FAFAFA1a)`. */
export const BTN_GLASS =
  'inline-flex items-center justify-center gap-2 rounded-md bg-gradient-to-t from-white/5 to-white/10 ' +
  'px-4 text-small font-medium whitespace-nowrap text-ink ' +
  'transition-colors duration-150 ease-out hover:from-white/10 hover:to-white/15';

export const BTN_SM = 'h-9';
export const BTN_MD = 'h-10';

/**
 * Gradient text mask from the reference's display headings
 * (`linear-gradient(93deg, #FAFAFA 24%, #A1A1AA 74%)`), expressed against our
 * ink tokens.
 */
export const GRADIENT_TEXT =
  'bg-[linear-gradient(93deg,var(--color-ink)_22%,var(--color-ink-secondary)_78%)] ' +
  'bg-clip-text text-transparent';

/** 96px hero display. */
export const TYPE_HERO =
  'text-[clamp(2.5rem,7.4vw,6rem)] leading-[1.02] font-semibold tracking-[-0.035em]';

/** 72px rising-feature display. */
export const TYPE_DISPLAY =
  'text-[clamp(2.25rem,5.6vw,4.5rem)] leading-[1.03] font-semibold tracking-[-0.03em]';

/** 48px section heading. */
export const TYPE_SECTION =
  'text-[clamp(1.875rem,4vw,3rem)] leading-[1.05] font-semibold tracking-[-0.025em]';

/** 20px lead paragraph. */
export const TYPE_LEAD = 'text-[1.0625rem] leading-relaxed sm:text-xl text-ink-secondary';
