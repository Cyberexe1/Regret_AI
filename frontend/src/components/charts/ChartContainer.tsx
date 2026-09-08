import type { ReactElement, ReactNode } from 'react';
import { ResponsiveContainer } from 'recharts';
import { cn } from '@/lib/cn';
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';

export interface ChartContainerProps {
  title: string;
  description?: string;
  /** Right-aligned slot for a legend, range switch or filter. */
  action?: ReactNode;
  /** Fixed plot height in pixels; width is always fluid. */
  height?: number;
  className?: string;
  /** A single Recharts chart element. */
  children: ReactElement;
}

/**
 * Gives every chart the same card chrome, heading hierarchy and responsive
 * sizing, so individual views only describe the data.
 */
export function ChartContainer({
  title,
  description,
  action,
  height = 260,
  className,
  children,
}: ChartContainerProps) {
  return (
    <Card className={cn('space-y-5', className)}>
      <CardHeader action={action}>
        <CardTitle>{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <div style={{ height }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          {children}
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
