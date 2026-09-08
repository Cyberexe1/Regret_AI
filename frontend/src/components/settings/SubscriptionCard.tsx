import { Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Progress } from '@/components/ui/Progress';
import { workspaceSubscription } from '@/data/workspace';
import { formatDate } from '@/lib/format';

export interface SubscriptionCardProps {
  /** Called when Upgrade is pressed. No billing is wired up. */
  onUpgrade: () => void;
}

export function SubscriptionCard({ onUpgrade }: SubscriptionCardProps) {
  const { plan, analysesRemaining, analysesPerMonth, renewsOn } = workspaceSubscription;
  const used = analysesPerMonth - analysesRemaining;

  return (
    <div className="px-5 py-5 md:px-6">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-section-title text-ink">{plan} plan</p>
          <p className="numeric mt-1.5 text-small text-ink-secondary">
            {analysesRemaining} decision analyses remaining this month
          </p>
          <p className="mt-1 text-small text-ink-muted">
            Allowance resets {formatDate(renewsOn)}
          </p>
        </div>

        <Button variant="primary" size="md" leftIcon={Sparkles} onClick={onUpgrade}>
          Upgrade
        </Button>
      </div>

      <Progress
        className="mt-6"
        value={(used / analysesPerMonth) * 100}
        tone={analysesRemaining <= 1 ? 'warning' : 'accent'}
        size="sm"
        label={`${used} of ${analysesPerMonth} used`}
      />
    </div>
  );
}
