import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';

/**
 * Placeholder while the charting chunk loads. Deliberately imports no chart
 * library, so it stays in the main bundle.
 */
export function ChartCardFallback() {
  return (
    <Card className="flex h-full flex-col" aria-busy>
      <Skeleton className="h-4 w-40" />
      <Skeleton className="mt-2 h-3 w-52" />

      <div className="mt-5 flex flex-1 flex-col items-center gap-6 sm:flex-row sm:gap-7">
        <Skeleton shape="circle" className="size-38 shrink-0" />
        <div className="w-full space-y-3">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      </div>
    </Card>
  );
}
