import { ArrowRight, CircleQuestionMark } from 'lucide-react';
import { Link } from 'react-router-dom';
import { buttonClasses } from '@/components/ui/Button';
import { topUncertainty } from '@/data/dashboard';
import { ROUTES } from '@/data/navigation';
import { cn } from '@/lib/cn';

/**
 * The one card on the page that is deliberately not a plain surface: an
 * accent-tinted panel, because this is the thing the user should act on.
 */
export function UncertaintyCard() {
  return (
    <section className="flex h-full flex-col rounded-xl border border-accent-line/70 bg-accent-soft/40 p-6">
      <div className="flex items-center gap-2.5">
        <CircleQuestionMark className="size-4 shrink-0 text-accent-ink" aria-hidden />
        <p className="eyebrow">Your biggest unresolved uncertainty</p>
      </div>

      <h3 className="mt-4 text-section-title text-ink">{topUncertainty.title}</h3>
      <p className="mt-2.5 text-small text-ink-secondary">{topUncertainty.detail}</p>

      <Link
        to={ROUTES.analysis}
        className={cn(buttonClasses({ variant: 'primary', size: 'sm' }), 'mt-6 self-start')}
      >
        Investigate
        <ArrowRight className="size-3.5" aria-hidden />
      </Link>
    </section>
  );
}
