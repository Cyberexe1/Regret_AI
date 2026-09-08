import type { LucideIcon } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Divider } from '@/components/ui/Divider';

export interface PagePlaceholderProps {
  icon: LucideIcon;
  /** Route path, shown so it is obvious which route rendered. */
  route: string;
  /** What this page will own once it is built. */
  scope: string[];
}

/**
 * Foundation-stage page body. Each route renders one of these until its real
 * surface is designed, so navigation can be verified end to end.
 */
export function PagePlaceholder({ icon: Icon, route, scope }: PagePlaceholderProps) {
  return (
    <Card padding="lg" className="max-w-3xl space-y-5">
      <div className="flex items-center gap-3">
        <span className="inline-flex size-9 items-center justify-center rounded-lg border border-accent-line bg-accent-soft text-accent-ink">
          <Icon className="size-4.5" aria-hidden />
        </span>
        <div>
          <p className="text-card-title text-ink">Route ready</p>
          <p className="numeric text-small text-ink-muted">{route}</p>
        </div>
      </div>

      <Divider label="Planned scope" />

      <ul className="space-y-2.5">
        {scope.map((item) => (
          <li key={item} className="flex gap-3 text-body text-ink-secondary">
            <span className="mt-2 size-1.5 shrink-0 rounded-full bg-ink-faint" aria-hidden />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
