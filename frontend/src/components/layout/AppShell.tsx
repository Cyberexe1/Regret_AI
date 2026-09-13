import { Suspense, useCallback, useEffect, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Outlet, useLocation } from 'react-router-dom';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { useModifierHotkey } from '@/hooks/useModifierHotkey';
import { CommandPalette } from './CommandPalette';
import { PageLoading } from './PageLoading';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { DURATION, EASE_OUT } from '@/lib/motion';

const SIDEBAR_COLLAPSED_KEY = 'regret-engine:sidebar-collapsed';

function readStoredCollapsed(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return window.localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1';
  } catch {
    // Storage can throw in locked-down environments (private browsing, etc.) -
    // fall back to the default, expanded state rather than crashing the shell.
    return false;
  }
}

/**
 * Application chrome for every workspace route: permanent sidebar at `lg`,
 * drawer below it, sticky topbar, command palette on Cmd/Ctrl+K, and a
 * scrolling content column.
 */
export function AppShell() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(readStoredCollapsed);
  const { pathname } = useLocation();
  const reduceMotion = useReducedMotion();

  const togglePalette = useCallback(() => setPaletteOpen((open) => !open), []);
  const openPalette = useCallback(() => setPaletteOpen(true), []);
  const closePalette = useCallback(() => setPaletteOpen(false), []);

  // Stable identities: both are effect dependencies inside Sidebar, so an
  // inline arrow would resubscribe its listeners on every shell render.
  const openDrawer = useCallback(() => setDrawerOpen(true), []);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);

  const toggleSidebarCollapsed = useCallback(() => {
    setSidebarCollapsed((collapsed) => {
      const next = !collapsed;
      try {
        window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, next ? '1' : '0');
      } catch {
        // Best-effort persistence only - collapsing still works this session
        // even if storage is unavailable.
      }
      return next;
    });
  }, []);

  useModifierHotkey('k', togglePalette);

  // Navigating from inside the drawer should always close it.
  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  return (
    <div className="min-h-dvh min-w-0 overflow-x-clip bg-canvas text-ink">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-70 focus:rounded-md focus:border focus:border-hairline-strong focus:bg-surface-overlay focus:px-3 focus:py-2 focus:text-small"
      >
        Skip to content
      </a>

      <Sidebar
        open={drawerOpen}
        onClose={closeDrawer}
        onOpenCommandPalette={openPalette}
        collapsed={sidebarCollapsed}
        onToggleCollapsed={toggleSidebarCollapsed}
      />

      <div
        className={
          sidebarCollapsed
            ? 'transition-[padding] duration-200 lg:pl-[var(--sidebar-width-collapsed)]'
            : 'transition-[padding] duration-200 lg:pl-[var(--sidebar-width)]'
        }
      >
        <Topbar onOpenSidebar={openDrawer} onOpenCommandPalette={openPalette} />

        <main id="main-content">
          {/* A failing view must not blank the shell, and must not survive navigation. */}
          <ErrorBoundary resetKey={pathname}>
            {/* Route modules load on demand; the chrome stays put while they do. */}
            <Suspense fallback={<PageLoading />}>
              {reduceMotion ? (
                <Outlet />
              ) : (
                <motion.div
                  key={pathname}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: DURATION.quick, ease: EASE_OUT }}
                >
                  <Outlet />
                </motion.div>
              )}
            </Suspense>
          </ErrorBoundary>
        </main>
      </div>

      <CommandPalette open={paletteOpen} onClose={closePalette} />
    </div>
  );
}
