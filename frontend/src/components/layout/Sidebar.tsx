import { useEffect, useRef } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { Search, Sparkles, X } from 'lucide-react';
import { Link, NavLink } from 'react-router-dom';
import { Logo } from '@/components/Logo';
import { Avatar } from '@/components/ui/Avatar';
import { Button, buttonClasses } from '@/components/ui/Button';
import { Kbd } from '@/components/ui/Kbd';
import { primaryNav, ROUTES } from '@/data/navigation';
import { workspaceProfile } from '@/data/workspace';
import { useEscapeKey } from '@/hooks/useEscapeKey';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import { useLockBodyScroll } from '@/hooks/useLockBodyScroll';
import { useIsDesktop } from '@/hooks/useMediaQuery';
import { cn } from '@/lib/cn';
import type { NavItem } from '@/types';
import { DURATION, EASE_OUT } from '@/lib/motion';

/**
 * Row styling for one navigation item.
 *
 * Three states, in priority order: active, emphasised (New Decision) and
 * default. Every row carries a transparent border so the emphasised item does
 * not shift the others by a pixel.
 */
function navRowClasses(isActive: boolean, emphasis: boolean): string {
  return cn(
    'group flex items-center gap-3 rounded-md border px-3 py-2 text-small font-medium transition-colors duration-150',
    isActive && 'border-transparent bg-accent-soft text-ink',
    !isActive && emphasis && 'border-accent-line bg-panel-accent text-ink hover:bg-accent-soft',
    !isActive &&
      !emphasis &&
      'border-transparent text-ink-secondary hover:bg-surface-raised hover:text-ink',
  );
}

function NavRow({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const { label, to, icon: Icon, count, emphasis = false } = item;

  return (
    <NavLink
      to={to}
      end={to === ROUTES.decisions}
      onClick={onNavigate}
      className={({ isActive }) => navRowClasses(isActive, emphasis)}
    >
      {({ isActive }) => (
        <>
          <Icon
            className={cn(
              'size-4 shrink-0 transition-colors',
              isActive || emphasis
                ? 'text-accent-ink'
                : 'text-ink-muted group-hover:text-ink-secondary',
            )}
            aria-hidden
          />
          <span className="truncate">{label}</span>
          <span className="ml-auto flex shrink-0 items-center gap-2">
            {typeof count === 'number' ? (
              <span className="numeric text-micro text-ink-muted">{count}</span>
            ) : null}
            {isActive ? <span className="h-4 w-0.5 rounded-full bg-accent" aria-hidden /> : null}
          </span>
        </>
      )}
    </NavLink>
  );
}

interface SidebarContentProps {
  onNavigate?: () => void;
  onOpenCommandPalette: () => void;
}

function SidebarContent({ onNavigate, onOpenCommandPalette }: SidebarContentProps) {
  const { workspaceName, plan, user } = workspaceProfile;

  return (
    <div className="flex h-full flex-col">
      {/* pt-3 matches the floating topbar's top inset, so both headers align. */}
      <div className="flex h-[var(--header-offset)] shrink-0 items-center border-b border-hairline px-4 pt-3">
        <NavLink to={ROUTES.dashboard} onClick={onNavigate} aria-label="REGRET ENGINE dashboard">
          <Logo />
        </NavLink>
      </div>

      {/* Command palette trigger */}
      <div className="shrink-0 px-3 pt-3">
        <button
          type="button"
          onClick={onOpenCommandPalette}
          className="flex w-full items-center gap-2.5 rounded-md border border-hairline bg-surface-inset px-3 py-2 text-small text-ink-muted transition-colors duration-150 hover:border-hairline-strong hover:bg-surface-raised hover:text-ink-secondary"
        >
          <Search className="size-4 shrink-0" aria-hidden />
          <span>Search</span>
          <Kbd className="ml-auto">⌘ K</Kbd>
        </button>
      </div>

      <nav aria-label="Primary" className="flex-1 overflow-y-auto p-3">
        <ul className="space-y-1">
          {primaryNav.map((item) => (
            <li key={item.to}>
              <NavRow item={item} onNavigate={onNavigate} />
            </li>
          ))}
        </ul>
      </nav>

      <div className="shrink-0 space-y-3 border-t border-hairline p-3">
        <Link
          to={ROUTES.settings}
          onClick={onNavigate}
          className="flex items-center gap-3 rounded-md px-1.5 py-1.5 transition-colors hover:bg-surface-raised"
        >
          <Avatar name={user.name} size="md" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-small font-medium text-ink">{user.name}</p>
            <p className="truncate text-micro text-ink-muted">
              {user.role} · {workspaceName}
            </p>
          </div>
        </Link>

        <div className="rounded-lg border border-hairline bg-surface-raised p-3">
          <p className="eyebrow">Plan</p>
          <p className="mt-1 text-small font-medium text-ink">{plan} Plan</p>
          <Link
            to={ROUTES.settings}
            onClick={onNavigate}
            className={cn(
              buttonClasses({ variant: 'primary', size: 'sm', fullWidth: true }),
              'mt-3',
            )}
          >
            <Sparkles className="size-3.5" aria-hidden />
            Upgrade
          </Link>
        </div>
      </div>
    </div>
  );
}

export interface SidebarProps {
  /** Drawer state; ignored at `lg` and above where the sidebar is permanent. */
  open: boolean;
  onClose: () => void;
  onOpenCommandPalette: () => void;
}

export function Sidebar({ open, onClose, onOpenCommandPalette }: SidebarProps) {
  const reduceMotion = useReducedMotion();
  const drawerRef = useRef<HTMLElement>(null);
  const isDesktop = useIsDesktop();

  // The drawer is a modal surface below `lg`: scroll is frozen, Escape
  // dismisses, Tab cycles inside it, and focus returns to the opener on close.
  useLockBodyScroll(open && !isDesktop);
  useEscapeKey(open && !isDesktop, onClose);
  useFocusTrap(open && !isDesktop, drawerRef);

  /**
   * Crossing to `lg` hides the drawer with CSS while its state stays open,
   * which would otherwise leave the page scroll locked with nothing visible to
   * dismiss. Reset the state instead of relying on the media query alone.
   */
  useEffect(() => {
    if (isDesktop && open) onClose();
  }, [isDesktop, open, onClose]);

  return (
    <>
      {/* Permanent rail from lg upwards */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[var(--sidebar-width)] border-r border-hairline bg-surface lg:block">
        <SidebarContent onOpenCommandPalette={onOpenCommandPalette} />
      </aside>

      {/* Drawer below lg */}
      <AnimatePresence>
        {open ? (
          <div className="fixed inset-0 z-50 lg:hidden">
            <motion.div
              className="absolute inset-0 bg-scrim backdrop-blur-sm"
              initial={reduceMotion ? undefined : { opacity: 0 }}
              animate={reduceMotion ? undefined : { opacity: 1 }}
              exit={reduceMotion ? undefined : { opacity: 0 }}
              transition={{ duration: DURATION.micro }}
              onClick={onClose}
            />
            <motion.aside
              ref={drawerRef}
              className="absolute inset-y-0 left-0 w-[min(18rem,calc(100vw-0.75rem))] max-w-full overflow-hidden border-r border-hairline-strong bg-surface shadow-overlay outline-none"
              initial={reduceMotion ? undefined : { x: '-100%' }}
              animate={reduceMotion ? undefined : { x: 0 }}
              exit={reduceMotion ? undefined : { x: '-100%' }}
              transition={{ duration: DURATION.quick, ease: EASE_OUT }}
              role="dialog"
              aria-modal="true"
              aria-label="Navigation"
              /* Focus target of last resort for the trap. */
              tabIndex={-1}
            >
              <Button
                variant="ghost"
                size="sm"
                iconOnly
                leftIcon={X}
                aria-label="Close navigation"
                className="absolute top-2.5 right-2.5 z-10"
                onClick={onClose}
              />
              <SidebarContent onNavigate={onClose} onOpenCommandPalette={onOpenCommandPalette} />
            </motion.aside>
          </div>
        ) : null}
      </AnimatePresence>
    </>
  );
}
