import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Logo } from '@/components/Logo';
import { buttonClasses } from '@/components/ui/Button';
import { ROUTES } from '@/data/navigation';
import { cn } from '@/lib/cn';

/**
 * Root route. Deliberately minimal at this stage: it exists so `/` resolves and
 * gives access to the shell. The real landing page is designed later.
 */
export function LandingPage() {
  return (
    <div className="flex min-h-dvh flex-col bg-canvas text-ink">
      <header className="border-b border-hairline">
        <div className="mx-auto flex h-[var(--topbar-height)] max-w-[var(--page-max-width)] items-center justify-between px-[var(--page-gutter)]">
          <Logo />
          <Link
            to={ROUTES.dashboard}
            className={cn(buttonClasses({ variant: 'secondary', size: 'sm' }))}
          >
            Open workspace
          </Link>
        </div>
      </header>

      <main className="flex flex-1 items-center">
        <div className="mx-auto w-full max-w-3xl px-[var(--page-gutter)] py-16 md:py-24">
          <p className="eyebrow">Decision intelligence</p>
          <h1 className="mt-4 text-display text-ink">
            Find out how this decision fails before it does.
          </h1>
          <p className="mt-6 max-w-2xl text-body text-ink-secondary">
            REGRET ENGINE does not tell you whether a decision is good. It surfaces the assumptions
            you are taking for granted, the conditions under which the decision breaks, the regret
            you are likely to feel at six months and five years, and the cheapest experiment that
            would settle the question before you commit.
          </p>

          <div className="mt-9 flex flex-wrap items-center gap-3">
            <Link to={ROUTES.newDecision} className={buttonClasses({ variant: 'primary', size: 'lg' })}>
              Analyse a decision
              <ArrowRight className="size-4.5" aria-hidden />
            </Link>
            <Link to={ROUTES.dashboard} className={buttonClasses({ variant: 'ghost', size: 'lg' })}>
              View the workspace
            </Link>
          </div>
        </div>
      </main>

      <footer className="border-t border-hairline">
        <div className="mx-auto max-w-[var(--page-max-width)] px-[var(--page-gutter)] py-5">
          <p className="text-small text-ink-muted">
            REGRET ENGINE — frontend foundation. Analysis engine not yet connected.
          </p>
        </div>
      </footer>
    </div>
  );
}
