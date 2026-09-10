import { Card } from '@/components/ui/Card';
import type { SnapshotItem } from '@/types/report';

export interface DecisionSnapshotProps {
  items: SnapshotItem[];
}

export function DecisionSnapshot({ items }: DecisionSnapshotProps) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {items.map((item) => (
        <Card key={item.label} className="flex flex-col justify-between gap-3">
          <p className="eyebrow">{item.label}</p>
          <p className="numeric text-metric text-ink">{item.value}</p>
        </Card>
      ))}
    </div>
  );
}
