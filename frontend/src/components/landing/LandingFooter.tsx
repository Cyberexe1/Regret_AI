import { Link } from 'react-router-dom';
import { Logo } from '@/components/Logo';
import { footerGroups } from '@/data/landing';
import { cn } from '@/lib/cn';
import { LANDING_CONTAINER } from './LandingSection';

const LINK_CLASS = 'text-small text-ink-secondary transition-colors hover:text-ink';

export function LandingFooter() {
  return (
    <footer className="border-t border-hairline bg-surface">
      <div className={cn(LANDING_CONTAINER, 'py-14')}>
        <div className="grid gap-10 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1fr)]">
          <div>
            <Logo />
            <p className="mt-4 max-w-xs text-small text-ink-secondary">
              Decision intelligence for consequential choices.
            </p>
          </div>

          {footerGroups.map((group) => (
            <nav key={group.heading} aria-label={group.heading}>
              <p className="eyebrow">{group.heading}</p>
              <ul className="mt-4 space-y-2.5">
                {group.links.map((link) => (
                  <li key={link.label}>
                    {link.external ? (
                      <a href={link.to} className={LINK_CLASS}>
                        {link.label}
                      </a>
                    ) : (
                      <Link to={link.to} className={LINK_CLASS}>
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        <div className="mt-12 flex flex-wrap items-center justify-between gap-3 border-t border-hairline pt-6">
          <p className="text-small text-ink-muted">REGRET ENGINE</p>
          <p className="text-small text-ink-muted">
            Prototype build. The analysis engine is not connected yet.
          </p>
        </div>
      </div>
    </footer>
  );
}
