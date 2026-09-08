import { Skeleton, SkeletonText } from '@/components/ui/Skeleton';
import { PageContainer } from './PageContainer';

/** Fallback while a lazily-loaded route module arrives. */
export function PageLoading() {
  return (
    <PageContainer>
      <div className="space-y-8" role="status" aria-label="Loading page">
        <div className="space-y-3">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-7 w-64" />
          <SkeletonText lines={2} className="max-w-xl" />
        </div>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[0, 1, 2, 3].map((tile) => (
            <Skeleton key={tile} shape="block" className="h-24" />
          ))}
        </div>
        <Skeleton shape="block" className="h-64" />
      </div>
    </PageContainer>
  );
}
