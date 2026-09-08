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

export function LandingNav() {
  const [menuOpen, setMenuOpen] = useState(false);
  useEscapeKey(menuOpen, () => setMenuOpen(false));

  return (
    <header className="glass sticky top-0 z-40 border-b border-hairline">
      <div className={cn(LANDING_CONTAINER, 'flex h-[var(--topbar-height)] items-center gap-6')}>
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
          <Link
            to={ROUTES.dashboard}
            className={cn(buttonClasses({ variant: 'ghost', size: 'sm' }), 'hidden sm:inline-flex')}
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
            className="overflow-hidden border-t border-hairline bg-surface lg:hidden"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className={cn(LANDING_CONTAINER, 'space-y-1 py-4')}>
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

              <div className="flex flex-col gap-2 pt-3 sm:hidden">
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
