import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { cn } from '@/lib/cn';
import { primaryNav, ROUTES } from '@/data/navigation';
import { workspaceProfile } from '@/data/workspace';
import { useLockBodyScroll } from '@/hooks/useLockBodyScroll';
import { useEscapeKey } from '@/hooks/useEscapeKey';
import { Avatar } from '@/components/ui/Avatar';
import { Button } from '@/components/ui/Button';
import { Logo } from '@/components/Logo';

function navLinkClasses({ isActive }: { isActive: boolean }): string {
  return cn(
    'group flex items-center gap-3 rounded-md px-3 py-2 text-small font-medium transition-colors duration-150',
    isActive
      ? 'bg-accent-soft text-ink'
      : 'text-ink-secondary hover:bg-surface-raised hover:text-ink',
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { workspaceName, plan, user } = workspaceProfile;

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-[var(--topbar-height)] shrink-0 items-center border-b border-hairline px-4">
        <NavLink to={ROUTES.dashboard} onClick={onNavigate} aria-label="REGRET ENGINE dashboard">
          <Logo />
        </NavLink>
      </div>

      <nav aria-label="Primary" className="flex-1 overflow-y-auto p-3">
        <ul className="space-y-1">
          {primaryNav.map(({ label, to, icon: Icon, count }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === ROUTES.decisions}
                className={navLinkClasses}
                onClick={onNavigate}
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      className={cn(
                        'size-4 shrink-0 transition-colors',
                        isActive ? 'text-accent-ink' : 'text-ink-muted group-hover:text-ink-secondary',
                      )}
                      aria-hidden
                    />
                    <span className="truncate">{label}</span>
                    <span className="ml-auto flex shrink-0 items-center gap-2">
                      {typeof count === 'number' ? (
                        <span className="numeric text-micro text-ink-muted">{count}</span>
                      ) : null}
                      {isActive ? (
                        <span className="h-4 w-0.5 rounded-full bg-accent" aria-hidden />
                      ) : null}
                    </span>
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="shrink-0 border-t border-hairline p-3">
        <div className="flex items-center gap-3 rounded-md px-1.5 py-1.5">
          <Avatar name={user.name} size="md" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-small font-medium text-ink">{user.name}</p>
            <p className="truncate text-micro text-ink-muted">
              {workspaceName} · {plan}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export interface SidebarProps {
  /** Drawer state; ignored at `lg` and above where the sidebar is permanent. */
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  useLockBodyScroll(open);
  useEscapeKey(open, onClose);

  return (
    <>
      {/* Permanent rail from lg upwards */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[var(--sidebar-width)] border-r border-hairline bg-surface lg:block">
        <SidebarContent />
      </aside>

      {/* Drawer below lg */}
      <AnimatePresence>
        {open ? (
          <div className="fixed inset-0 z-50 lg:hidden">
            <motion.div
              className="absolute inset-0 bg-canvas/80 backdrop-blur-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              onClick={onClose}
            />
            <motion.aside
              className="absolute inset-y-0 left-0 w-[min(17rem,85vw)] border-r border-hairline-strong bg-surface shadow-overlay"
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
              aria-label="Sidebar"
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
              <SidebarContent onNavigate={onClose} />
            </motion.aside>
          </div>
        ) : null}
      </AnimatePresence>
    </>
  );
}
