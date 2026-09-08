import { Card } from '@/components/ui/Card';
import { Progress } from '@/components/ui/Progress';
import type { SnapshotItem } from '@/types';

export interface DecisionSnapshotProps {
  items: SnapshotItem[];
}

export function DecisionSnapshot({ items }: DecisionSnapshotProps) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {items.map((item) => (
        <Card key={item.label} className="flex flex-col justify-between gap-3">
          <p className="eyebrow">{item.label}</p>
          <div>
            <p className="numeric text-metric text-ink">
              {item.value}
            </p>
            {typeof item.percentage === 'number' ? (
              <Progress
                className="mt-2.5"
                value={item.percentage}
                tone={item.tone ?? 'accent'}
                size="sm"
              />
            ) : null}
          </div>
        </Card>
      ))}
    </div>
  );
}
