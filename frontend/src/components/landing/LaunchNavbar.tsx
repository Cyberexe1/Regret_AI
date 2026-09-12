import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Menu, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { LogoMark } from '@/components/Logo';
import { launchNavLinks } from '@/data/landingLaunch';
import { ROUTES } from '@/data/navigation';
import { useEscapeKey } from '@/hooks/useEscapeKey';
import { cn } from '@/lib/cn';
import { DURATION, EASE_OUT } from '@/lib/motion';
import { BAND, BTN_GLASS, BTN_LIGHT, BTN_SM } from './tokens';

/** Full-width action inside the mobile sheet. */
const BTN_SHEET = 'h-10 w-full';

/**
 * Reference navbar: mark plus wordmark on the left, centred menu, two actions
 * on the right. Sticky and glassed so the hero glow does not bleed through the
 * text as the page scrolls.
 */
export function LaunchNavbar() {
  const [open, setOpen] = useState(false);
  useEscapeKey(open, () => setOpen(false));

  return (
    <header className="sticky top-0 z-40 glass">
      <div className={cn(BAND, 'flex h-17 min-w-0 items-center gap-4 sm:gap-8 lg:gap-12')}>
        <Link
          to={ROUTES.landing}
          aria-label="REGRET ENGINE home"
          className="flex min-w-0 items-center gap-2"
        >
          <LogoMark className="size-6 shrink-0" />
          <span className="truncate text-lg font-bold tracking-[-0.01em] text-ink">
            Regret Engine
          </span>
        </Link>

        <nav aria-label="Primary" className="hidden flex-1 justify-center lg:flex">
          <ul className="flex items-center gap-1">
            {launchNavLinks.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  className="rounded-md px-4 py-2 text-small font-medium text-ink transition-colors hover:bg-white/5"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="ml-auto flex shrink-0 items-center gap-3 lg:ml-0">
          <Link
            to={ROUTES.dashboard}
            className="hidden rounded-md px-4 py-2 text-small font-medium text-ink transition-colors hover:bg-white/5 sm:inline-flex"
          >
            Sign in
          </Link>
          <Link
            to={ROUTES.newDecision}
            className={cn(BTN_LIGHT, BTN_SM, 'hidden sm:inline-flex')}
          >
            Get started
          </Link>

          <button
            type="button"
            aria-label={open ? 'Close menu' : 'Open menu'}
            aria-expanded={open}
            onClick={() => setOpen((value) => !value)}
            className="inline-flex size-9 items-center justify-center rounded-md text-ink transition-colors hover:bg-white/5 lg:hidden"
          >
            {open ? <X className="size-4.5" aria-hidden /> : <Menu className="size-4.5" aria-hidden />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {open ? (
          <motion.div
            className={cn(BAND, 'overflow-hidden lg:hidden')}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: DURATION.quick, ease: EASE_OUT }}
          >
            <div className="mb-3 space-y-1 rounded-xl border border-white/10 bg-surface p-3 shadow-soft">
              {launchNavLinks.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  onClick={() => setOpen(false)}
                  className="block rounded-md px-3 py-2.5 text-body text-ink-secondary transition-colors hover:bg-white/5 hover:text-ink"
                >
                  {link.label}
                </a>
              ))}

              <div className="flex flex-col gap-2 pt-2 sm:hidden">
                <Link to={ROUTES.newDecision} className={cn(BTN_LIGHT, BTN_SHEET)}>
                  Get started
                </Link>
                <Link to={ROUTES.dashboard} className={cn(BTN_GLASS, BTN_SHEET)}>
                  Sign in
                </Link>
              </div>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </header>
  );
}
