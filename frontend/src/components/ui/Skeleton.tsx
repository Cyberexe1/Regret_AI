import { cn } from '@/lib/cn';

export type SkeletonShape = 'text' | 'block' | 'circle';

const SHAPE: Record<SkeletonShape, string> = {
  text: 'h-3.5 rounded-sm',
  block: 'rounded-lg',
  circle: 'rounded-full',
};

export interface SkeletonProps {
  shape?: SkeletonShape;
  className?: string;
}

export function Skeleton({ shape = 'text', className }: SkeletonProps) {
  return (
    <div
      aria-hidden
      className={cn('animate-pulse bg-hairline-strong motion-reduce:animate-none', SHAPE[shape], className)}
    />
  );
}

export interface SkeletonTextProps {
  lines?: number;
  className?: string;
}

/** Multi-line text placeholder with a shortened final line. */
export function SkeletonText({ lines = 3, className }: SkeletonTextProps) {
  return (
    <div className={cn('space-y-2', className)} role="status" aria-label="Loading">
      {Array.from({ length: lines }, (_, index) => (
        <Skeleton key={index} className={index === lines - 1 ? 'w-3/5' : 'w-full'} />
      ))}
    </div>
  );
}
