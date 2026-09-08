import { useCallback, useEffect, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Outlet, useLocation } from 'react-router-dom';
import { useModifierHotkey } from '@/hooks/useModifierHotkey';
import { CommandPalette } from './CommandPalette';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

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
    <div className="min-h-dvh bg-canvas text-ink">
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
          {reduceMotion ? (
            <Outlet />
          ) : (
            <motion.div
              key={pathname}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            >
              <Outlet />
            </motion.div>
          )}
        </main>
      </div>

      <CommandPalette open={paletteOpen} onClose={closePalette} />
    </div>
  );
}
