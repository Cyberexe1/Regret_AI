import { cn } from '@/lib/cn';

export interface DividerProps {
  orientation?: 'horizontal' | 'vertical';
  /** Optional inline caption, rendered centred on horizontal dividers. */
  label?: string;
  className?: string;
}

export function Divider({ orientation = 'horizontal', label, className }: DividerProps) {
  if (orientation === 'vertical') {
    return <span role="separator" aria-orientation="vertical" className={cn('w-px self-stretch bg-hairline', className)} />;
  }

  if (label) {
    return (
      <div className={cn('flex items-center gap-3', className)}>
        <span className="h-px flex-1 bg-hairline" />
        <span className="eyebrow shrink-0">{label}</span>
        <span className="h-px flex-1 bg-hairline" />
      </div>
    );
  }

  return <hr className={cn('h-px border-0 bg-hairline', className)} />;
}
