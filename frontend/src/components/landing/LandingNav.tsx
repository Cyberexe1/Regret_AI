import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Menu, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Logo } from '@/components/Logo';
import { Button, buttonClasses } from '@/components/ui/Button';
import { landingNavLinks } from '@/data/landing';
import { ROUTES } from '@/data/navigation';
import { useEscapeKey } from '@/hooks/useEscapeKey';
import { cn } from '@/lib/cn';
import { LANDING_CONTAINER } from './LandingSection';
import { DURATION, EASE_OUT } from '@/lib/motion';

export function LandingNav() {
  const [menuOpen, setMenuOpen] = useState(false);
  useEscapeKey(menuOpen, () => setMenuOpen(false));

  return (
    <header className="sticky top-0 z-40 px-[var(--page-gutter)] pt-3">
      {/* Floating, rounded bar to match the workspace topbar, rather than an
          edge-to-edge strip. */}
      <div
        className={cn(
          LANDING_CONTAINER,
          'glass flex h-[var(--topbar-height)] items-center gap-6 rounded-xl border border-hairline px-4 shadow-soft',
        )}
      >
        <Link to={ROUTES.landing} aria-label="REGRET ENGINE home" className="shrink-0">
          <Logo />
        </Link>

        <nav aria-label="Landing" className="hidden flex-1 justify-center lg:flex">
          <ul className="flex items-center gap-1">
            {landingNavLinks.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  className="rounded-md px-3 py-2 text-small text-ink-secondary transition-colors hover:bg-surface-raised hover:text-ink"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="ml-auto flex items-center gap-2 lg:ml-0">
          {/* Real sign-in affordance: bordered like an account action, not a
              plain text link, even though there is no auth behind it yet. */}
          <Link
            to={ROUTES.dashboard}
            className={cn(buttonClasses({ variant: 'secondary', size: 'sm' }), 'hidden sm:inline-flex')}
          >
            Sign in
          </Link>
          <Link
            to={ROUTES.newDecision}
            className={cn(
              buttonClasses({ variant: 'primary', size: 'sm' }),
              'hidden sm:inline-flex',
            )}
          >
            Start analyzing
          </Link>

          <Button
            variant="ghost"
            size="sm"
            iconOnly
            leftIcon={menuOpen ? X : Menu}
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
            className="lg:hidden"
            onClick={() => setMenuOpen((open) => !open)}
          />
        </div>
      </div>

      <AnimatePresence>
        {menuOpen ? (
          <motion.div
            className={cn(LANDING_CONTAINER, 'overflow-hidden lg:hidden')}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: DURATION.quick, ease: EASE_OUT }}
          >
            <div className="mt-2 space-y-1 rounded-xl border border-hairline bg-surface p-3 shadow-soft">
              {landingNavLinks.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  onClick={() => setMenuOpen(false)}
                  className="block rounded-md px-3 py-2.5 text-body text-ink-secondary transition-colors hover:bg-surface-raised hover:text-ink"
                >
                  {link.label}
                </a>
              ))}

              <div className="flex flex-col gap-2 pt-2 sm:hidden">
                <Link
                  to={ROUTES.newDecision}
                  className={buttonClasses({ variant: 'primary', size: 'md', fullWidth: true })}
                >
                  Start analyzing
                </Link>
                <Link
                  to={ROUTES.dashboard}
                  className={buttonClasses({ variant: 'secondary', size: 'md', fullWidth: true })}
                >
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
