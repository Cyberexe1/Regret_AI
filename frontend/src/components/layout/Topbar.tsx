import { Menu, Plus } from 'lucide-react';
import { Link, matchPath, useLocation } from 'react-router-dom';
import { Avatar } from '@/components/ui/Avatar';
import { Button, buttonClasses } from '@/components/ui/Button';
import { ROUTES, routeMeta, type RouteMeta } from '@/data/navigation';
import { workspaceProfile } from '@/data/workspace';
import { cn } from '@/lib/cn';

const FALLBACK_META: RouteMeta = {
  path: '*',
  title: 'Regret Engine',
  eyebrow: 'Workspace',
};

function resolveMeta(pathname: string): RouteMeta {
  return (
    routeMeta.find((meta) => matchPath({ path: meta.path, end: true }, pathname)) ?? FALLBACK_META
  );
}

export interface TopbarProps {
  onOpenSidebar: () => void;
}

export function Topbar({ onOpenSidebar }: TopbarProps) {
  const { pathname } = useLocation();
  const meta = resolveMeta(pathname);
  const isOnIntake = matchPath({ path: ROUTES.newDecision, end: true }, pathname) !== null;

  return (
    <header className="glass sticky top-0 z-20 border-b border-hairline">
      <div className="flex h-[var(--topbar-height)] items-center gap-3 px-[var(--page-gutter)]">
        <Button
          variant="ghost"
          size="sm"
          iconOnly
          leftIcon={Menu}
          aria-label="Open navigation"
          className="lg:hidden"
          onClick={onOpenSidebar}
        />

        <div className="min-w-0 flex-1">
          <p className="eyebrow truncate">{meta.eyebrow}</p>
          <h1 className="truncate text-section-title text-ink">{meta.title}</h1>
        </div>

        {isOnIntake ? null : (
          <Link
            to={ROUTES.newDecision}
            className={cn(
              buttonClasses({ variant: 'primary', size: 'sm' }),
              'hidden sm:inline-flex',
            )}
          >
            <Plus className="size-4" aria-hidden />
            New decision
          </Link>
        )}

        <Link
          to={ROUTES.settings}
          aria-label="Workspace settings"
          className="rounded-lg transition-opacity hover:opacity-80"
        >
          <Avatar name={workspaceProfile.user.name} size="sm" />
        </Link>
      </div>
    </header>
  );
}
