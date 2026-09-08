import { ArrowLeft } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { buttonClasses } from '@/components/ui/Button';
import { Logo } from '@/components/Logo';
import { ROUTES } from '@/data/navigation';

export function NotFoundPage() {
  const { pathname } = useLocation();

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-6 bg-canvas px-[var(--page-gutter)] text-center">
      <Logo />
      <div className="space-y-3">
        <p className="eyebrow">404</p>
        <h1 className="text-page-title text-ink">No route here</h1>
        <p className="numeric text-small text-ink-muted">{pathname}</p>
      </div>
      <Link to={ROUTES.dashboard} className={buttonClasses({ variant: 'secondary', size: 'md' })}>
        <ArrowLeft className="size-4" aria-hidden />
        Back to dashboard
      </Link>
    </div>
  );
}
