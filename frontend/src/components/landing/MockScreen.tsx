import { cn } from '@/lib/cn';

/* -------------------------------------------------------------------------- *
 * Product mockup
 *
 * The reference design drops a screenshot into a rounded outer frame. We draw
 * the screen instead of shipping a PNG, so the mockup stays legible at every
 * width, inherits the real design tokens, and never goes stale against the
 * actual product.
 *
 * Everything inside is decorative chrome, not interactive: the wrapper is
 * marked `aria-hidden` by `MockFrame` so screen readers skip it entirely and
 * read the surrounding copy instead.
 * -------------------------------------------------------------------------- */

export type MockVariant = 'dashboard' | 'intake' | 'analysis' | 'report';

const SIDEBAR_ITEMS = ['Dashboard', 'New decision', 'History', 'Experiments', 'Settings'];

/** Deterministic bar heights, in percent. Regret exposure across 12 decisions. */
const BARS = [38, 62, 45, 78, 54, 88, 66, 41, 72, 95, 58, 80];

function Chrome({ title, eyebrow }: { title: string; eyebrow: string }) {
  return (
    <div className="flex min-w-0 items-center justify-between gap-2 border-b border-hairline px-2.5 py-2 sm:gap-4 sm:px-4 sm:py-3">
      <div className="min-w-0">
        <p className="text-[0.5rem] font-medium tracking-[0.14em] text-ink-muted uppercase">
          {eyebrow}
        </p>
        <p className="truncate text-[0.8125rem] font-semibold text-ink">{title}</p>
      </div>
      <div className="flex shrink-0 items-center gap-1 sm:gap-1.5">
        <span className="hidden h-5 w-10 rounded-sm bg-white/5 min-[375px]:block sm:w-14" />
        <span className="h-5 w-10 rounded-sm bg-gradient-to-b from-ink to-ink/80 sm:w-16" />
      </div>
    </div>
  );
}

function Sidebar() {
  return (
    <div className="hidden w-36 shrink-0 flex-col gap-1 border-r border-hairline p-3 sm:flex">
      <div className="mb-3 flex items-center gap-2">
        <span className="size-4 rounded-sm bg-accent-soft ring-1 ring-accent-line ring-inset" />
        <span className="h-1.5 w-14 rounded-full bg-white/15" />
      </div>
      {SIDEBAR_ITEMS.map((item, index) => (
        <div
          key={item}
          className={cn(
            'flex items-center gap-2 rounded-sm px-2 py-1.5',
            index === 0 ? 'bg-white/[0.06]' : '',
          )}
        >
          <span
            className={cn('size-2.5 rounded-[3px]', index === 0 ? 'bg-accent' : 'bg-white/15')}
          />
          <span className="text-[0.5625rem] leading-none text-ink-secondary">{item}</span>
        </div>
      ))}
    </div>
  );
}

function StatTile({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="min-w-0 rounded-md border border-hairline bg-white/[0.02] p-2 sm:p-2.5">
      <p className="text-[0.5rem] tracking-[0.12em] text-ink-muted uppercase">{label}</p>
      <p className={cn('mt-1 text-sm font-semibold numeric', tone)}>{value}</p>
    </div>
  );
}

function DashboardBody() {
  return (
    <div className="min-w-0 flex-1 space-y-2 p-2 sm:space-y-3 sm:p-4">
      <div className="grid min-w-0 grid-cols-2 gap-1.5 sm:gap-2 sm:grid-cols-4">
        <StatTile label="Analyzed" value="24" tone="text-ink" />
        <StatTile label="Assumptions" value="96" tone="text-info-ink" />
        <StatTile label="At threshold" value="7" tone="text-warning-ink" />
        <StatTile label="Tests open" value="3" tone="text-accent-ink" />
      </div>

      <div className="min-w-0 rounded-md border border-hairline bg-white/[0.02] p-2 sm:p-3">
        <div className="mb-2 flex min-w-0 items-center justify-between gap-2 sm:mb-3">
          <p className="min-w-0 truncate text-[0.625rem] font-semibold text-ink">Regret exposure by decision</p>
          <span className="rounded-sm border border-accent-line bg-accent-soft px-1.5 py-0.5 text-[0.5rem] text-accent-ink">
            last 12
          </span>
        </div>
        <div className="flex h-20 min-w-0 items-end gap-1 sm:h-28 sm:gap-1.5">
          {BARS.map((height, index) => (
            <div
              key={index}
              className={cn(
                'flex-1 rounded-t-[2px]',
                height >= 78 ? 'bg-accent' : 'bg-white/20',
              )}
              style={{ height: `${height}%` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function IntakeBody() {
  return (
    <div className="min-w-0 flex-1 space-y-2 p-2 sm:space-y-3 sm:p-4">
      <div className="space-y-1.5">
        <p className="text-[0.5625rem] text-ink-secondary">The decision</p>
        <div className="rounded-md border border-hairline bg-canvas px-2.5 py-2 text-[0.625rem] text-ink">
          Should I invest ₹5,00,000 to start a cloud kitchen?
        </div>
      </div>

      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-1.5 sm:gap-2">
        {[
          ['Domain', 'Business · Capital'],
          ['Commit by', '30 Nov 2026'],
          ['Reversibility', 'Hard to unwind'],
          ['Budget', '₹5,00,000'],
        ].map(([label, value]) => (
          <div key={label} className="min-w-0 space-y-1">
            <p className="text-[0.5625rem] text-ink-secondary">{label}</p>
            <div className="break-words rounded-md border border-hairline bg-canvas px-2 py-1.5 text-[0.5625rem] text-ink sm:px-2.5">
              {value}
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-1.5">
        <p className="text-[0.5625rem] text-ink-secondary">Constraints that actually bind</p>
        <div className="h-14 rounded-md border border-hairline bg-canvas px-2.5 py-2 text-[0.5625rem] leading-relaxed text-ink-secondary">
          No second round of funding. One kitchen lease. I cannot run it full time before month
          four.
        </div>
      </div>

      <div className="flex justify-end">
        <span className="rounded-sm bg-gradient-to-b from-ink to-ink/80 px-2.5 py-1 text-[0.5625rem] font-medium text-ink-inverse">
          Run analysis
        </span>
      </div>
    </div>
  );
}

const AGENTS: [string, string, 'done' | 'active' | 'queued'][] = [
  ['Assumption hunter', '4 surfaced', 'done'],
  ['Blindspot hunter', '3 categories missing', 'done'],
  ['Devil’s advocate', '2 framing attacks held', 'done'],
  ['Threshold engine', 'calculating breaking point', 'active'],
  ['Regret simulator', 'queued', 'queued'],
  ['Experiment planner', 'queued', 'queued'],
];

function AnalysisBody() {
  return (
    <div className="min-w-0 flex-1 space-y-1.5 p-2 sm:space-y-2 sm:p-4">
      {AGENTS.map(([name, detail, state]) => (
        <div
          key={name}
          className="flex min-w-0 items-center gap-2 rounded-md border border-hairline bg-white/[0.02] px-2 py-1.5 sm:gap-2.5 sm:px-2.5 sm:py-2"
        >
          <span
            className={cn(
              'size-2 shrink-0 rounded-full',
              state === 'done' && 'bg-success',
              state === 'active' && 'bg-accent',
              state === 'queued' && 'bg-ink-faint',
            )}
          />
          <p className="min-w-0 flex-1 truncate text-[0.625rem] font-medium text-ink">{name}</p>
          <p className="max-w-[45%] shrink truncate text-[0.5625rem] text-ink-secondary">{detail}</p>
        </div>
      ))}

      <div className="rounded-md border border-accent-line bg-panel-accent px-2.5 py-2">
        <div className="flex items-center justify-between">
          <p className="text-[0.5625rem] text-accent-ink">Analysis progress</p>
          <p className="text-[0.5625rem] text-accent-ink numeric">58%</p>
        </div>
        <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-white/10">
          <div className="h-full w-[58%] rounded-full bg-accent" />
        </div>
      </div>
    </div>
  );
}

function ReportBody() {
  return (
    <div className="min-w-0 flex-1 space-y-2 p-2 sm:space-y-3 sm:p-4">
      <div className="min-w-0 rounded-md border border-warning-line bg-panel-warning p-2 sm:p-3">
        <p className="text-[0.5rem] tracking-[0.12em] text-warning-ink uppercase">Verdict</p>
        <p className="mt-1 text-[0.6875rem] leading-snug font-semibold text-ink">
          Do not commit yet. One uncertainty decides this, and it is cheap to test.
        </p>
      </div>

      <div className="min-w-0 rounded-md border border-hairline bg-white/[0.02] p-2 sm:p-3">
        <div className="flex min-w-0 items-center justify-between gap-2">
          <p className="min-w-0 truncate text-[0.625rem] font-semibold text-ink">Repeat customer rate</p>
          <span className="rounded-sm border border-danger-line bg-danger-soft px-1.5 py-0.5 text-[0.5rem] text-danger-ink">
            critical
          </span>
        </div>

        <div className="relative mt-3 h-1.5 rounded-full bg-white/10">
          <div className="absolute inset-y-0 left-[51%] w-[9%] rounded-full bg-info" />
          <div className="absolute inset-y-[-4px] left-[68%] w-0.5 rounded-full bg-danger" />
        </div>

        <div className="mt-2 flex min-w-0 items-center justify-between gap-2 text-[0.5625rem]">
          <span className="min-w-0 truncate text-info-ink">evidence 18–21%</span>
          <span className="min-w-0 truncate text-right text-danger-ink">breaks below 24%</span>
        </div>
      </div>

      <div className="min-w-0 rounded-md border border-accent-line bg-panel-accent p-2 sm:p-3">
        <p className="text-[0.5rem] tracking-[0.12em] text-accent-ink uppercase">
          Recommended experiment
        </p>
        <p className="mt-1 text-[0.625rem] text-ink">
          14-day pilot from a rented kitchen before committing ₹5,00,000.
        </p>
        <p className="mt-1.5 text-[0.5625rem] text-ink-secondary">
          Cost: 14 days · ₹0 of the capital committed
        </p>
      </div>
    </div>
  );
}

const HEADER: Record<MockVariant, { eyebrow: string; title: string }> = {
  dashboard: { eyebrow: 'Overview', title: 'Dashboard' },
  intake: { eyebrow: 'Intake', title: 'New decision' },
  analysis: { eyebrow: 'Engine', title: 'Analysis workspace' },
  report: { eyebrow: 'Decision', title: 'Decision report' },
};

export function MockScreen({ variant = 'dashboard' }: { variant?: MockVariant }) {
  const header = HEADER[variant];

  return (
    <div className="flex h-full min-h-0 min-w-0 w-full overflow-hidden rounded-lg border border-canvas bg-surface">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Chrome eyebrow={header.eyebrow} title={header.title} />
        {variant === 'dashboard' ? <DashboardBody /> : null}
        {variant === 'intake' ? <IntakeBody /> : null}
        {variant === 'analysis' ? <AnalysisBody /> : null}
        {variant === 'report' ? <ReportBody /> : null}
      </div>
    </div>
  );
}

export interface MockFrameProps {
  variant?: MockVariant;
  /** Fades the bottom of the frame into the canvas, as the hero does. */
  fade?: boolean;
  className?: string;
}

/** Outer frame: translucent bezel, inner screen, optional bottom fade. */
export function MockFrame({ variant = 'dashboard', fade = false, className }: MockFrameProps) {
  return (
    <div aria-hidden className={cn('relative min-w-0 max-w-full', className)}>
      <div className="h-full rounded-2xl bg-white/10 p-1.5 pb-0 sm:p-2 sm:pb-0">
        <MockScreen variant={variant} />
      </div>
      {fade ? (
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              'linear-gradient(180deg, transparent 0%, color-mix(in oklab, var(--color-canvas) 90%, transparent) 86%)',
          }}
        />
      ) : null}
    </div>
  );
}
