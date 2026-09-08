import { Bell, CircleQuestionMark, Menu } from 'lucide-react';
import { Link, matchPath, useLocation } from 'react-router-dom';
import { Avatar } from '@/components/ui/Avatar';
import { Button } from '@/components/ui/Button';
import { Kbd } from '@/components/ui/Kbd';
import { ROUTES, routeMeta, type RouteMeta } from '@/data/navigation';
import { workspaceProfile } from '@/data/workspace';
import { TopbarMenu } from './TopbarMenu';

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
  onOpenCommandPalette: () => void;
}

export function Topbar({ onOpenSidebar, onOpenCommandPalette }: TopbarProps) {
  const { pathname } = useLocation();
  const meta = resolveMeta(pathname);

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

        <div className="flex items-center gap-1">
          <TopbarMenu icon={Bell} label="Notifications" title="Notifications">
            <p className="text-small text-ink-secondary">
              Nothing yet. Once decisions are being analysed, this is where threshold breaches and
              finished experiments will appear.
            </p>
          </TopbarMenu>

          <TopbarMenu icon={CircleQuestionMark} label="Help and shortcuts" title="Shortcuts">
            <ul className="space-y-2.5">
              <li className="flex items-center justify-between gap-3 text-small text-ink-secondary">
                Command palette
                <Kbd>⌘ K</Kbd>
              </li>
              <li className="flex items-center justify-between gap-3 text-small text-ink-secondary">
                Close overlay
                <Kbd>Esc</Kbd>
              </li>
            </ul>
            <Button
              variant="secondary"
              size="sm"
              fullWidth
              className="mt-4"
              onClick={onOpenCommandPalette}
            >
              Open command palette
            </Button>
          </TopbarMenu>

          <Link
            to={ROUTES.settings}
            aria-label="Account settings"
            className="ml-1 rounded-lg transition-opacity hover:opacity-80"
          >
            <Avatar name={workspaceProfile.user.name} size="sm" />
          </Link>
        </div>
      </div>
    </header>
  );
}
