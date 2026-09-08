import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

/**
 * Application chrome for every authenticated-area route: permanent sidebar at
 * `lg`, drawer below it, sticky topbar, and a scrolling content column.
 */
export function AppShell() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { pathname } = useLocation();

  // Navigating from inside the drawer should always close it.
  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  return (
    <div className="min-h-dvh bg-canvas text-ink">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-60 focus:rounded-md focus:border focus:border-hairline-strong focus:bg-surface-overlay focus:px-3 focus:py-2 focus:text-small"
      >
        Skip to content
      </a>

      <Sidebar open={drawerOpen} onClose={() => setDrawerOpen(false)} />

      <div className="lg:pl-[var(--sidebar-width)]">
        <Topbar onOpenSidebar={() => setDrawerOpen(true)} />
        <main id="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
