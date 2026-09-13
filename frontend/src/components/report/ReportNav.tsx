import { cn } from '@/lib/cn';

export interface ReportNavItem {
  id: string;
  label: string;
}

export interface ReportNavProps {
  items: ReportNavItem[];
}

/**
 * Sticky mini table-of-contents for the Decision Report - the same
 * scroll-to-id approach `IntakeProgress` already uses for the New
 * Decision page, so a long report can be jumped around instead of only
 * scrolled through top to bottom. `items` is built by the page itself
 * from whichever sections actually rendered (some are conditional, e.g.
 * "Your history" only exists when there's real historical/pattern data)
 * - this component never assumes a fixed list.
 */
export function ReportNav({ items }: ReportNavProps) {
  if (items.length === 0) return null;

  const scrollToSection = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <nav
      aria-label="Jump to a section"
      className="lg:sticky lg:top-[calc(var(--header-offset)+0.75rem)] lg:max-h-[calc(100vh-var(--header-offset)-1.5rem)] lg:overflow-y-auto"
    >
      <p className="eyebrow">On this page</p>
      <ul className="mt-3 space-y-1">
        {items.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => scrollToSection(item.id)}
              className={cn(
                'block w-full truncate rounded-md px-2.5 py-1.5 text-left text-small text-ink-secondary',
                'transition-colors duration-150 hover:bg-surface-raised hover:text-ink',
              )}
            >
              {item.label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
