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

/**
 * Application chrome for every workspace route: permanent sidebar at `lg`,
 * drawer below it, sticky topbar, command palette on Cmd/Ctrl+K, and a
 * scrolling content column.
 */
export function AppShell() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { pathname } = useLocation();
  const reduceMotion = useReducedMotion();

  const togglePalette = useCallback(() => setPaletteOpen((open) => !open), []);
  const openPalette = useCallback(() => setPaletteOpen(true), []);
  const closePalette = useCallback(() => setPaletteOpen(false), []);

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
        onClose={() => setDrawerOpen(false)}
        onOpenCommandPalette={openPalette}
      />

      <div className="lg:pl-[var(--sidebar-width)]">
        <Topbar onOpenSidebar={() => setDrawerOpen(true)} onOpenCommandPalette={openPalette} />

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
