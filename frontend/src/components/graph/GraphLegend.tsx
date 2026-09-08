import { cn } from '@/lib/cn';
import { graphCategoryLabel, graphCategoryTone, toneFill } from '@/lib/tone';
import { GRAPH_CATEGORIES } from '@/types';

export function GraphLegend() {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-2">
      {GRAPH_CATEGORIES.map((category) => (
        <li key={category} className="flex items-center gap-1.5">
          <span
            className={cn('size-2 shrink-0 rounded-full', toneFill[graphCategoryTone[category]])}
            aria-hidden
          />
          <span className="text-small text-ink-secondary">{graphCategoryLabel[category]}</span>
        </li>
      ))}
    </ul>
  );
}
