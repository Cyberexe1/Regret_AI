import { Link } from 'react-router-dom';
import { LogoMark } from '@/components/Logo';
import { footerColumns, footerLegal } from '@/data/landingLaunch';
import { cn } from '@/lib/cn';
import { BAND } from './tokens';

const LINK = 'text-small text-ink-secondary transition-colors hover:text-ink';

/** Reference footer: brand block, link columns, hairline, then the legal row. */
export function LaunchFooter() {
  const year = new Date().getFullYear();

  return (
    <footer className={cn(BAND, 'pb-8')}>
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-10 border-b border-white/10 pt-10 pb-12 sm:grid-cols-2 sm:pt-12 sm:pb-16 lg:grid-cols-4">
        <div className="flex min-w-0 flex-col gap-3">
          <Link
            to="/"
            className="flex min-w-0 items-center gap-2"
            aria-label="REGRET ENGINE home"
          >
            <LogoMark className="size-6 shrink-0" />
            <span className="truncate text-lg font-bold text-ink">Regret Engine</span>
          </Link>
          <p className="max-w-xs text-small text-ink-secondary">
            Decision intelligence for choices that are expensive to reverse.
          </p>
        </div>

        {footerColumns.map((column) => (
          <nav
            key={column.heading}
            aria-label={column.heading}
            className="flex min-w-0 flex-col gap-4"
          >
            <p className="text-small font-semibold text-ink">{column.heading}</p>
            <ul className="flex flex-col gap-3">
              {column.links.map((link) => (
                <li key={`${column.heading}-${link.label}`}>
                  {link.external ? (
                    <a href={link.to} className={LINK}>
                      {link.label}
                    </a>
                  ) : (
                    <Link to={link.to} className={LINK}>
                      {link.label}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </div>

      <div className="flex min-w-0 flex-col items-start gap-4 pt-6 sm:flex-row sm:flex-wrap sm:items-center">
        <p className="min-w-0 w-full text-xs text-ink-secondary sm:w-auto sm:flex-1">
          © {year} REGRET ENGINE. Prototype build — the analysis engine is still in development.
        </p>
        <div className="flex min-w-0 flex-wrap items-center gap-4">
          {footerLegal.map((item) => (
            <a key={item.label} href={item.href} className="text-xs text-ink-secondary hover:text-ink">
              {item.label}
            </a>
          ))}
        </div>
      </div>
    </footer>
  );
}
