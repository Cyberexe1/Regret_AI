import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';

/**
 * Placeholder while the charting chunk loads. Deliberately imports no chart
 * library, so it stays in the main bundle.
 */
export function ChartCardFallback() {
  return (
    <Card className="flex h-full min-w-0 flex-col overflow-hidden" aria-busy>
      <Skeleton className="h-4 w-40 max-w-full" />
      <Skeleton className="mt-2 h-3 w-52 max-w-full" />

      <div className="mt-5 flex min-w-0 flex-1 flex-col items-center gap-5 2xl:flex-row 2xl:gap-7">
        <Skeleton shape="circle" className="aspect-square h-auto w-full max-w-36 shrink-0" />
        <div className="w-full min-w-0 space-y-3">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      </div>
    </Card>
  );
}
